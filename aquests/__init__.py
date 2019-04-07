# 2016. 1. 10 by Hans Roh hansroh@gmail.com

__version__ = "0.8.9.1"

version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  __version__.split (".")))

import os, sys
import asyncore
import timeit
import time, math, random
from . import lifetime, queue, request_builder, response_builder, stubproxy
from rs4 import logger as logger_f, tc
from .client import socketpool
from .dbapi import dbpool
from .client import adns, asynconnect
from .athreads.fifo import await_fifo
from . import client, dbapi
from aquests.protocols import dns
from .protocols.http import localstorage as ls
from .protocols.http import request_handler, response as http_response
from .protocols import http2
from .protocols.http2 import H2_PROTOCOLS
from .dbapi import request as dbo_request
import copy

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
result = None
_http_status = {}
_http_version = {}
	
def configure (
	workers = 1, 
	logger = None, 
	callback = None, 
	timeout = 10, 
	cookie = False, 
	force_http1 = False,
	http2_constreams = 1,
	allow_redirects = True,
	qrandom = False,
	use_pool = True,
	tracking = False,
	backend = False,
	dns = []
):
	global _logger, _cb_gateway, _concurrent, _initialized, _timeout
	global _workers, _que, _allow_redirects, _force_h1
	
	if logger is None:
		logger = logger_f.screen_logger ()
	_logger = logger
	
	if qrandom:		
		_que = queue.RandomQueue ()
	else:
		_que = queue.Queue ()
	
	_allow_redirects = allow_redirects
	_force_h1 = request_handler.RequestHandler.FORCE_HTTP_11 = force_http1
	
	if not use_pool:
		asynconnect.AsynConnect.keep_connect = use_pool
		asynconnect.AsynSSLConnect.keep_connect = use_pool		
	if not _force_h1:
		asynconnect.AsynConnect.fifo_class = await_fifo
		asynconnect.AsynSSLConnect.fifo_class = await_fifo
			
	http2.MAX_HTTP2_CONCURRENT_STREAMS = http2_constreams
	_workers = workers
	_concurrent = workers
	
	if not force_http1:
		_concurrent = workers * http2_constreams
	elif http2_constreams:
		pass
		#_logger ("parameter http2_constreams is ignored", "warn")	
				
	if callback:
		_cb_gateway = callback
	
	if cookie:
		ls.create (_logger)
	_timeout = timeout	
	client.set_timeout (timeout)
	dbapi.set_timeout (timeout)
	
	socketpool.create (_logger, backend = backend, use_pool = use_pool)
	dbpool.create (_logger, backend = backend)
	adns.init (_logger, dns)
	lifetime.init (_timeout / 2., logger) # maintern interval	
	if tracking:
		lifetime.enable_memory_track ()
	_initialized = True

def _reque_first (request):
	global _que
	
	_que.first (request)	

def handle_status_401 (response):
	global _que
	if not response.request.get_auth () or response.request.reauth_count:
		return response
	
	_logger ("authorization failed, %s" % response.url, "info")		
	request = response.request	
	request.reauth_count = 1	
	_reque_first (request)	
	
def handle_status_3xx (response):
	global _allow_redirects	, _que
	
	if not _allow_redirects:
		return response
	if response.status_code not in (301, 302, 307, 308):
		return response

	newloc = response.get_header ('location')	
	oldloc = response.request.uri
	request = response.request
	
	if newloc == oldloc:
		response.response = http_response.FailedResponse (711, "Redirect Error", request)
		return response
	
	try:		
		request.relocate (response.response, newloc)		
	except RuntimeError:		
		response.response = http_response.FailedResponse (711, "Redirect Error", request)
		return response
	
	#_logger ("%s redirected to %s from %s" % (response.status_code, newloc, oldloc), "info")	
	# DO NOT use relocated response.request, it is None
	_reque_first (request)
	
