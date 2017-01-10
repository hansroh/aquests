import threading, random
from . import asynconnect
import time
try:
	from urllib.parse import urlparse
except ImportError:
	from urlparse import urlparse	
import copy
from aquests.protocols.http2 import H2_PROTOCOLS

PROTO_LOADBALANCE = H2_PROTOCOLS


class SocketPool:
	object_timeout = 120
	maintern_interval = 30
	
	def __init__ (self, logger):
		self.__socketfarm = {}
		self.__protos = {}
		self.__numget  = 0
		self.__last_maintern = time.time ()
		self.logger = logger
		self.lock = threading.RLock ()
		self.numobj = 0
	
	def match (self, request):
		return False		
	
	def get_name (self):
		return "__socketpool__"
				
	def status (self):
		info = {}
		cluster = {}
		self.lock.acquire ()
		info ["numget"] = self.__numget
				
		try:
			try:	
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
					
			finally:
				self.lock.release ()
				
		except:
			self.logger.trace ()
					
		info ["cluster"] = cluster
		return info
		
	def report (self, asyncon, well_functioning):
		pass # for competitable
	
	def get_nodes (self):
		if not self.__socketfarm: return [None] # at least one item needs
		return list(self.__socketfarm.items ())
		
	def maintern (self):		
		# close unused sockets
		for serverkey, node in list(self.__socketfarm.items ()):
			for _id, asyncon in list(node.items ()):					
				if not hasattr (asyncon, "maintern"):
					continue
				
				try:
					deletable = asyncon.maintern (self.object_timeout)					
				except:
					self.logger.trace ()
				else:
					if deletable:
						del self.__socketfarm [serverkey][_id]
						del asyncon
						self.numobj -= 1														
			
			if not self.__socketfarm [serverkey]:
				del self.__socketfarm [serverkey]
				
		self.__last_maintern = time.time ()
	
	def _get (self, serverkey, server, *args):
		asyncon = None
		self.lock.acquire ()
		try:
			try:
				if time.time () - self.__last_maintern > self.maintern_interval:					
					self.maintern ()
							
				self.__numget += 1
				if serverkey not in self.__socketfarm:
					asyncon = self.create_asyncon (server, *args)
					self.__socketfarm [serverkey] = {}
					self.__socketfarm [serverkey][id (asyncon)] = asyncon
					
				else:		
					proto = self.__protos.get (serverkey)
					asyncons = list(self.__socketfarm [serverkey].values ())
					if proto in PROTO_LOADBALANCE:
						random.shuffle (asyncons)
												
					for each in asyncons:	
						if not each.isactive ():
							asyncon = each
							break
					
					if not asyncon:
						asyncon = self.create_asyncon (server, *args)
						self.__socketfarm [serverkey][id (asyncon)] = asyncon
				
				asyncon.set_active (True)
			
			finally:
				self.lock.release ()
		
		except:
			self.logger.trace ()
		
		proto = self.__protos.get (serverkey)
		if not proto and asyncon.get_proto ():
			self.__protos [serverkey] = asyncon.get_proto ()
									
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
		
		try:
			addr, port = server.split (":", 1)
			port = int (port)
		except ValueError:
			addr, port = server, __dft_Port
		
		self.numobj += 1			
		asyncon = __conn_class ((addr, port), self.lock, self.logger)	
		asyncon.set_proxy (scheme == "proxy")
		return asyncon
				
	def get (self, uri):	
		scheme, server, script, params, qs, fragment = urlparse (uri)
		serverkey = "%s://%s" % (scheme, server)		
		return self._get (serverkey, server, scheme)
		
	def cleanup (self):
		self.lock.acquire ()
		try:
			try:
				for server in list(self.__socketfarm.keys ()):					
					for asyncon in list(self.__socketfarm [server].values ()):
						asyncon.disconnect ()
			finally:
				self.lock.release ()
		except:
			self.logger.trace ()


pool = None

def create (logger):
	global pool
	if pool is None:
		pool = SocketPool (logger)

def get (uri):	
	return pool.get (uri)
		
def cleanup ():	
	pool.cleanup ()
