from .protocols.http import request as http_request, request_handler as http_request_handler
from .protocols.ws import request_handler as ws_request_handler, request as ws_request
from .protocols.grpc import request as grpc_request
from .dbapi import request as dbo_request
from .protocols.proxy import tunnel_handler
from .protocols.http import localstorage as ls, util

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
    
def make_http (_method, url, params, auth, headers, meta, proxy, logger):
    headers = util.normheader (headers)
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
        ct, ac = "application/x-www-form-urlencoded", "*/*"
        if _method.endswith ("json"):
            _method = _method [:-4]
            ct, ac = "application/json", "application/json"
        util.set_content_types (headers, params, (ct, ac))
        req = http_request.HTTPRequest (url, _method.upper (), params, headers, auth, logger, meta)        
    
    req.handler = handler_class
    return req

def make_dbo (_method, server, dbmethod, params, dbname, auth, meta, logger):
    return dbo_request.Request (_method [1:], server, dbname, auth, dbmethod, params, None, meta)
