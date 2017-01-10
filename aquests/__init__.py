# 2016. 1. 10 by Hans Roh hansroh@gmail.com

VERSION = "0.2a1"
version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  VERSION.split (".")))

from . import lifetime
from .lib import logger
from .client import socketpool
from .dbapi import dbpool
from .client import adns
from .protocols.http import request as http_request, request_handler as http_request_handler
try:
	from urllib.parse import urlparse
except ImportError:
	from urlparse import urlparse	
	
class Queue:
	def __init__ (self):
		self.q = []
	
	def add (self, req):
		self.q.append (req)
		
	def get (self):
		try:
			return self.q.pop (0)
		except IndexError:
			return None


class AquestResponse:
	def __init__ (self, handler):
		self.response = handler.response
		self.request = self.response.request
		self.meta = self.request.meta
		self.log = self.request.logger.log
		self.traceback = self.request.logger.trace
		del self.response.request		
	
	def __getattr__ (self, name):
		return getattr (self.response, name)
		
	def read (self):
		return self.response.get_content ()
	

def cb_gateway_demo (response):
	print (_finished_total, response.code, response.msg, response.version)
	
_request_total = 0			
_finished_total = 0		
_initialized = False
_logger = None
_cb_gateway = cb_gateway_demo
_concurrent = 1
_currents = 0
_que = Queue ()
_dns_query_req = {}

def configure (concurrent = 1, logger_obj = None, callback = None):
	global _logger, _cb_gateway, _concurrent, _initialized
	
	_concurrent = concurrent
	if logger_obj is None:
		logger_obj = logger.screen_logger ()
	_logger = logger_obj
	if callback:
		_cb_gateway = callback
	
	socketpool.create (_logger)
	dbpool.create (_logger)
	adns.init (_logger)
	lifetime.init ()
	_initialized = True
	
def _request_finished (handler):
	global _cb_gateway, _currents, _concurrent, _finished_total
	
	_finished_total += 1
	_cb_gateway (AquestResponse (handler))
	if lifetime._shutdown_phase:
		_currents -= 1
		return
	for i in range (_concurrent - _currents + 1):
		_req ()

def _add (method, url, params = None, auth = None, headers = {}, meta = {}):
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
	_que.add ((method, url, params, auth, headers, meta))

def _req ():
	global _que, _logger, _finished_total, _currents, _request_total
	args = _que.get ()
	if args is None and lifetime._shutdown_phase == 0:		
		lifetime.shutdown (0, 7)
		return	
	_request_total += 1	
	
	method, url, params, auth, headers, meta = args
	_method = method.lower ()
	if _method in ("postgresql", "redis", "mongodb", "sqlite3"):
		asyncon = dbpool.get (url)
		handler = http_request_handler.RequestHandler (asyncon, req, _request_finished)
		
	elif _method in ("ws", "wss"):
		asyncon = socketpool.get (url)
		handler = http_request_handler.RequestHandler (asyncon, req, _request_finished)
		
	else:	
		asyncon = socketpool.get (url)
		if _method in ("get", "delete"):						
			req = http_request.HTTPRequest (url, method, params, headers, "utf8", auth, _logger, meta)
		else:	
			if not headers:
				headers = {}
				
			if _method in ("post", "put", "postxml", "postjson", "postform"):
				req = 1
				
			elif _method == "rpc":
				req = 1
				
			elif _method == "grpc":
				req = 1
				
		handler = http_request_handler.RequestHandler (asyncon, req, _request_finished)
		
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
	_add ('GET', *args, **karg)
	
	