from .protocols.http import request as http_request, request_handler as http_request_handler
from .protocols.ws import request_handler as ws_request_handler, request as ws_request
from .protocols.grpc import request as grpc_request
from .protocols.proxy import tunnel_handler

def make_ws (_method, url, params, auth, headers, meta, proxy, logger):
	if type (params) is tuple:
		op_code, msg = params
	else:
		op_code, msg = 1, params # OP_TEXT
			
	req = ws_request.Request (url, msg, headers, op_code, auth, logger, meta)
	if proxy:
		if _method == 'wss':
			handler_class = tunnel_handler.WSSSLProxyTunnelHandler
		else:
			handler_class = tunnel_handler.WSProxyTunnelHandler
	else:		
		handler_class = ws_request_handler.RequestHandler
	return req, handler_class


def make_http (_method, url, params, auth, headers, meta, proxy, logger):
	if proxy and url.startswith ('https://'):
		handler_class = tunnel_handler.SSLProxyTunnelHandler
	else:			
		handler_class = http_request_handler.RequestHandler

	if _method == "rpc":
		rpcmethod, params = params
		req = http_request.XMLRPCRequest (url, rpcmethod, params, headers, None, auth, logger, meta)
		
	elif _method == "grpc":
		rpcmethod, params = params
		req = grpc_request.GRPCRequest (url, rpcmethod, params, headers, None, auth, logger, meta)
	
	else:		
		if _method in ("get", "delete"):						
			req = http_request.HTTPRequest (url, _method.upper (), params, headers, None, auth, logger, meta)
			
		else:	
			if not headers:
				headers = {}
	
			if _method in ("post", "put"):
				ct = None
				for k, v in headers.items ():
					if k.lower () == "content-type":
						ct = v						
						break
				if not ct: raise TypeError ("Content Type Undefined")
			
			elif _method != "upload":
				ct = content_types.get (_method)
				if not ct: raise TypeError ("Content Type Undefined")
				headers ['Content-Type'] = ct
				
			if _method == "upload":
				req = http_request.HTTPMultipartRequest (url, "POST", params, headers, None, auth, logger, meta)
			else:
				_method = _method.startswith ("posr") and _method [:4] or _method [:3]
				req = http_request.HTTPRequest (url, _method.upper (), params, headers, None, auth, logger, meta)	
			
	return req, handler_class

