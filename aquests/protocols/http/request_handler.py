from . import response as http_response
from aquests.protocols.http2 import request_handler as http2_request_handler
from . import base_request_handler
from aquests.client import asynconnect
import base64
from aquests.protocols.http import http_util
from hashlib import md5
from base64 import b64encode
import os
from hyperframe.frame import SettingsFrame
from aquests.protocols.http2 import H2_PROTOCOLS

class Authorizer:
	def __init__ (self):
		self.db = {}
	
	def get (self, netloc, auth, method, uri, data):
		if netloc not in self.db:
			return ""
			
		infod = self.db [netloc]
		if infod ["meth"] == "basic":
			return "Basic " + base64.encodestring ("%s:%s" % auth) [:-1]
		elif infod ["meth"] == "bearer":
			return "Bearer " + auth [0]
		else:
			infod ["nc"] += 1
			hexnc = hex (infod ["nc"])[2:].zfill (8)
			infod ["cnonce"] = http_util.md5uniqid ()
			
			A1 = md5 (("%s:%s:%s" % (auth [0], infod ["realm"], auth [1])).encode ("utf8")).hexdigest ()
			if infod ["qop"] == "auth":
				A2 = md5 (("%s:%s" % (method, uri)).encode ("utf8")).hexdigest ()
			elif type (data) is bytes:
				entity = md5 (data).hexdigest ()
				A2 = md5 (("%s:%s" % (method, uri)).encode ("utf8")).hexdigest ()
			else:
				return # sorry data is not bytes
						
			Hash = md5 (("%s:%s:%s:%s:%s:%s" % (
				A1,
				infod ["nonce"],
				hexnc,
				infod ["cnonce"],
				infod ["qop"],
				A2
				)).encode ("utf8")
			).hexdigest ()
			
			return (
				'Digest username="%s", realm="%s", nonce="%s", '
				'uri="%s", response="%s", opaque="%s", qop=%s, nc=%s, cnonce="%s"' % (
					auth [0], infod ["realm"], infod ["nonce"], uri, Hash, 
					infod ["opaque"], infod ["qop"], hexnc, infod ["cnonce"]
				)
			)
			
	def set (self, netloc, authreq, auth):
		if auth is None:
			return
		
		amethod, authinfo = authreq.split (" ", 1)		
		infod = {"meth": amethod.lower ()}
		infod ["nc"] = 0
		for info in authinfo.split (","):
			k, v = info.strip ().split ("=", 1)
			if not v: return self.get_www_authenticate ()
			if v[0] == '"': v = v [1:-1]
			infod [k]	 = v
		
		if "qop" in infod:
			qop = list (map (lambda x: x.strip (), infod ["qop"].split (",")))
			if "auth" in qop:
				infod ["qop"] = "auth"
			else:
				infod ["qop"] = "auth-int"
				
		self.db [netloc] = infod
		

authorizer = Authorizer ()

