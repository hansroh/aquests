VERSION = "0.1.1"
version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  VERSION.split (".")))

import asyncore
from . import rql
from . import localstorage
from . import rc
from skitai import lifetime
from skitai.client import adns
from skitai.lib import strutil
from skitai.protocol.http import request as http_request
from skitai.protocol.http import response as http_response
from skitai.protocol.http import request_handler as http_request_handler
from skitai.protocol.http import tunnel_handler
from skitai.protocol.ws import request_handler as ws_request_handler
from skitai.protocol.ws import tunnel_handler as ws_tunnel_handler
from skitai.protocol.ws import request as ws_request
from skitai.protocol.dns import asyndns
from skitai.client import socketpool, asynconnect
from skitai.server.threads import trigger

_currents = {}
_latest = ""
_map = asyncore.socket_map
_logger = None
_debug = False
_que = []
_max_numpool = 4
_current_numpool = 4
_concurrents = 2
_default_header = ""
_use_lifetime = True
_timeout = 30

def configure (
	logger = None, 
	numpool = 3,
	timeout = 30,
	concurrents = 2,
	default_option = "", 
	response_max_size = 100000000,
	use_lifetime = True,
	debug = False
	):
	
	global _logger, _max_numpool, _current_numpool, _concurrents, _default_option, _configured, _use_lifetime, _timeout, _debug
	
	_default_option = default_option
	_max_numpool = numpool + 1
	_current_numpool = _max_numpool
	_logger = logger
	_concurrents = concurrents
	_use_lifetime = use_lifetime
	_debug = debug
	
	http_response.Response.SIZE_LIMIT = response_max_size
	localstorage.create (logger)
		
	socketpool.create (logger)
	adns.init (logger)
	trigger.start_trigger (logger) # for keeping lifetime loop
			
	
def add (thing, callback, front = False):
	global _que, _default_header, _logger, _current_numpool, _currents

	if strutil.is_str_like (thing):
		thing = thing + " " + _default_option
		try:
			thing = rql.RQL (thing)
		except:
			_logger.trace ()
			return
	
	#thing.show ()
	
	if front:
		_que.insert (0, (thing, callback, _logger))
	else:	
		_que.append ((thing, callback, _logger))
		
	# notify new item
	if thing.uinfo.netloc not in _currents:
		_current_numpool += 1
	
	if _latest: # after loop started, not during queueing
		maybe_pop ()

def maybe_pop ():
	global _max_numpool, _current_numpool, _que, _map, _concurrents
	global _logger, _use_lifetime, _debug, _currents, _latest
	
	lm = len (_map)
	if _use_lifetime and not _que and lm == 1:
		lifetime.shutdown (0, 1)
		return
	
	if _current_numpool > _max_numpool:
		_current_numpool = _max_numpool  # maximum
	
	_currents = {}
	for r in list (_map.values ()):
		if isinstance (r, asynconnect.AsynConnect) and r.handler: 
			netloc = r.handler.request.rql.uinfo.netloc
		elif isinstance (r, asyndns.async_dns): 
			netloc = r.qname						
		else:
			continue	
			
		try: _currents [netloc] += 1
		except KeyError: _currents [netloc] = 1
		
	index = 0
	indexes = []		
	while lm < _current_numpool and _que:
		try:
			item = _que [index]
		except IndexError:
			# for minimize cost to search new item by concurrents limitation
			_current_numpool = len (_currents) * _concurrents
			if _current_numpool < 2:
				_current_numpool = 2 # minmum	
			if _debug:
				print (">>>>>>>>>>>> resize numpool %d" % _current_numpool)
			break
		
		el = item [0]
		if _currents.get (el.uinfo.netloc, 0) < _concurrents:
			try: 
				_currents [el.uinfo.netloc] += 1
			except KeyError:
				_currents [el.uinfo.netloc] = 1
			indexes.append (index)
			lm += 1
		index += 1
	
	if _debug:
		print (">>>>>>>>>>>> numpool:%d in map:%d queue:%d" % (_current_numpool, len (_map), len (_que)))
	
	pup = 0
	for index in indexes:
		item = _que.pop (index - pup)
		Item (*item)		
		pup += 1

	if pup:
		# for multi threading mode
		trigger.the_trigger.pull_trigger ()
	
	return pup	

