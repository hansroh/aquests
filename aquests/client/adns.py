from ..protocols.dns import asyndns
import time

class DNSCache:
	def __init__ (self, logger = None, dns_servers = []):		
		self.dns = asyndns.Request (logger)
		self.logger = logger
		self.dns_servers = dns_servers
		self.cache = {}
		self.hits = 0

	def set (self, answers):		
		if not answers:
			return

		for answer in answers:
			name = answer ["name"].lower ()
			if name not in self.cache:
				self.cache [name] = {}
			if "ttl" in answer:
				answer ["valid"]	= time.time () + answer ["ttl"]
			self.cache [name][answer ["typename"]] = [answer]
		
	def expire (self, host):
		try: del self.cache [host]
		except KeyError: pass		

	def get (self, host, qtype = "A", check_ttl = True):	
		host = host.lower ()
		try: answers = self.cache [host][qtype]
		except KeyError: return []
		answer = answers [0]
		if "valid" not in answer:
			return [answer]
		else:
			now = time.time ()
			if check_ttl and answer ["valid"] < now:				
				# use max 5 minutes seconds for other querees
				answer ['valid'] = now + 300
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