def _request_finished (handler):
	global _cb_gateway, _currents, _concurrent, _finished_total, _logger, _bytesrecv,_force_h1
	global _http_status, _http_version
	
	req_id = handler.request.meta ['req_id']	
	try: 
		_currents.pop (req_id)
	except KeyError:
		pass
			
	if isinstance (handler, dbo_request.Request):
		response = handler	
		
	else:
		response = response_builder.HTTPResponse (handler.response)		
		
		try:
			for handle_func in (handle_status_401, handle_status_3xx):
				response = handle_func (response)
				if not response:
					# re-requested
					return req_if_queue (req_id)					
		except:
			_logger.trace ()
		
	_finished_total += 1
	response.logger = _logger
	_bytesrecv += len (response.content)
	
	try: _http_status [response.status_code] += 1
	except KeyError: _http_status [response.status_code] = 1
	try: _http_version [response.version] += 1
	except KeyError: _http_version [response.version] = 1
	
	callback = response.meta ['req_callback'] or _cb_gateway
	try:
		callback (response)
	except:		
		_logger.trace ()	
	
	req_if_queue (req_id)
	
def req_if_queue (req_id):
	global _logger, _currents
	
	try:
		qsize () and _req ()
	except RecursionError:
		try: 
			_currents.pop (req_id)
		except KeyError: 
			pass	
		_logger ("too many error occured, failed requeueing", "fail")
		
def _req ():
	global _que, _logger, _currents, _request_total, _backend
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
	
def workings ():
	global _currents
	return 	len (_currents)
			
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
	global _workers, _logger, _que, _timeout, _max_conns, _bytesrecv, _concurrent, _finished_total, _max_conns, _force_h1, _request_total, _bytesrecv
	global result, _http_status, _http_version
	
	if not qsize ():
		_logger.log ('no item in queue.')
		return
	
	if not _initialized:
		configure ()
	
	_fetch_started = timeit.default_timer ()
	# IMP. mannually set
	lifetime._polling = 1
	
	# create initail workers	
	#_logger ("creating connection pool", "info")
	target_socks = min (_workers, qsize ())
	for i in range (target_socks):
		_req ()	
	
	select_timeout = 1.0
	if not _force_h1 and http2.MAX_HTTP2_CONCURRENT_STREAMS > 1:
		# wait all availabale	
		while qsize ():			
			lifetime.lifetime_loop (select_timeout, 1)
			target_socks = sum ([1 for conn in asyncore.socket_map.values () if hasattr (conn, "get_proto") and not isinstance (conn, (dns.UDPClient, dns.TCPClient)) and conn.get_proto () in H2_PROTOCOLS and conn.connected and not conn.isactive ()])
			if target_socks == _workers:
				#_logger ('%d connection(s) created' % target_socks, 'info')				
				break
	
	# now starting
	if http2.MAX_HTTP2_CONCURRENT_STREAMS == 1:
		measurement = min
	else:
		measurement = max
		
	while qsize () or _currents:
		lifetime.lifetime_loop (select_timeout, 1)
		while _concurrent > measurement (len (_currents), mapsize ()) and qsize ():
			_req ()
			_max_conns = max (_max_conns, mapsize ())			
		#print ('--', len (_currents), mapsize (), qsize ())
		if not mapsize ():
			break
		
	lifetime._polling = 0
	_duration = timeit.default_timer () - _fetch_started
	socketpool.cleanup ()
	dbpool.cleanup ()	
	result = Result (_finished_total, _duration, _bytesrecv, _max_conns, copy.copy (_http_status), copy.copy (_http_version))
	
	# reinit for next session
	_request_total = 0			
	_finished_total = 0		
	_max_conns = 0
	_bytesrecv = 0
	_http_status = {}
	_http_version = {}

