# 2016. 1. 10 by Hans Roh hansroh@gmail.com

__version__ = "0.7.5.5"
version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  __version__.split (".")))

from . import lifetime, queue, request_builder, response_builder, stubproxy
from .lib import logger as logger_f
from .lib.athreads import trigger
from .client import socketpool
from .dbapi import dbpool
from .client import adns
from . import client, dbapi
from .protocols.http import localstorage as ls
from .protocols.http import request_handler
from .protocols import http2
from .dbapi import request as dbo_request
import os
import asyncore
import timeit
import time, math, random

DEBUG = 0

try:
	from urllib.parse import urlparse
except ImportError:
	from urlparse import urlparse	

def cb_gateway_demo (response):
	global _logger 
	
	try: cl = len (response.content)
	except: cl = 0	
	if isinstance (response, dbo_request.Request):		
		status = "DBO %s %s %d records/documents received"	% (
			response.code, 
			response.msg,
			cl
		)
	else:
		status = "HTTP/%s %s %s %d bytes received" % (
			response.version,
			response.code, 
			response.msg, 
			cl
		)
			
	_logger.log (
		"REQ %s-%d. %s" % (
		response.meta ['req_method'],
		response.meta ['req_id'],		
		status
		)
	)	
	#print (response.headers)	
	#print (response.data)

	      		
_request_total = 0			
_finished_total = 0		
_initialized = False
_logger = None
_cb_gateway = cb_gateway_demo
_concurrent = 1
_workers = 1
_currents = {}
_que = None
_dns_query_req = {}
_timeout = 10
	
def configure (
	workers = 1, 
	logger = None, 
	callback = None, 
	timeout = 10, 
	cookie = False, 
	force_http1 = False,
	http2_constreams = 1,
	allow_redirects = True,
	qrandom = False
):
	global _logger, _cb_gateway, _concurrent, _initialized, _timeout, _workers, _que
	
	if logger is None:
		logger = logger_f.screen_logger ()
	_logger = logger

	if qrandom:		
		_que = queue.RandomQueue ()
	else:
		_que = queue.Queue ()

	request_handler.RequestHandler.FORCE_HTTP_11 = force_http1
	request_handler.RequestHandler.ALLOW_REDIRECTS = allow_redirects
	http2.MAX_HTTP2_CONCURRENT_STREAMS = max (http2_constreams, 3)		
	_workers = workers
	_concurrent = workers
	if _concurrent == 1:
		# for preventing lifetime.loop break
		trigger.start_trigger ()
		
	if not force_http1:
		_concurrent = workers * http2_constreams
				
	if callback:
		_cb_gateway = callback
	
	if cookie:
		ls.create (_logger)
	_timeout = timeout	
	client.set_timeout (timeout)
	dbapi.set_timeout (timeout)
	
	socketpool.create (_logger)
	dbpool.create (_logger)
	adns.init (_logger)
	lifetime.init (_timeout / 2.) # maintern interval
	_initialized = True

def _next ():
	global _currents, _concurrent, _finished_total, _que, _logger
	
	_finished_total += 1	
	# preventing recursive _next	
	if lifetime._shutdown_phase:
		return
		
	if not qsize ():
		if not _currents:
			lifetime.shutdown (0, 30)
		return
	
	#print ('---', _concurrent, len (_currents), mapsize (), qsize ())
	try: _req ()
	except: _logger.trace ()
	while _concurrent > min (len (_currents), mapsize ()) and qsize ():		
		try: _req ()
		except: _logger.trace ()

def _request_finished (handler):
	global _cb_gateway, _currents, _concurrent, _finished_total, _logger
	
	if isinstance (handler, dbo_request.Request):
		response = handler
	else:
		response = response_builder.HTTPResponse (handler)
	
	_currents.pop (response.meta ['req_id'])
	response.logger = _logger
	
	callback = response.meta ['req_callback'] or _cb_gateway
	try:
		callback (response)
	except:	
		_logger.trace ()
	_next ()

def _req ():
	global _que, _logger, _finished_total, _currents, _request_total
	
	args = _que.get ()	
	_request_total += 1
	
	_is_request = False
	_is_db = False
	_method = None
	
	if type (args) is not tuple:
		req = args
		_is_request = True
		_is_db = hasattr (req, 'dbtype')		
	else:
		_is_request = False
		_method = args [0].lower ()
		
	if _is_db or _method in ("postgresql", "redis", "mongodb", "sqlite3"):
		if not _is_request:
			method, server, (dbmethod, params), dbname, auth, meta = args
			asyncon = dbpool.get (server, dbname, auth, "*" + _method)
			req = request_builder.make_dbo (_method, server, dbmethod, params, dbname, auth, meta, _logger)
		else:
			asyncon = dbpool.get (req.server, req.dbname, req.auth, "*" + req.dbtype)				
		_currents [meta ['req_id']] = [0, req.server]
		req.set_callback (_request_finished)
		asyncon.execute (req)
		
	else:	
		if not _is_request:
			method, url, params, auth, headers, meta, proxy = args
			asyncon = socketpool.get (url)		
			if _method in ("ws", "wss"):
				req = request_builder.make_ws (_method, url, params, auth, headers, meta, proxy, _logger)
			else:
				req = request_builder.make_http (_method, url, params, auth, headers, meta, proxy, _logger)			
		else:
			asyncon = socketpool.get (req.uri)
		_currents [meta ['req_id']] = [0, req.uri]
		handler = req.handler (asyncon, req, _request_finished)
		if asyncon.get_proto () and asyncon.isconnected ():			
			asyncon.handler.handle_request (handler)
		else:
			handler.handle_request ()	
		