class RequestHandler (base_request_handler.RequestHandler):
	def __init__ (self, asyncon, request, callback, connection = "keep-alive"):
		self.asyncon = asyncon
		self.wrap_in_chunk = False
		self.end_of_data = False
		self.expect_disconnect = False		
		
		self.request = request
		self.callback = callback
		base_request_handler.RequestHandler.__init__ (self, request.logger)
		self.connection = connection				
		
		self.expect_disconnect = False
		self.retry_count = 0
		self.reauth_count = 0
		
		self.buffer = b""	
		self.response = None
		
		self._ssl = False
		if isinstance (self.asyncon, asynconnect.AsynSSLConnect):
			self._ssl = True
			
		self.method, self.uri = (
			self.request.get_method (),			
			self.asyncon.is_proxy () and self.request.uri or self.request.path
		)
		self.header = []
		if request.get_address () is None:
			request.set_address (self.asyncon.address)
		
	def _del_ (self):
		self.callback = None
		self.asyncon = None
		self.request = None
		self.response = None
		
	#------------------------------------------------
	# handler must provide these methods
	#------------------------------------------------
	def get_http_auth_header (self, data = b""):
		auth = self.request.get_auth ()
		if auth:
			uri = self.asyncon.is_proxy () and self.request.uri or self.request.path
			auth_header = authorizer.get (self.request.get_address (), auth, self.method, uri, data)
			if auth_header is None:
				raise AssertionError ("Unknown authedentification method")
			return auth_header
	
	def rebuild_http2_headers (self, headers, headers_1x, payload):
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
			
		payload = self.request.get_payload ()	
		auth_header = self.get_http_auth_header (payload)
		if auth_header:
			hc ["Authorization"] = auth_header
		
		if http_version == "2.0":
			headers = [
				(":method", self.method),
				(":path", self.uri),
				(":scheme", self._ssl and "https" or "http")
			]
			return self.rebuild_http2_headers (headers, self.request.get_headers (), payload)			
		
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
		if not self.response or self.asyncon.get_terminator () == b"\r\n":
			self.buffer += data
		else:			
			self.response.collect_incoming_data (data)
		
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
			try:
				self.create_response ()
			except:					
				# I don't know why handle exception here.
				# If not, recv data continuously T.T
				self.asyncon.handle_error ()
				return
					
			# 100 Continue etc. try recv continued header
			if self.response is None:
				return				
			
			if self.used_chunk ():
				self.wrap_in_chunk = True
				self.asyncon.set_terminator (b"\r\n") #chunked transfer
			
			else:			
				try:
					clen = self.get_content_length ()
				except TypeError:
					if self.will_be_close ():
						clen = ""
						self.expect_disconnect = True
					else:
						clen = 0 # no transfer-encoding, no content-lenth												
				
				if clen == 0:
					return self.found_end_of_body ()
					
				self.asyncon.set_terminator (clen)
			
	def create_response (self):
		buffer, self.buffer = self.buffer, b""
		try:
			self.response = http_response.Response (self.request, buffer.decode ("utf8"))
		except:
			self.log ("response header error: `%s`" % repr (buffer [:80]), "error")
			self.asyncon.handle_close (708, "Response Header Error")
		else:	
			self.is_continue_response ()
		
	def is_continue_response (self):	
		# default header never has "Expect: 100-continue"
		# ignore, wait next message	
		if self.response.code == 100:
			self.asyncon.set_terminator (b"\r\n\r\n")
			self.response = None
			return True
		elif self.response.code == 101:	# swiching protocol
			if self.response.get_header ("Upgrade") == "h2c":
				self.asyncon._proto = "h2c"
				self.response = None
				self.switch_to_http2 ()				
				return True
		return False
		
	def found_end_of_body (self):	
		if self.response:
			self.response.done ()
		if self.handled_http_authorization ():
			return
		if self.will_be_close ():
			self.asyncon.disconnect ()			
		self.close_case_with_end_tran ()
	
	def handled_http_authorization (self):
		if self.response.code != 401:
			return 0 #pass
			
		if self.reauth_count > 0:
			self.asyncon.handle_close (710, "Authorization Failed")
			return 1 # abort
		
		self.reauth_count = 1		
		try: 
			authorizer.set (self.request.get_address (), self.response.get_header ("WWW-Authenticate"), self.request.get_auth ())					
		except:
			self.trace ()
			self.asyncon.handle_close (711, "Unknown Authedentification Method")
			return 1 # abort			
		else:
			self.handle_request ()
			return 1
		
		return 0 #pass
			
	def connection_closed (self, why, msg):
		is_real_asyncon = hasattr (self.asyncon, "address")
		
		if self.response and self.expect_disconnect:
			self.close_case ()
			return
	
		# possibly disconnected cause of keep-alive timeout		
		if why == 700 and self.response is None and self.retry_count == 0:
			self.retry_count = 1			
			if is_real_asyncon:
				# if not exists, fake asyncon
				self.handle_request ()
				return
		
		self.response = http_response.FailedResponse (why, msg, self.request)				
		if hasattr (self.asyncon, "begin_tran"):
			self.close_case ()
	
	def close_case_with_end_tran (self):
		self.asyncon.end_tran ()
		self.close_case ()
		
	def close_case (self):
		if self.asyncon:
			self.asyncon.handler = None # unlink back ref.
		if self.callback:
			self.callback (self)
	
	def switch_to_http2 (self):
		http2_request_handler.RequestHandler (self)		
		
	def has_been_connected (self):
		if self._ssl or self.request.initial_http_version == "2.0":
			if self.request.initial_http_version == "2.0":
				self.asyncon.set_proto ("h2c")
			if self.asyncon._proto in H2_PROTOCOLS:
				self.switch_to_http2 ()
			else:
				for data in self.get_request_buffer ("1.1", False):
					self.asyncon.push (data)				
					
	def handle_request (self):
		self.buffer, self.response = b"", None
		self.asyncon.set_terminator (b"\r\n\r\n")	
		if not (self._ssl or self.request.initial_http_version == "2.0"):
			for data in self.get_request_buffer ("1.1", True):
				self.asyncon.push (data)
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
						if timeout < self.asyncon.keep_alive_timeout:
							self.asyncon.set_keep_alive_timeout (timeout)
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
   	
   	
   	