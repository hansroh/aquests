from ..http import tunnel_handler
from ..ws import request_handler as ws_request_handler
from ..ws import tunnel_handler as ws_tunnel_handler

class SSLProxyTunnelHandler (tunnel_handler.SSLProxyTunnelHandler):
	def get_handshaking_buffer (self):	
		req = ("CONNECT %s:%d HTTP/%s\r\nUser-Agent: %s\r\n\r\n" % (
					self.request.rql.uinfo.netloc, 
					self.request.rql.uinfo.port,
					self.request.rql.hconf.version,
					self.request.rql.get_useragent ()
				)).encode ("utf8")
		return req
		
class WSSSLProxyTunnelHandler (SSLProxyTunnelHandler, ws_tunnel_handler.SSLProxyTunnelHandler):
	pass

class WSProxyTunnelHandler (ws_tunnel_handler.ProxyTunnelHandler, SSLProxyTunnelHandler):
	def get_handshaking_buffer (self):	
		return SSLProxyTunnelHandler.get_handshaking_buffer (self)