def countreq ():
	global _request_total
	return 	_request_total

def qsize ():	
	global _que
	return _que.qsize ()

def mapsize ():
	return len (asyncore.socket_map)
	
def countfin ():	
	global _finished_total
	return _finished_total

def countcli ():	
	global _currents
	return _currents

def concurrent ():
	global _concurrent
	return _concurrent

def fetchall ():
	global _workers, _logger, _que, _timeout
	
	if not _initialized:
		configure ()
	
	_fetch_started = timeit.default_timer ()
	for i in range (min (_workers, _que.qsize ())):
		_req ()		
		
	lifetime.loop (os.name == "nt" and 1.0 or _timeout / 2.0)
	_duration = timeit.default_timer () - _fetch_started	
	socketpool.cleanup ()
	dbpool.cleanup ()
	
	_logger.log ("* %d tasks during %1.5f sec, %1.2f tasks/sec" % (_que.req_id, _duration, _que.req_id / _duration))

def suspend (timeout):
	a, b = math.modf (timeout)
	for i in range (int (b)):		
		socketpool.noop ()
		time.sleep (1)
	time.sleep (a)
		

_dns_reqs = 0
def _add (method, url, params = None, auth = None, headers = {}, callback = None, meta = {}, proxy = None):	
	global _que, _initialized, _dns_query_req, _dns_reqs
	
	def dns_result (answer = None):
		global _dns_reqs	
		_dns_reqs -= 1
	
	if not _initialized:		
		configure ()
	if not meta: meta = {}
	meta ['req_id'] = _que.req_id
	meta ['req_method'] = method
	meta ['req_callback'] = callback
	host = urlparse (url) [1].split (":")[0]
	# DNS query for caching and massive 
	
	if not lifetime._polling and _dns_reqs < 10 and host not in _dns_query_req:	
		_dns_query_req [host] = None
		_dns_reqs += 1
		adns.query (host, "A", callback = dns_result)
		for i in range (2): 
			lifetime.poll_fun_wrap (0.1)
	_que.add ((method, url, params, auth, headers, meta, proxy))
	
#----------------------------------------------------
# Add Reuqest (protocols.*.request) Object
#----------------------------------------------------	
def add (request):
	global _que	
	_que.add (request)
		
#----------------------------------------------------
# REST CALL
#----------------------------------------------------	
def get (*args, **karg):
	_add ('get', *args, **karg)

def delete (*args, **karg):
	_add ('delete', *args, **karg)

def head (*args, **karg):
	_add ('head', *args, **karg)

def trace (*args, **karg):
	_add ('trace', *args, **karg)

def options (*args, **karg):
	_add ('options', *args, **karg)
				
def post (*args, **karg):
	_add ('post', *args, **karg)

def patch (*args, **karg):
	_add ('patch', *args, **karg)

def patchform (*args, **karg):
	_add ('patchform', *args, **karg)

def patchxml (*args, **karg):
	_add ('patchxml', *args, **karg)

def patchjson (*args, **karg):
	_add ('patchjson', *args, **karg)

def patchnvp (*args, **karg):
	_add ('patchnvp', *args, **karg)
					
def put (*args, **karg):
	_add ('put', *args, **karg)

def postform (*args, **karg):
	_add ('postform', *args, **karg)

def postxml (*args, **karg):
	_add ('postxml', *args, **karg)

def postjson (*args, **karg):
	_add ('postjson', *args, **karg)	

def postnvp (*args, **karg):
	_add ('postnvp', *args, **karg)	

def putform (*args, **karg):
	_add ('putform', *args, **karg)

def putxml (*args, **karg):
	_add ('putxml', *args, **karg)

def putjson (*args, **karg):
	_add ('putjson', *args, **karg)	

def putnvp (*args, **karg):
	_add ('putnvp', *args, **karg)	
	
def upload (*args, **karg):
	_add ('upload', *args, **karg)	

def ws (*args, **karg):
	_add ('ws', *args, **karg)	

def wss (*args, **karg):
	_add ('wss', *args, **karg)	
	
	
#----------------------------------------------------
# XMLRPC, gRPC
#----------------------------------------------------
def _addrpc (method, rpcmethod, params, url, auth = None, headers = {}, callback = None, meta = {}, proxy = None):	
	_add (method, url, (rpcmethod, params), auth, headers, callback, meta, proxy)
	
def rpc	(*args, **karg):
	return stubproxy.Proxy ('rpc', _addrpc, *args, **karg)
	
def grpc	(*args, **karg):
	return stubproxy.Proxy ('grpc', _addrpc, *args, **karg)

#----------------------------------------------------
# DBO QEURY
#----------------------------------------------------
def _adddbo (method, dbmethod, params, server, dbname = None, auth = None, callback = None, meta = {}):
	global _que
	
	if not _initialized:
		configure ()
	if not meta: meta = {}	
	meta ['req_id'] = _que.req_id
	meta ['req_method'] = method
	meta ['req_callback'] = callback
	
	_que.add ((method, server, (dbmethod, params), dbname, auth, meta))
	
def postgresql (*args, **karg):
	return stubproxy.Proxy ('postgresql', _adddbo, *args, **karg)
pg = postgresql

def redis (*args, **karg):
	return stubproxy.Proxy ('redis', _adddbo, *args, **karg)

def mongodb (*args, **karg):
	return stubproxy.Proxy ('mongodb', _adddbo, *args, **karg)
	
def sqlite3 (*args, **karg):
	return stubproxy.Proxy ('sqlite3', _adddbo, *args, **karg)

