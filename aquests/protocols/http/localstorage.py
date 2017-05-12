import base64
import random
try:
	from urllib.parse import urlparse
except ImportError:
	from urlparse import urlparse	
from . import util

g = None

def create (logger):
	global g
	g = LocalStorage (logger)

class LocalStorage:
	def __init__ (self, logger):
		self.logger = logger
		self.cookie = {}
		self.data = {}		
	
	def get_host (self, url):
		return urlparse (url) [1].split (":") [0].lower ()
	
	def set_item (self, url, key, val):
		host = self.get_host (url)
		if host not in self.data:
			self.data = {}
		self.data [key] = val
	
	def get_item (self, url, key):
		host = self.get_host (url)
		try:
			return self.data [host][key]
		except KeyError:
			return 
		
	def get_cookie_as_list (self, url):
		cookie = []
		for domain in self.cookie:
			netloc, script = urlparse (url) [1:3]
			netloc = netloc.lower ()	
			if ("." + netloc).find (domain) > -1:
				for path in self.cookie [domain]:
					if script.find (path) > -1:						
						cookie += list(self.cookie [domain][path].items ())
		return cookie
	
	def get_cookie_as_dict (self, url):	
		cookie = self.get_cookie_as_list (url)		
		dict = {}
		if cookie:
			for k, v in cookie:
				dict [k] = v
		return dict
		
	def get_cookie (self, url, key):
		d = self.get_cookie_as_dict ()
		try:
			return d [key]
		except KeyError:
			return None
		
	def get_cookie_as_string (self, url):
		cookie = self.get_cookie_as_list (url)
		if cookie:
			return "; ".join (["%s=%s" % (x, y) for x, y in cookie])			
		return ""
		
	def set_cookie_from_data (self, url, cookie):
		host = self.get_host (url)
		self.cookie [host] = {}
		self.cookie [host]["/"] = {}
		
		if type (cookie) != type ([]):
			cookie = util.strdecode (cookie, 1)
					
		for k, v in cookie:
			self.cookie [host]["/"][k] = v
	
	def clear_cookie (self, url):
		url = url.lower ()
		for domain in list(self.cookie.keys ()):
			if url.find (domain) > -1:
				del self.cookie [domain]				
	
	def set_cookie (self, url, key, val, domain = None, path = "/"):
		if domain is None:
			domain = self.get_host (url)
		try: self.cookie [domain]
		except KeyError: self.cookie [domain] = {}
		try: self.cookie [domain][path]
		except KeyError: self.cookie [domain][path] = {}					
		self.cookie [domain][path][key] = val
	
	def del_cookie (self, url, key):
		if domain is None:
			domain = self.get_host (url)
		try: self.cookie [domain]
		except KeyError: return		
		try: self.cookie [domain][path]
		except KeyError: return
		for path in self.cookie [domain]:
			del self.cookie [domain][path][key]
		
	def set_cookie_from_string (self, url, cookiestr):
		host = self.get_host (url)
		ckey, cval = '', ''				
		s = {}
		count = 0
		for element in cookiestr.split (";"):
			try: 
				k, v = element.split ("=", 1)
			except:
				k, v = element, ''
			
			if count == 0:			
				if v.find ("%") != -1:
					ckey, cval = k.strip (), v.strip ()
				else:
					ckey, cval = k.strip (), v.strip ()
			else:
				s [k.strip ().lower ()] = v.strip ().lower ()
				
			count += 1
		
		try: domain = s ['domain']
		except KeyError: domain = host
		try: path = s ['path']
		except KeyError: path = '/'
		
		try: self.cookie [domain]
		except KeyError: self.cookie [domain] = {}
		try: self.cookie [domain][path]
		except KeyError: self.cookie [domain][path] = {}
					
		self.cookie [domain][path][ckey] = cval			
