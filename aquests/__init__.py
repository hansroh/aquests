# 2016. 1. 10 by Hans Roh hansroh@gmail.com

VERSION = "0.2a1"
version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  VERSION.split (".")))

from . import lifetime, queue, request_builder, response_builder, stubproxy
from .lib import logger as logger_f
from .client import socketpool
from .dbapi import dbpool
from .client import adns


try:
	from urllib.parse import urlparse
except ImportError:
	from urlparse import urlparse	
	

def cb_gateway_demo (response):
	print (_finished_total, response.code, response.msg, response.version)	
	print (response.read ())
	
	
_request_total = 0			
_finished_total = 0		
_initialized = False
_logger = None
_cb_gateway = cb_gateway_demo
_concurrent = 1
_currents = 0
_que = queue.Queue ()
_dns_query_req = {}

def configure (workers = 1, logger = None, callback = None):
	global _logger, _cb_gateway, _concurrent, _initialized
	
	_concurrent = workers
	if logger is None:
		logger = logger_f.screen_logger ()
	_logger = logger
	if callback:
		_cb_gateway = callback
	
	socketpool.create (_logger)
	dbpool.create (_logger)
	adns.init (_logger)
	lifetime.init ()
	_initialized = True


def _next ():
	global _currents, _concurrent, _finished_total
	
	_finished_total += 1
	if lifetime._shutdown_phase:
		_currents -= 1
		return
		
	for i in range (_concurrent - _currents + 1):
		_req ()
			
def _request_finished (handler):
	global _cb_gateway, _currents, _concurrent, _finished_total	
	_cb_gateway (response_builder.HTTPResponse (handler))
	_next ()
	
def _query_finished (*args):
	global _cb_gateway, _currents, _concurrent, _finished_total
	_cb_gateway (response_builder.DBOResponse (*args))
	_next ()	

def _add (method, url, params = None, auth = None, headers = {}, meta = {}, proxy = None):
	def dns_result (answer = None):
		pass
		
	global _que, _initialized, _dns_query_req
		
	if not _initialized:
		configure ()	
	host = urlparse (url) [1].split (":")[0]
	# DNS query for caching and massive 
	if host not in _dns_query_req:
		_dns_query_req [host] = None
		adns.query (host, "A", callback = dns_result)	
	_que.add ((method, url, params, auth, headers, meta, proxy))

content_types = {
	'postxml': "text/xml",
	'postjson': "application/json",	
	'postform': "application/x-www-form-urlencoded",
	'postnvp': "text/namevalue"	
}

def _req ():
	global _que, _logger, _finished_total, _currents, _request_total
	global content_types
	
	args = _que.get ()	
	if args is None and lifetime._shutdown_phase == 0:		
		lifetime.shutdown (0, 7)
		return
	_request_total += 1	
	
	method, url, params, auth, headers, meta, proxy = args
	_method = method.lower ()
	if _method in ("postgresql", "redis", "mongodb", "sqlite3"):
		asyncon = dbpool.get (url)
		handler = http_request_handler.RequestHandler (asyncon, req, _request_finished)
	
	else:	
		asyncon = socketpool.get (url)
		if _method in ("ws", "wss"):
			req, handler_class = request_builder.make_ws (_method, url, params, auth, headers, meta, proxy, _logger)		
			handler = handler_class (asyncon, req, _request_finished)
			
		else:
			req, handler_class = request_builder.make_http (_method, url, params, auth, headers, meta, proxy, _logger)
			handler = handler_class (asyncon, req, _request_finished)
		
		if asyncon.get_proto () and asyncon.isconnected ():
			asyncon.handler.handle_request (handler)
		else:
			handler.handle_request ()
		
def countreq ():
	global _request_total
	return 	_request_total

def countfin ():	
	global _finished_total
	return _finished_total

def countcli ():	
	global _currents
	return _currents

def fetchall ():
	global _concurrent, _currents
	
	if not _initialized:
		configure ()
			
	for i in range (_concurrent):		
		_req ()
		_currents += 1
		
	lifetime.loop (1.0)
	socketpool.cleanup ()
	dbpool.cleanup ()
	
def get (*args, **karg):
	_add ('get', *args, **karg)

def post (*args, **karg):
	_add ('post', *args, **karg)
		
def postform (*args, **karg):
	_add ('postform', *args, **karg)

def postxml (*args, **karg):
	_add ('postxml', *args, **karg)

def postjson (*args, **karg):
	_add ('postjson', *args, **karg)	

def postnvp (*args, **karg):
	_add ('postnvp', *args, **karg)	

def upload (*args, **karg):
	_add ('upload', *args, **karg)	

def ws (*args, **karg):
	_add ('ws', *args, **karg)	

def wss (*args, **karg):
	_add ('wss', *args, **karg)	

def _addrpc (method, rpcmethod, params, url, __params = None, auth = None, headers = {}, meta = {}, proxy = None):	
	_add (method, url, (rpcmethod, params), auth, headers, meta, proxy)
	
def rpc	(*args, **karg):
	return stubproxy.Proxy ('rpc', _addrpc, *args, **karg)
	
def grpc	(*args, **karg):
	return stubproxy.Proxy ('grpc', _addrpc, *args, **karg)