def get_all ():
	import time
	global _use_lifetime, _map, _que, _logger, _concurrent, _current_numpool, _latest
	
	if not _que:
		_logger ("[warn] no item to get")
		return
	
	for i in range (_current_numpool):
		if not maybe_pop ():
			break
	
	if not _use_lifetime: 
		return
	
	try:
		lifetime.loop (3.0)
	finally:	
		socketpool.cleanup ()	
		# reset for new session
		_current_numpool = _max_numpool
		_latest = ""
	

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


class HTTPRequest (http_request.HTTPRequest):
	def __init__ (self, rql, logger = None):		
		self.rql = rql		
		url = self.rql.uinfo.rfc
		method = self.rql.uinfo.method.upper ()
		http_request.HTTPRequest.__init__ (self, url, method, headers = self.rql.get_headers (), logger = logger)
			
	def split (self, uri):
		return (self.rql.uinfo.netloc, self.rql.uinfo.port), self.rql.uinfo.uri
		
	def serialize (self):
		pass
		
	def get_auth (self):
		return self.rql.hconf.auth
			
	def get_data (self):
		if self.rql.uinfo.scheme in ("ws", "wss"): return b""
		return self.rql.uinfo.data is not None and self.rql.uinfo.data.encode ("utf8") or b""

	def get_rql (self):
		return self.rql
	
	def get_useragent (self):
		return self.rql.hconf.user_agent
		

class WSRequest (HTTPRequest, ws_request.Request):
	def __init__ (self, rql, logger = None):
		self.rql = rql
		ws_request.Request.__init__ (self, self.rql.uinfo.rfc, self.uinfo.data, self.hconf.opcode, self.hconf.auth, logger = logger)
		
		
class Item:
	def __init__ (self, thing, callback, logger = None):
		global _logger, _timeout
		
		if localstorage.g is None:
			configure (logger)
		
		if strutil.is_str_like (thing):
			self.rql = rql.RQL (thing)
		else:
			self.rql = thing
			
		if logger:
			self.logger = logger			
		else:
			self.logger = _logger
		self.callback = callback
		
		if self.rql.uinfo.scheme in ("ws", "wss"):
			self.rql.uinfo.connection = "keep-alive, Upgrade"			
			self.rql.to_version_11 ()
			request = WSRequest (self.rql, logger = self.logger)
			# websocket proxy should be tunnel
			if self.rql.hconf.proxy:
				self.rql.hconf.tunnel = self.rql.hconf.proxy
				del self.rql.hconf.proxy
			if self.rql.hconf.tunnel:
				if self.rql.uinfo.scheme == 'wss':
					handler_class = WSSSLProxyTunnelHandler				
				else:
					handler_class = WSProxyTunnelHandler		
			else:
				handler_class = ws_request_handler.RequestHandler
				
		else:
			request = HTTPRequest (self.rql, logger = self.logger)
			if self.rql.hconf.tunnel:		
				request.rql.to_version_11 ()
				handler_class = SSLProxyTunnelHandler
			else:	
				handler_class = http_request_handler.RequestHandler
			
		sp = socketpool.socketpool		
		if self.rql.hconf.tunnel:
			asyncon = sp.get ("proxys://%s" % self.rql.hconf.tunnel)
		elif self.rql.hconf.proxy:
			asyncon = sp.get ("proxy://%s" % self.rql.hconf.proxy)
		else:
			asyncon = sp.get (request.rql.uinfo.rfc)
					
		handler_class (asyncon, request, self.callback_wrap, request.rql.hconf.version, request.rql.hconf.connection).start ()
	
	def handle_websocket (self, handler):
		if handler.response.code == 101:
			request = WSRequest (handler.request.rql, logger = self.logger)
			ws_request_handler.RequestHandler (asyncon, request, self.callback_wrap).start ()
		
	def callback_wrap (self, handler):
		global _latest
	
		r = rc.ResponseContainer (handler, self.callback)
		_latest = r.uinfo.netloc
		# unkink back refs
		handler.asyncon = None
		handler.callback = None
		handler.response = None
		handler.request = None
		del handler
		
		try:
			self.callback (r)		
		except:
			_logger.trace ()
		maybe_pop ()
