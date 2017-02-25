from . import request_handler as http_request_handler
from . import response

DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; Skitaibot/0.1a)"	

class ProxyTunnelHandler (http_request_handler.RequestHandler):
	def __init__ (self, asyncon, request, callback, *args, **karg):
		http_request_handler.RequestHandler.__init__ (self, asyncon, request, callback, connection = "keep-alive")
	
	def get_handshaking_buffer (self):
		req = ("CONNECT %s:%d HTTP/1.1\r\nUser-Agent: %s\r\n\r\n" % (
					self.request.address [0], 
					self.request.address [1],					
					DEFAULT_USER_AGENT
		)).encode ("utf8")
		return req
	
	def start_handshake (self):
		self.asyncon.set_terminator ("\r\n\r\n")
		self.asyncon.push (self.get_handshaking_buffer ())
		self.asyncon.begin_tran (self)
	
	def convert_to_ssl (self):
		pass
		
	def finish_handshake (self):
		if self.response.code == 200:
			self.asyncon.established = True
			self.response = None
			self.convert_to_ssl ()
			for buf in self.get_request_buffer ():
				self.asyncon.push (buf)
		else:
			self.response = response.FailedResponse (self.response.code, self.response.msg)
			self.asyncon.handle_close (720, "Returned %d %s" % (self.response.code, self.response.msg))
							
	def handle_request (self):	
		if not self.asyncon.established:
			self.start_handshake ()
		else:
			http_request_handler.RequestHandler.handle_request (self)
		
	def found_end_of_body (self):			
		if not self.asyncon.established:
			self.finish_handshake ()											
		else:
			http_request_handler.RequestHandler.found_end_of_body (self)
		
	def connection_closed (self, why, msg):
		if self.response is None:
			self.response = response.FailedResponse (why, msg)
		self.close_case ()


class SSLProxyTunnelHandler (ProxyTunnelHandler):
	def convert_to_ssl (self):
		self.asyncon.established = True
		self.asyncon.connected = False
		self.asyncon.connecting = True

