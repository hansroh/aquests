import threading, random
from . import asynconnect, synconnect
import time
try:
	from urllib.parse import urlparse
except ImportError:
	from urlparse import urlparse	
import copy
from ..protocols.http2 import H2_PROTOCOLS
from ..protocols import http2

PROTO_CONCURRENT_STREAMS = H2_PROTOCOLS

def select_channel (asyncons):
	asyncon = None
	_asyncons = []
	
	for each in asyncons:
		if each.isactive ():
			continue
		if not each.isconnected ():
			_asyncons = [(each, 0)]
			break
			
		if each.handler is not None:			
			_asyncons.append ((each, each.handler.jobs ()))
	
	if _asyncons:
		_asyncons.sort (key = lambda x: x [1])		
		if _asyncons [0][1] < http2.MAX_HTTP2_CONCURRENT_STREAMS:
			asyncon = _asyncons [0][0]
	
	return asyncon
	

class SocketPool:
	object_timeout = 120
	maintern_interval = 30
	use_syn_connection = False
	ctype = None

	def __init__ (self, logger, backend = False, use_pool = True):
		self.__socketfarm = {}
		self.__protos = {}
		self.__numget  = 0
		self.__last_maintern = time.time ()
		self.logger = logger
		self.backend = backend
		self.use_pool = use_pool
		self.lock = threading.RLock ()
		self.numobj = 0
	
	def match (self, request):
		return False		
	
	def get_name (self):
		return "__socketpool__"
				
	def status (self):
		info = {}
		cluster = {}
		info ["numget"] = self.__numget
				
		try:
			with self.lock:
				for serverkey, node in list(self.__socketfarm.items ()):	
					nnode = {}
					nnode ["numactives"] = len ([x for x in list(node.values ()) if x.isactive ()])
					nnode ["numconnecteds"] = len ([x for x in list(node.values ()) if x.isconnected ()])
					conns = []
					for asyncon in list(node.values ()):
						stu = {
							"class": asyncon.__class__.__name__, 
							"connected": asyncon.isconnected (), 
							"isactive": asyncon.isactive (), 
							"request_count": asyncon.get_request_count (),
							"event_time": time.asctime (time.localtime (asyncon.event_time)), 
							"zombie_timeout": asyncon.zombie_timeout,								
						}
						try: stu ["has_result"] = asyncon.has_result
						except AttributeError: pass						
						
						if hasattr (asyncon, "get_history"):
							stu ["history"] = asyncon.get_history ()
							
						try:
							stu ["in_map"] = asyncon.is_channel_in_map ()
						except AttributeError: 
							pass	
							
						conns.append (stu)
													
					nnode ["connections"] = conns
					cluster [serverkey] = nnode
			
		except:
			self.logger.trace ()
					
		info ["cluster"] = cluster
		return info
		
	def report (self, asyncon, well_functioning):
		pass # for competitable
	
	def get_nodes (self):
		with self.lock:
			if not self.__socketfarm: return [None] # at least one item needs
			return list(self.__socketfarm.items ())
		
	def maintern (self):
		# close unused sockets				
		for serverkey, node in list (self.__socketfarm.items ()):
			for _id, asyncon in list (node.items ()):
				if not hasattr (asyncon, "maintern"):
					continue
				
				try:
					deletable = asyncon.maintern (self.object_timeout)
				except:
					self.logger.trace ()
				else:
					if deletable:
						asyncon.handler = None # break back ref.
						try: del node [_id]
						except KeyError: pass
						self.numobj -= 1
			
			# KeyError, WHY?
			if not node:
				try: del self.__socketfarm [serverkey]
				except KeyError: pass						
				try: del self.__protos [serverkey]
				except KeyError: pass
		
		self.logger ('mainterned %d socket pool' % len (self.__socketfarm), 'info')
				
	def _get (self, serverkey, server, *args):
		asyncon = None	
		if self.use_pool and time.time () - self.__last_maintern > self.maintern_interval:
			self.__last_maintern = time.time ()
			try:				
				self.maintern ()
			except:
				self.logger.trace ()
					
		self.__numget += 1
		if not self.use_pool:
			asyncon = self.create_asyncon (server, *args)
			
		else:	
			if serverkey not in self.__socketfarm:
				self.__socketfarm [serverkey] = {}
				asyncon = self.create_asyncon (server, *args)
				self.__socketfarm [serverkey][id (asyncon)] = asyncon
				
			else:		
				asyncons = list(self.__socketfarm [serverkey].values ())
				if self.__protos.get (serverkey) in PROTO_CONCURRENT_STREAMS:
					asyncon = select_channel (asyncons)
					
				else:
					for each in asyncons:								
						if not each.isactive ():
							asyncon = each
							break
				
				if not asyncon:
					asyncon = self.create_asyncon (server, *args)
					self.__socketfarm [serverkey][id (asyncon)] = asyncon
			
			proto = self.__protos.get (serverkey)
			if not proto and asyncon.get_proto ():
				self.__protos [serverkey] = asyncon.get_proto ()
				
		asyncon.set_active (True)		
		return asyncon
	
	def create_asyncon (self, server, scheme):		
		if scheme in ("https", "wss"):
			__conn_class = asynconnect.AsynSSLConnect
			__dft_Port = 443
		elif scheme == "tunnel":
			__conn_class = asynconnect.AsynConnect
			__dft_Port = 443
		elif scheme == "proxy":
			__conn_class = asynconnect.AsynConnect			
			__dft_Port = 5000
		elif scheme == "proxys":
			__conn_class = asynconnect.AsynSSLProxyConnect
			__dft_Port = 5000				
		else:
			__conn_class = asynconnect.AsynConnect
			__dft_Port = 80

		if self.use_syn_connection:
			if scheme == "https":
				__conn_class = synconnect.SynSSLConnect
			elif scheme == "http":	
				__conn_class = synconnect.SynConnect
		try:
			addr, port = server.split (":", 1)
			port = int (port)
		except ValueError:
			addr, port = server, __dft_Port
		
		self.numobj += 1			
		asyncon = __conn_class ((addr, port), self.lock, self.logger)	
		self.backend and asyncon.set_backend ()
		asyncon.set_proxy (scheme == "proxy")
		return asyncon
				
	def get (self, uri):		
		scheme, server, script, params, qs, fragment = urlparse (uri)
		serverkey = "%s://%s" % (scheme, server)
		try:
			with self.lock:
				return self._get (serverkey, server, scheme)
		except:
			self.logger.trace ()
			return None
			
	def noop (self):
		if not self.use_pool:
			return 
			
		with self.lock:
			for server in list(self.__socketfarm.keys ()):					
				for asyncon in list(self.__socketfarm [server].values ()):
					asyncon.set_event_time ()
			
	def cleanup (self):
		if not self.use_pool:
			return 
			
		try:
			with self.lock:
				for server in list(self.__socketfarm.keys ()):					
					for asyncon in list(self.__socketfarm [server].values ()):
						asyncon.disconnect ()
						del asyncon
				self.__socketfarm = {}
				self.__protos = {}
							
		except:
			self.logger.trace ()


pool = None

def create (logger, backend = False, use_pool = True):
	global pool
	if pool is None:
		pool = SocketPool (logger, backend, use_pool)

def get (uri):	
	return pool.get (uri)
		
def cleanup ():	
	pool.cleanup ()

def noop ():
	pool.noop ()
	