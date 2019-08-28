from . import response as http_response
from ..http2 import request_handler as http2_request_handler
from . import base_request_handler, http_auth, respcodes
from ...client import asynconnect
import base64
from hashlib import md5
import os
from hyperframe.frame import SettingsFrame
from ..http2 import H2_PROTOCOLS
from ...client import socketpool
from rs4.cbutil import tuple_cb
from rs4 import asyncore

class ProtocolSwitchError (Exception):
	pass


class RequestHandler (base_request_handler.RequestHandler):
	FORCE_HTTP_11 = False	
	
	def __init__ (self, asyncon, request, callback, connection = "keep-alive"):
		base_request_handler.RequestHandler.__init__ (self, request.logger)
		self.asyncon = asyncon
		self.wrap_in_chunk = False
		self.end_of_data = False
		self.expect_disconnect = False
		
		self.request = request
		self.callback = callback		
		self.connection = connection				
		
		self.retry_count = 0
		self.http2_handler = None
		
		self.buffer = b""	
		self.response = None
		self.callbacked = 0
		
		self._ssl = isinstance (self.asyncon, asynconnect.AsynSSLConnect)			
		self.method, self.uri = (
			self.request.get_method (),			
			self.asyncon.is_proxy () and self.request.uri or self.request.path
		)
		self.header = []
		if request.get_address () is None:
			request.set_address (self.asyncon.address)
		
	#------------------------------------------------
	# handler must provide these methods
	#------------------------------------------------
	def rebuild_http2_headers (self, headers, headers_1x):
		content_encoding = None
		for k, v in headers_1x:
			k = k.lower ()
			if k == "host":
				headers.insert (2, (":authority", v))
				continue
			if k in ("connection", "transfer-encoding"):
				continue
			if k == "content-encodig":
				content_encoding = v
			headers.append ((k, str (v)))
		return headers, content_encoding
	
	def get_http2_upgrade_header (self):
		# try h2c protocol
		hc = {}
		hc ["Upgrade"] = "h2c"
		hc ['Connection'] = 'Upgrade, HTTP2-Settings'
		http2_settings = SettingsFrame (0)
		http2_settings.settings [SettingsFrame.INITIAL_WINDOW_SIZE] = 65535
		settings = base64.urlsafe_b64encode(
		    http2_settings.serialize_body ()
		).rstrip (b'=').decode ("utf8")
		hc ['HTTP2-Settings'] = settings
		return hc
				
	def get_request_header (self, http_version = "1.1", upgrade = True):
		if not self.asyncon.isconnected () and upgrade and http_version == "1.1" and not self._ssl:
			hc = self.get_http2_upgrade_header ()
		elif ((http_version == "1.1" and self.connection == "close") or (http_version == "1.0" and self.connection == "keep-alive")):
			hc = {"Connection": self.connection}
		else:
			hc = {}
			
		auth_header = http_auth.authorizer.make_http_auth_header (self.request, self.asyncon.is_proxy ())
		if http_version == "2.0":
			headers = [
				(":method", self.method),
				(":path", self.uri),
				(":scheme", self._ssl and "https" or "http")
			]
			if auth_header:
				headers.append (("authorization", auth_header))
			return self.rebuild_http2_headers (headers, self.request.get_headers ())
		
		if auth_header:
			hc ["Authorization"] = auth_header
		headers = list (hc.items ()) + self.request.get_headers ()
		self.header = ["%s: %s" % x for x in headers]
		req = ("%s %s HTTP/%s\r\n%s\r\n\r\n" % (
			self.method,
			self.uri,
			http_version,
			"\r\n".join (self.header)
		)).encode ("utf8")		
		return req
		
	def get_request_payload (self):
		return self.request.get_payload ()
						
	def get_request_buffer (self, http_version = "1.1", upgrade = True):
		payload = self.get_request_payload ()
		if type (payload) is bytes:			
			return [self.get_request_header (http_version, upgrade) + payload]
		return [self.get_request_header (http_version, upgrade), payload]	
		
	def collect_incoming_data (self, data):		
		if not data:
			self.end_of_data = True
			return
		if not self.response or self.asyncon.get_terminator () == b"\r\n":
			self.buffer += data
		else:
			try:
				self.response.collect_incoming_data (data)			
			except http_response.ContentLimitReached:
				self.asyncon.handle_error (719)
		
	def found_terminator (self):
		if self.response:			
			if self.end_of_data:
				return self.found_end_of_body ()
			
			if self.wrap_in_chunk:
				if self.asyncon.get_terminator () == 0:
					self.asyncon.set_terminator (b"\r\n")
					self.buffer = b""
					return
						
				if not self.buffer:
					return
				
				chunked_size = int (self.buffer.split (b";") [0], 16)				
				self.buffer = b""
				
				if chunked_size == 0:
					self.end_of_data = True
					self.asyncon.set_terminator (b"\r\n")
					
				elif chunked_size > 0:
					self.asyncon.set_terminator (chunked_size)
			
			else:
				self.found_end_of_body ()
						
		else:
			self.expect_disconnect = False
			self.create_response ()
			if not self.response or isinstance (self.response, http_response.FailedResponse):
				return
			
			if self.used_chunk ():
				self.wrap_in_chunk = True
				self.asyncon.set_terminator (b"\r\n") #chunked transfer
			
			else:
				clen = 0 # no transfer-encoding, no content-lenth	
				try:
					clen = self.get_content_length ()
				except TypeError:
					if self.will_be_close ():
						self.expect_disconnect = True
						if self.response.get_header ("content-type"):
							clen = None						
				if clen == 0:
					return self.found_end_of_body ()					
				self.asyncon.set_terminator (clen)
			
	def create_response (self):
		buffer, self.buffer = self.buffer, b""		
		try:
			response = http_response.Response (self.request, buffer.decode ("utf8"))			
			if self.handle_response_code (response):				
				return
		except ProtocolSwitchError:
			return self.asyncon.handle_error (716)
		except:
			self.log ("response header error: `%s`" % repr (buffer [:80]), "error")
			return self.asyncon.handle_error (715)			
		
		ct = response.check_accept ()
		if ct:	
			self.log ("response content-type error: `%s`" % ct, "error")			
			return self.asyncon.handle_close (718)
		
		cl = response.check_max_content_length ()
		if cl:
			self.log ("response content-length error: `%d`" % cl, "error")
			return self.asyncon.handle_close (719)
			
		self.response = response

	def handle_response_code (self, response):
		# default header never has "Expect: 100-continue"
		# ignore, wait next message	
		if response.code == 100:
			self.asyncon.set_terminator (b"\r\n\r\n")			
			return 1
			
		elif response.code == 101 and response.get_header ("Upgrade") == "h2c":	# swiching protocol		
			self.asyncon._proto = "h2c"
			try:				
				self.switch_to_http2 ()
			except:	
				raise ProtocolSwitchError
			return 1
		return 0	
	
	def handled_http_authorization (self):
		if self.response.code != 401:
			return
						
		if self.request.reauth_count > 0:
			return

		try: 
			http_auth.authorizer.save_http_auth_header (self.request, self.response)
		except:
			self.trace ()
				
	def found_end_of_body (self):
		if self.response:
			self.response.done ()		
		
		self.handled_http_authorization ()			
		if self.will_be_close ():
			self.asyncon.disconnect ()		
		self.close_case_with_end_tran ()
	
	def enter_shutdown_process (self):		
		self.asyncon.handle_close (705)
		
	def connection_closed (self, why, msg):		
		if not self.asyncon:
			return # server side disconnecting because timeout, ignored
		# possibly disconnected cause of keep-alive timeout
		# but works only HTTP 1.1
		if not self.http2_handler and why == 700 and self.response is None and self.retry_count == 0:
			self.retry_count = 1			
			self.handle_rerequest ()
			return True		

		if self.response and (self.expect_disconnect or why >= 700):
			self.close_case ()
			return

		self.response = http_response.FailedResponse (why, msg, self.request)
		if hasattr (self.asyncon, "begin_tran"):
			self.close_case ()
			
	def close_case_with_end_tran (self):		
		self.asyncon.end_tran ()
		#print (self.request.meta ['sid'], 'end_tran')
		self.close_case ()
		
	def handle_callback (self):
		if self.callbacked:
			return
		tuple_cb (self, self.callback)
		self.callbacked = 1		
	
	def close_case (self):		
		self.handle_callback ()
	
	def switch_to_http2 (self):		
		if self.http2_handler is None:			
			self.http2_handler = http2_request_handler.RequestHandler (self)			
		else:
			self.http2_handler.handle_request (self)	
		
	def has_been_connected (self):
		if self._ssl or self.request.initial_http_version == "2.0":
			if self.request.initial_http_version == "2.0":
				self.asyncon.set_proto ("h2c")			
			if self.asyncon._proto in H2_PROTOCOLS:				
				self.switch_to_http2 ()
			else:
				for data in self.get_request_buffer ("1.1", False):
					self.asyncon.push (data)
	
	def handle_rerequest (self):
		# init for redirecting or reauth
		self.response = None
		self.end_of_data = False
		self.buffer = b''
		self.callbacked = 0
		self.handle_request ()
						
	def handle_request (self):
		if self.asyncon.isconnected () and self.asyncon.get_proto ():			
			return self.switch_to_http2 ()
		
		self.buffer, self.response = b"", None
		self.asyncon.set_terminator (b"\r\n\r\n")
		
		if (self.asyncon.connected) or not (self._ssl or self.request.initial_http_version == "2.0"):
			# IMP: if already connected, it means not http2
			upgrade = True
			if self.FORCE_HTTP_11:
				upgrade = False
			elif self.asyncon.isconnected ():
				upgrade = False
			for data in self.get_request_buffer ("1.1", upgrade):
				self.asyncon.push (data)

		if self._ssl and self.FORCE_HTTP_11 and self.request.initial_http_version != "2.0":
			self.asyncon.negotiate_http2 (False)
			
		self.asyncon.begin_tran (self)
	
	def will_be_close (self):
		if self.connection == "close": #server misbehavior ex.paxnet
			return True
				
		close_it = True
		connection = self.response.get_header ("connection", "").lower ()
		if self.response.version == "1.1":
			if not connection or connection.find ("keep-alive") != -1 or connection.find ("upgrade") != -1:
				close_it = False
		else:
			if connection.find ("keep-alive") != -1:
				close_it = False
		
		if not close_it:
			keep_alive = self.response.get_header ("keep-alive")
			if keep_alive:
				for each in keep_alive.split (","):
					try: 
						k, v = each.split ("=", 1)
					except ValueError:
						continue
					
					if k.strip () == "timeout": 
						timeout = int (v)
						if timeout < self.asyncon.zombie_timeout:
							self.asyncon.set_timeout (timeout)
					elif k.strip () == "max" and int (v) == 0:
						close_it = True
								
		return close_it
	
	def used_chunk (self):
		transfer_encoding = self.response.get_header ("transfer-encoding")
		return transfer_encoding and transfer_encoding.lower () == "chunked"
	
	def get_content_length (self):
		return int (self.response.get_header ("content-length"))
	
	def get_content_type (self):
		return self.response.get_header ("content-type")
		
	def get_http_version (self):
		return self.response.version
   	
   	
   	