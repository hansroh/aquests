from hashlib import md5
from urllib.parse import urlparse
from . import util
import re

DEFAULT_PORT_MAP = {'http': 80, 'https': 443, 'ws': 80, 'wss': 443}
NON_IP_COMPONENT = re.compile ("[^.0-9]")

def sort_args (data):
	args = {}
	for arg in data.split ("&"):
		try: k, v = arg.split ("=")
		except: continue
		if v:
			args [k] = v
	args = list(args.items ())
	args.sort ()
	argslist = []
	for k, v in args:
		argslist.append ("%s=%s" % (k, v))		
	argslist.sort ()		
	return "&".join (argslist)

def parse_address (scheme, address):
	try: 
		host, port = address.split (":", 1)
		port = int (port)
	except ValueError:
		host = address
		if scheme in ("http", "ws"):
			port = 80
		else:
			port = 443	
	return host, port
	
def uuid (uri, method = "get", data = "", include_data = True):
	# url id
	if uri.find ("://") == -1:
		return None
	method = method.lower ()
	scheme, address, script, params, qs, fragment = urlparse (uri)
	
	if not script: 
		script = "/"
	host, port = parse_address (scheme, address)		
	sig = [
		method,
		host.startswith ("www.") and host [4:] or host, 
		str (port),
		script
	]
	if include_data:
		sig.append (params)
	if qs:
		sig.append (sort_args (qs))
	if data:
		sig.append (sort_args (data))
	return md5 (":".join (sig).encode ("utf8")).hexdigest ()

def usid (uri, method = "get"):	
	# script id
	return make_uuid (uri, method, "", False)

def uinf (url):
	return UrlInfo (url)

	
class UrlInfo:	
	def __init__ (self, url):
		self.url = url
		self._parse ()
		
	def _parse (self):
		url = self.url
		self.scheme, self.netloc, self.script, self.params, self.querystring, self.fragment = urlparse (url)
		
		if not self.script: 
			self.script = '/'
		if self.querystring:
			try: self.querystring = util.strencode (self.querystring)
			except: pass
		
		uri = self.script #real request uri
		if self.params:
			uri += ';' + self.params
		if self.querystring:
			uri += '?' + self.querystring
		self.uri = uri
		
		position = self.netloc.find('@')
		if position > -1:
			self.auth, self.netloc = self.netloc.split ("@", 1)		
			try: 
				self.username, self.password = self.auth.split (':', 1)
			except ValueError:	
				pass
			else:	
				self.auth = (self.username, self.password)

		try:
			self.netloc, self.port = self.netloc.split (':', 1)
		except ValueError:
			try:
				self.netloc, self.port = self.netloc, DEFAULT_PORT_MAP [self.scheme]
			except KeyError:
				self.netloc, self.port = self.netloc, 80
		
		self.netloc = self.netloc.lower ()
		try: self.port = int (self.port)
		except: self.port = 80
		
		if DEFAULT_PORT_MAP [self.scheme] == self.port:
			self.rfc = '%s://%s%s' % (self.scheme, self.netloc, self.uri)
		else:
			self.rfc = '%s://%s:%d%s' % (self.scheme, self.netloc, self.port, self.uri)
			
		self.host = None
		self.domain = None
		self.subdomain = None
		self.topdomain = None
		
		if NON_IP_COMPONENT.search (self.netloc):
			netloc = self.netloc
			netloc2 = netloc.split (".")
			self.topdomain = netloc2 [-1]
			
			if len (netloc2) == 1:
				self.host = ""	
				self.domain = netloc
				self.subdomain = netloc				
			elif len (netloc2) == 2:
				self.host = ""	
				self.domain = netloc
				self.subdomain = netloc2 [0]				
			elif len (netloc2 [-1]) >= 3:
				self.domain = ".".join (netloc2 [-2:])
				self.host = ".".join (netloc2 [:-2])
				self.subdomain = netloc2 [-2]			
				if not self.host:
					self.host = "www"
			elif len (netloc2 [-1]) == 2:
				if len (netloc2) == 2:
					self.domain = ".".join (netloc2)
					self.subdomain = netloc2 [0]
					self.host = "www"
				elif len (netloc2) == 3:
					if netloc2 [0] == "www":
						self.domain = ".".join (netloc2 [-2:])
						self.subdomain = netloc2 [-2]
					else:
						self.domain = ".".join (netloc2)
						self.subdomain = netloc2 [0]
					self.host = "www"
				else:
					self.domain = ".".join (netloc2 [-3:])
					self.host = ".".join (netloc2 [:-3])
					self.subdomain = netloc2 [-3]
		