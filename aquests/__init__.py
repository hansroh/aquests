# 2016. 1. 10 by Hans Roh hansroh@gmail.com

__version__ = "0.7.6.29"
version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  __version__.split (".")))
import threading
from . import lifetime, queue, request_builder, response_builder, stubproxy
from .lib import logger as logger_f
from .lib.athreads import trigger
from .client import socketpool
from .dbapi import dbpool
from .client import adns, asynconnect
from .lib.athreads.fifo import await_fifo
from . import client, dbapi
from aquests.protocols.dns.asyndns import async_dns
from .protocols.http import localstorage as ls
from .protocols.http import request_handler, response as http_response
from .protocols import http2
from .protocols.http2 import H2_PROTOCOLS
from .dbapi import request as dbo_request
import os
import asyncore
import timeit
import time, math, random
import sys

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
_max_conns = 0
_bytesrecv = 0
_allow_redirects = True
_force_h1 = False
	
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
	global _logger, _cb_gateway, _concurrent, _initialized, _timeout, _workers, _que, _allow_redirects, _force_h1
	
	if logger is None:
		logger = logger_f.screen_logger ()
	_logger = logger

	if qrandom:		
		_que = queue.RandomQueue ()
	else:
		_que = queue.Queue ()
	
	_allow_redirects = allow_redirects
	_force_h1 = request_handler.RequestHandler.FORCE_HTTP_11 = force_http1	
	if not _force_h1:
		asynconnect.AsynConnect.fifo_class = await_fifo
		asynconnect.AsynSSLConnect.fifo_class = await_fifo
		
	http2.MAX_HTTP2_CONCURRENT_STREAMS = http2_constreams
	_workers = workers
	_concurrent = workers
	
	if not force_http1:
		_concurrent = workers * http2_constreams
	elif http2_constreams:
		_logger ("parameter http2_constreams is ignored", "warn")	
				
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

def _reque_first (request):
	global _que	
	_que.first (request)	

def handle_status_401 (response):
	global _que
	if not response.request.get_auth () or response.request.reauth_count:
		return response
	response.request.reauth_count = 1
	
	_logger ("authorization failed, %s" % response.url, "info")
	_reque_first (response.request)

def handle_status_3xx (response):
	global _allow_redirects	, _que
	
	if not _allow_redirects:
		return response
	if response.status_code not in (301, 302, 307, 308):
		return response
	
	newloc = response.get_header ('location')	
	oldloc = response.request.uri
	
	original_request = response.request
	try:
		new_request = response.request.relocate (response.response, newloc)
	except RuntimeError:		
		response.response = http_response.FailedResponse (711, "Redirect Error", original_request)
		return response
	
	_logger ("%s redirected %s from %s" % (response.status_code, response.reason, oldloc), "info")	
	# DO NOT use relocated response.request, it is None
	_reque_first (new_request)
	
def _request_finished (handler):
	global _cb_gateway, _currents, _concurrent, _finished_total, _logger, _bytesrecv,_force_h1
	try:
		if isinstance (handler, dbo_request.Request):
			response = handler
			_currents.pop (response.meta ['req_id'])
			
		else:
			response = response_builder.HTTPResponse (handler)
			_currents.pop (response.meta ['req_id'])
			for handle_func in (handle_status_401, handle_status_3xx):
				response = handle_func (response)
				if not response:
					return		
		_finished_total += 1
		response.logger = _logger
		_bytesrecv += len (response.content)
		callback = response.meta ['req_callback'] or _cb_gateway
		try:
			callback (response)
		except:		
			_logger.trace ()	
	
	except RecursionError:
		try: 
			_currents.pop (handler.request.meta ['req_id'])
		except KeyError: 
			pass	
		_logger ("too many error occured, stop requeueing", "info")	
		
	else:	
		qsize () and _req ()
		
def _req ():
	global _que, _logger, _currents, _request_total
	args = _que.get ()
	
	if args is None:
		return
		
	_request_total += 1
	_is_request = False
	_is_db = False
	_method = None

	if type (args) is not tuple:
		req = args
		meta = req.meta
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
	global _workers, _logger, _que, _timeout, _max_conns, _bytesrecv, _concurrent, _finished_total, _max_conns	
	
	if not _initialized:
		configure ()
	
	_fetch_started = timeit.default_timer ()
	# IMP. mannually set
	lifetime._polling = 1
	
	# create initail workers	
	_logger ("creating connection pool", "info")
	target_socks = min (_workers, qsize ())
	for i in range (target_socks):
		_req ()
			
	if not request_handler.RequestHandler.FORCE_HTTP_11 and http2.MAX_HTTP2_CONCURRENT_STREAMS > 1:		
		# wait all availabale	
		while 1:
			lifetime.lifetime_loop (os.name == "nt" and 1.0 or _timeout / 2.0, 1)
			if sum ([1 for conn in asyncore.socket_map.values () if not isinstance (conn, async_dns) and conn.get_proto () in H2_PROTOCOLS and conn.connected and not conn.isactive ()]) == _workers:
				_logger ('%d connection(s) created' % target_socks, 'info')
				break
			
	# now starting
	while qsize () or _currents:
		while _concurrent > min (len (_currents), mapsize ()) and qsize ():
			_req ()			
		_max_conns = max (_max_conns, mapsize ())	
		#print ('--', len (_currents), mapsize (), qsize ())
		if not mapsize ():
			break
		lifetime.lifetime_loop (os.name == "nt" and 1.0 or _timeout / 2.0, 1)
	
	#for each in _currents:
	#	print ('-- unfinished', each)
	
	lifetime._polling = 0	
	_duration = timeit.default_timer () - _fetch_started
	socketpool.cleanup ()
	dbpool.cleanup ()
	
	_logger.log ("* %d tasks during %1.2f sec (%1.2f tasks/s), recieved %d bytes (%d bytes/s), max %d conns" % (
		_finished_total, _duration, 
		_finished_total / _duration, 
		_bytesrecv,
		_bytesrecv / _duration,
		_max_conns
		)
	)

def suspend (timeout):
	a, b = math.modf (timeout)
	for i in range (int (b)):		
		socketpool.noop ()
		time.sleep (1)
	time.sleep (a)

_dns_reqs = 0
def _add (method, url, params = None, auth = None, headers = {}, callback = None, meta = None, proxy = None):	
	global _que, _initialized, _dns_query_req, _dns_reqs, _workers

	if not _initialized:		
		configure ()
		
	if not meta: 
		meta = {}

	meta ['req_id'] = _que.req_id
	meta ['req_method'] = method
	meta ['req_callback'] = callback
	host = urlparse (url) [1].split (":")[0]
	
	# DNS query for caching and massive
	if not lifetime._polling:
		if _dns_reqs < _workers and host not in _dns_query_req:
			_dns_query_req [host] = None
			_dns_reqs += 1
			adns.query (host, "A", callback = lambda x: None)		
		if mapsize ():
			lifetime.poll_fun_wrap (0.05)
		
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

