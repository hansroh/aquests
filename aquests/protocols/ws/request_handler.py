from . import response, request
from ..http import request_handler, http_auth
from ..http.response import FailedResponse
from ...client import asynconnect
from rs4 import strutil

try:
	from urllib.parse import urlparse
except ImportError:
	from urlparse import urlparse
from base64 import b64encode
import os
import struct
import sys
try:
	from cStringIO import StringIO as BytesIO
except ImportError:
	from io import BytesIO
from . import OPCODE_CLOSE, OPCODE_TEXT, PAYLOAD_LEN, FIN, OPCODE, MASKED

class RequestHandler (request_handler.RequestHandler):
	def __init__ (self, asyncon, request, callback, *args, **karg):
		request_handler.RequestHandler.__init__ (self, asyncon, request, callback)
		self.initialize ()
	
	def initialize (self):
		self.buf = b""
		self.rfile = BytesIO ()		
		self.opcode = None
		self.payload_length = 0		
		self.has_masks = True
		self.masks = b""
		self._handshaking = False
		
	def handle_request (self):
		#print ("self.asyncon.upgraded", self.asyncon.upgraded)
		if not self.asyncon.upgraded:
			self.buffer, self.response = b"", None
			self._handshaking = True			
			self.asyncon.set_terminator (b"\r\n\r\n")
			for buf in self.get_request_buffer ():
				self.asyncon.push (buf)
		else:	
			self.asyncon.set_terminator (2)
			self.asyncon.push (self.request.get_payload ())
		self.asyncon.begin_tran (self)
		
	def get_request_buffer (self):
		hc = {}		
		scheme, netloc, script, param, queystring, fragment = urlparse (self.request.uri)
		
		addr, port = self.request.get_address ()
		if (scheme == "ws" and port == 80) or (scheme == "wss" and port == 443):
			host = addr [0]
		else:
			host = "%s:%d" % (addr, port)
					
		hc ['Host'] = host
		hc ['Origin'] = "%s://%s" % (type (self.asyncon) is asynconnect.AsynConnect and "https" or "http", hc ['Host'])
		hc ['Sec-WebSocket-Key'] = b64encode(os.urandom(16))
		hc ['Connection'] = "keep-alive, Upgrade"
		hc ['Upgrade'] = 'websocket'
		hc ['Cache-Control'] = 'no-cache'		
		
		auth_header = http_auth.authorizer.make_http_auth_header (self.request, self.asyncon.is_proxy ())
		if auth_header:
			hc ["Authorization"] = auth_header
		
		uri = self.asyncon.is_proxy () and self.request.uri.replace ("wss://", "https://").replace ("ws://", "http://") or self.request.path
		req = ("GET %s HTTP/1.1\r\n%s\r\n\r\n" % (
			uri,
			"\r\n".join (["%s: %s" % x for x in list(hc.items ())])
		)).encode ("utf8")		
		return [req]
	
	def connection_closed (self, why, msg):
		if self._handshaking:
			# possibly retry or close_case with error
			request_handler.RequestHandler.connection_closed (self, why, msg)
		else:
			if self.response is None:
				self.response = response.Response (self.request, why, msg)
			self.opcode = -1
			self.add_message ('')													
			self.close_case_with_end_tran ()
	
	def collect_incoming_data (self, data):		
		if self._handshaking:
			request_handler.RequestHandler.collect_incoming_data (self, data)
		elif self.masks or (not self.has_masks and self.payload_length):
			self.rfile.write (data)
		else:
			self.buf = data	
		
	def _tobytes (self, b):
		if sys.version_info[0] < 3:
			return map(ord, b)
		else:
			return b
	
	def found_end_of_body (self):
		if self.handled_http_authorization ():
			return
		
		if not (self.response.code == 101 and self.response.get_header ("Sec-WebSocket-Accept")):
			self.asyncon.handle_close (self.response.code, self.response.msg)
			
		else:
			self.response = None
			self._handshaking = False
			self.asyncon.upgraded = True											

			self.asyncon.push (self.request.get_payload ())
			self.asyncon.set_terminator (2)
	
	def add_message (self, data):
		if self.response is None:
			self.response = response.Response (self.request, 200, "OK", self.opcode, data)
		else:
			self.response.add_message (self.opcode, data)
								
	def found_terminator (self):
		if self._handshaking:
			request_handler.RequestHandler.found_terminator (self)
			
		elif self.masks or not self.has_masks:
			# end of message
			masked_data = bytearray(self.rfile.getvalue ())
			if self.masks:
				masking_key = bytearray(self.masks)
				data = bytearray ([masked_data[i] ^ masking_key [i%4] for i in range (len (masked_data))])
			else:
				data = masked_data	
			
			if self.opcode == OPCODE_TEXT:
				# text
				data = data.decode('utf-8')
			
			self.add_message (data)
			self.asyncon.set_terminator (2)
			self.close_case_with_end_tran ()
						
		elif self.payload_length:
			self.masks = self.buf
			self.asyncon.set_terminator (self.payload_length)
		
		elif self.opcode:
			if len (self.buf) == 2:
				fmt = ">H"
			else:
				fmt = ">Q"
			self.payload_length = struct.unpack(fmt, self._tobytes(self.buf))[0]
			if self.has_masks:
				self.asyncon.set_terminator (4) # mask
			else:
				self.asyncon.set_terminator (self.payload_length)
		
		elif self.opcode is None:
			b1, b2 = self._tobytes(self.buf)
			fin    = b1 & FIN
			self.opcode = b1 & OPCODE
			if self.opcode == OPCODE_CLOSE:				
				self.add_message ("")
				self.asyncon.disconnect ()
				self.close_case_with_end_tran ()
				return
				
			mask = b2 & MASKED
			if not mask:
				self.has_masks = False
			
			payload_length = b2 & PAYLOAD_LEN
			if payload_length == 0:
				self.add_message ("")
				self.opcode = None
				self.has_masks = True
				self.asyncon.set_terminator (2)
				self.close_case_with_end_tran ()
				return
			
			if payload_length < 126:
				self.payload_length = payload_length
				if self.has_masks:
					self.asyncon.set_terminator (4) # mask
				else:
					self.asyncon.set_terminator (self.payload_length)
			elif payload_length == 126:
				self.asyncon.set_terminator (2)	# short length
			elif payload_length == 127:
				self.asyncon.set_terminator (8) # long length

		else:
			raise AssertionError ("Web socket frame decode error")
	