class Result:
	def __init__ (self, tasks, duration, bytes_recv, max_conns, _http_status, _http_version):
		self.tasks = tasks
		self.duration = duration
		self.bytes_recv = bytes_recv
		self.max_conns = max_conns
		self._http_status = _http_status
		self._http_version = _http_version
	
	def report (self):
		print (tc.debug ("summary"))
		print ("- finished in: {:.2f} seconds".format (self.duration))
		print ("- requests: {:,} requests".format (self.tasks))
		print ("- requests/sec: {:.2f} requests".format (self.tasks / self.duration))
		print ("- bytes recieved: {:,} bytes".format (self.bytes_recv))
		print ("- bytes recieved/sec: {:,} bytes".format (int (self.bytes_recv / self.duration)))
		
		print (tc.debug ("response status codes"))
		for k, v in sorted (self._http_status.items ()):
			print ("- {}: {:,}".format (k, v))
		print (tc.debug ("response HTTP versions")	)
		for k, v in sorted (self._http_version.items ()):
			print ("- {}: {:,}".format (k, v))	
			
		
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
	_que.add ((method, url, params, auth, headers, meta, proxy))
	
	# DNS query for caching and massive
	if not lifetime._polling  and  _dns_reqs < _workers:
		host = urlparse (url) [1].split (":")[0]
		if host not in _dns_query_req:
			_dns_query_req [host] = None
			_dns_reqs += 1
			adns.query (host, "A", callback = lambda x: None)
			
		if dns.qsize ():
			dns.pop_all ()
			asyncore.loop (0.1, count = 2)
	#print ('~~~~~~~~~~~~~~~', asyndns.pool.connections)


def log (msg, type = "info"):
	global _logger
	_logger (msg, type)
	
#----------------------------------------------------
# Add Reuqest (protocols.*.request) Object
#----------------------------------------------------	
def add (request):
	global _que	
	_que.add (request)
			
#----------------------------------------------------
# HTTP CALL
#----------------------------------------------------	
def head (*args, **karg):
	_add ('head', *args, **karg)

def trace (*args, **karg):
	_add ('trace', *args, **karg)

def options (*args, **karg):
	_add ('options', *args, **karg)

def upload (*args, **karg):
	_add ('upload', *args, **karg)

def get (*args, **karg):
	_add ('get', *args, **karg)

def delete (*args, **karg):
	_add ('delete', *args, **karg)

def post (*args, **karg):
	_add ('post', *args, **karg)

def patch (*args, **karg):
	_add ('patch', *args, **karg)

def put (*args, **karg):
	_add ('put', *args, **karg)


def getjson (*args, **karg):
	_add ('getjson', *args, **karg)

def deletejson (*args, **karg):
	_add ('deletejson', *args, **karg)

def patchjson (*args, **karg):
	_add ('patchjson', *args, **karg)
	
def postjson (*args, **karg):
	_add ('postjson', *args, **karg)	
	
def putjson (*args, **karg):
	_add ('putjson', *args, **karg)	


def getxml (*args, **karg):
	_add ('getxml', *args, **karg)

def deletexml (*args, **karg):
	_add ('deletexml', *args, **karg)

def patchxml (*args, **karg):
	_add ('patchxml', *args, **karg)
	
def postxml (*args, **karg):
	_add ('postxml', *args, **karg)	
	
def putxml (*args, **karg):
	_add ('putxml', *args, **karg)	
	

#----------------------------------------------------
# Websocket
#----------------------------------------------------	
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

def jsonrpc	(*args, **karg):
	return stubproxy.Proxy ('jsonrpc', _addrpc, *args, **karg)
		
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
pgsql = pg = postgresql

def redis (*args, **karg):
	return stubproxy.Proxy ('redis', _adddbo, *args, **karg)

def mongodb (*args, **karg):
	return stubproxy.Proxy ('mongodb', _adddbo, *args, **karg)
	
def sqlite3 (*args, **karg):
	return stubproxy.Proxy ('sqlite3', _adddbo, *args, **karg)

