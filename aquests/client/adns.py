from ..protocols import dns
import time
import threading
import os

class DNSCache:
	maintern_interval = 17
	too_many_errors = 3
	def __init__ (self, prefer_protocol, logger = None):
		self.logger = logger
		self.prefer_protocol = prefer_protocol
		self.__last_maintern = time.time ()
		self.__lock = threading.RLock ()
		self.cache = {"localhost": {"data": "127.0.0.1", "valid": 2**32, "typename": "A"}}
		self.errors = {} 
		self.hits = 0

	def set (self, answers):
		if not answers [-1]["data"]:
			name = answers [0]["name"]
			if name not in self.errors:
				self.errors [name] = 1
			else:
				self.errors [name] += 1	
			return		
		
		with self.__lock:
			for answer in answers:
				name = answer['name'].lower ()			
				try:
					ttl = int (answer ["ttl"])	
				except (KeyError, ValueError):
					ttl = 1800
				answer ["valid"] = time.time () + max (ttl, 1800)
				if name not in self.cache:					
					self.cache [name] = answer
			
	def expire (self, host):
		with self.__lock:
			try: del self.cache [host]
			except KeyError: pass		
	
	def maintern (self, now):
		deletables = []
		with self.__lock:
			for host in self.cache:			
				ans = self.cache [host]
				if ans ["valid"] < now:
					deletables.append (host)					
			for host in deletables:
				del self.cache [host]
		self.__last_maintern = time.time ()
			
	def get (self, host, qtype = "A", check_ttl = True):
		now = time.time ()
		if now - self.__last_maintern > self.maintern_interval:
			self.maintern (now)

		host = host.lower ()
		with self.__lock:
			while 1:
				try: 
					answer = self.cache [host]
				except KeyError: 
					if self.errors.get (host, 0) >= self.too_many_errors:	
						return [{"name": host, "data": None, "error": "too many error"} ]
					return []
				else:
					tn = answer ['typename']
					if tn == "CNAME":
						host = answer ['data'].lower ()
					elif tn == qtype:	
						break
		
		if check_ttl and answer ["valid"] < now:				
			# extend 30 seconds for other querees
			answer ['valid'] = now + (answer ["data"] and 30 or 1)
			# new query will be started
			return []
			
		else:
			return [answer]
	
	def is_ip (self, name):
		arr = name.split (".")
		if len (arr) != 4: return False
		try: arr = [x for x in map (int, arr) if x & 255 == x]
		except ValueError: 
			return False
		if len (arr) != 4: return False
		return True
		
	def __call__ (self, host, qtype, callback):
		self.hits += 1
		hit = self.get (host, qtype, True)		
		if hit:
			return callback (hit)
		
		if self.is_ip (host):
			self.set ([{"name": host, "data": host, "typename": qtype}])
			return callback ([{"name": host, "data": host, "typename": qtype}])
		
		try:
			dns.query (host, qtype = qtype, protocol = self.prefer_protocol, callback = [self.set, callback])			
		except:
			self.logger.trace (host)
			hit = [{"name": host, "data": None, "typename": qtype, 'ttl': 60}]
			self.set (hit)
			callback (hit)


query = None

def init (logger, dns_servers = [], prefer_protocol = "tcp"):
	dns.create_pool (dns_servers, logger)
	global query
	if query is None:
		query = DNSCache (prefer_protocol, logger)

def get (name, qtype = "A"):	
	global query
	return query.get (name, qtype, False)

