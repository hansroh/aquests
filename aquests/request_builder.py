from .protocols.http import request as http_request, request_handler as http_request_handler
from .protocols.ws import request_handler as ws_request_handler, request as ws_request
from .protocols.grpc import request as grpc_request
from .dbapi import request as dbo_request
from .protocols.proxy import tunnel_handler
from .protocols.http import localstorage as ls

def make_ws (_method, url, params, auth, headers, meta, proxy, logger):
	req = ws_request.Request (url, params, headers, auth, logger, meta)
	if proxy:
		if _method == 'wss':
			handler_class = tunnel_handler.WSSSLProxyTunnelHandler
		else:
			handler_class = tunnel_handler.WSProxyTunnelHandler
	else:		
		handler_class = ws_request_handler.RequestHandler
	req.handler = handler_class	
	return req

CONTENT_TYPES = [
	('xml', "text/xml", "text/xml"),
	('json', "application/json", "application/json"),	
]
	
def make_http (_method, url, params, auth, headers, meta, proxy, logger):
	global CONTENT_TYPES
	if not headers:
		headers = {}
	if ls.g:
		headers ['Cookie'] = ls.g.get_cookie_as_string (url)
	if proxy and url.startswith ('https://'):
		handler_class = tunnel_handler.SSLProxyTunnelHandler
	else:			
		handler_class = http_request_handler.RequestHandler

	if _method == "rpc":
		rpcmethod, params = params
		req = http_request.XMLRPCRequest (url, rpcmethod, params, headers, auth, logger, meta)
	
	elif _method == "jsonrpc":
		rpcmethod, params = params
		req = http_request.JSONRPCRequest (url, rpcmethod, params, headers, auth, logger, meta)	

	elif _method == "grpc":
		rpcmethod, params = params
		req = grpc_request.GRPCRequest (url, rpcmethod, params, headers, auth, logger, meta)
	
	elif _method == "upload":
		req = http_request.HTTPMultipartRequest (url, "POST", params, headers, auth, logger, meta)
				
	else:
		ct = "application/x-www-form-urlencoded"
		ac = "*/*"
		for _alias, _ct, _ac in CONTENT_TYPES:
			if _method.endswith (_alias):
				_method = _method [:-len (_alias)]				
				ct = _ct
				ac = _ac
				break
		
		if headers.get ("Accept") is None:
			headers ['Accept'] = ac
		if params:
			headers ['Content-Type'] = ct
		req = http_request.HTTPRequest (url, _method.upper (), params, headers, auth, logger, meta)		
	
	req.handler = handler_class
	return req

def make_dbo (_method, server, dbmethod, params, dbname, auth, meta, logger):
	return dbo_request.Request (_method [1:], server, dbname, auth, dbmethod, params, None, meta)
