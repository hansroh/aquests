from ..protocols.dns import asyndns
import time
import threading

class DNSCache:
	maintern_interval = 17
	def __init__ (self, logger = None, dns_servers = []):		
		self.dns = asyndns.Request (logger)
		self.logger = logger
		self.dns_servers = dns_servers
		self.__last_maintern = time.time ()
		self.__lock = threading.RLock ()
		self.cache = {}
		self.hits = 0

	def set (self, answers):
		if not answers:
			return

		for answer in answers:
			name = answer ["name"].lower ()
			if not answer ["data"]:
				addrs = self.get (name, answer ["typename"], False)
				if addrs and addrs [0]["data"]:
					return
			
			try:
				ttl = int (answer ["ttl"])	
			except (KeyError, ValueError):
				ttl = 300
			answer ["valid"]	= time.time () + max (ttl, 300)
			
			with self.__lock:
				if name not in self.cache:
					self.cache [name] = {}
				self.cache [name][answer ["typename"]] = [answer]
		
	def expire (self, host):
		with self.__lock:
			try: del self.cache [host]
			except KeyError: pass		
	
	def maintern (self, now):
		deletables = []
		with self.__lock:
			for host in self.cache:
				for qtype in list (self.cache [host]):
					ans = self.cache [host][qtype][0]
					if ans ["valid"] < now:
						self.cache [host][qtype] = None
						del self.cache [host][qtype]
				if not self.cache [host]:
					deletables.append (host)
		
		with self.__lock:
			for host in deletables:
				self.cache [host] = None
				del self.cache [host]
		
		self.__last_maintern = time.time ()
			
	def get (self, host, qtype = "A", check_ttl = True):
		now = time.time ()
		if now - self.__last_maintern > self.maintern_interval:
			self.maintern (now)
		
		#print ('+++++++++++++++++', len(self.cache))
		host = host.lower ()
		with self.__lock:
			try: answers = self.cache [host][qtype]
			except KeyError: return []
		
		answer = answers [0]		
		if check_ttl and answer ["valid"] < now:				
			# extend 30 seconds for other querees
			answer ['valid'] = now + (answer ["data"] and 30 or 1)
			# nut new query will be started
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
			self.dns.req (host, server = self.dns_servers, qtype = qtype, protocol = "tcp", callback = [self.set, callback])
		except:
			self.logger.trace (host)
			hit = [{"name": host, "data": None, "typename": qtype, 'ttl': 60}]
			self.set (hit)
			callback (hit)


PUBLIC_DNS_SERVERS = ['8.8.8.8', '8.8.4.4']
query = None

def init (logger, dns_servers = []):
	if not dns_servers:
		dns_servers = PUBLIC_DNS_SERVERS
	global query
	if query is None:
		query = DNSCache (logger, dns_servers)	

def get (name, qtype = "A"):	
	global query
	return query.get (name, qtype, False)
