import base64
from hashlib import md5
import re
try:
	from urllib.parse import urlparse, quote_plus	, unquote_plus
except ImportError:
	from urlparse import urlparse
	from urllib import quote_plus, unquote_plus	
import time
from skitai.protocol.http import util

DEBUG = False
if not DEBUG:
	from . import localstorage

MAX_MOVED = 5
KEYWORDS = ('from', "label", "with")
LONGOPTS = ('cookie', 'user-agent', 'version', 'auth', 'proxy', 'tunnel', 'content-type', 'connection', 'opcode')
HEARES_NOT_ALLOWED = ("cookie", "content-type", "connection", "referer")
METHODS = ("get", "post", "head", "put", "delete", "options", "trace", "connect", "upload")
DEFAULT_PORT_MAP = {'http': 80, 'https': 443, 'ws': 80, 'wss': 443}
NON_IP_COMPONENT = re.compile ("[^.0-9]")

class UserData:
	def __getattr__ (self, n):
		return None
	
class HTTPOptions (UserData):
	version = "1.1"
	connection = "close"
	user_agent = "Mozilla/5.0 (compatible; Skitaibot/0.1a)"
	headers = {"Cache-Control": "max-age=0"}

class Attributes (UserData):
	depth = 0
	retrys = 0
	moved = []

	
class RQL:	
	def __init__ (self, rql):
		self.rql = rql
		self.udata = UserData ()
		self.hconf = HTTPOptions ()
		self.uinfo = Attributes ()
		self.__verson_changed = False
		self.parse ()
	
	def __str__ (self):
		return self.uinfo.rfc
	
	def get_headers (self):
		h = list (self.hconf.headers.items ())
		if self.hconf.cookie:
			h.append (("Cookie", self.hconf.cookie))
		if self.uinfo.referer:
			h.append (("Referer", self.uinfo.referer))
		return dict (h)
	
	def check_end_quote (self, quote, token):
		if token and token [-1] == quote and (len (token) == 1 or token [-2] != "\\"):
			token = token [:-1].replace ("\\" + quote, quote)
			quote = None
		else:	
			token = token.replace ("\\" + quote, quote)
		return quote, token
		
	def parse (self):
		if not self.rql.strip ():
			raise AssertionError ("Empty RQL")
		
		d = {}
		current_key = None
		current_quote = None
		
		for token in self.rql.split(" "):
			if not token and (current_key is None or not d [current_key]):
				continue
			
			if current_quote is not None:
				current_quote, token = self.check_end_quote (current_quote, token)
				d[current_key] += ' ' + token
				continue
				
			tk = token.lower()
			if tk in KEYWORDS or tk in METHODS:				
				current_key = tk
				d [current_key] = ''
			
			elif tk [:2] in ("--"):
				got_long_opt = True
				current_key = token				
				d[current_key] = ''
					
			else:
				try: 
					if d[current_key]:
						d[current_key] += ' ' + token
												
					else:
						if token [0] in "\"'":
							current_quote = token [0]
							token = token [1:]
							current_quote, token = self.check_end_quote (current_quote, token)
						d[current_key] = token
							
				except KeyError:
					current_key = 'get'					
					d[current_key] = token
		
		if current_quote:
			raise AssertionError ("Quotes Not Matched")
			
		self.analyze (d)
		self.set_attributes ()
		
	def set_referer (self, url, page_id = None):
		self.uinfo.referer = url
		self.uinfo.referer_id = page_id		
			
	def analyze (self, d):
		for k, v in d.items ():
			v = v.strip ()
			if k [:2] == "--":
				if k.startswith ("--head-"):
					hkey = k [7:]
					if hkey.lower () in HEARES_NOT_ALLOWED:
						raise AssertionError ("Not Allowed '%s' Header" % hkey)
					self.hconf.headers [hkey] = v
				
				elif k [2:] in LONGOPTS:
					# LONGOPTS = ('cookie', 'user-agent', 'version', 'auth', 'proxy', 'tunnel', 'content-type', 'connection')
					okey = k [2:]
					if okey == "cookie":
						if not DEBUG:
							localstorage.g.set_cookie_from_data (self.uinfo.rfc, v)
					elif okey == "user-agent":
						self.hconf.user_agent = v					
					elif okey == "content-type":
						self.hconf.content_type = v
					elif okey == "connection":
						self.hconf.connection = v
					else:
						setattr (self.hconf, okey, v)
				
				else:
					if k [-4:] == ":int":
						setattr (self.udata, k [2:-4], int (v))
					else:
						setattr (self.udata, k [2:], v)
							
			else:	
				if k in METHODS:
					self.uinfo.method = k
					if v.find ("://") == -1:
						v = "http://" + v # assume
					self.uinfo.url = v					
				elif k == "label":
					self.uinfo.label = v
				elif k == "from":
					self.set_referer (v)					
				elif k == "with":	
					self.uinfo.data = v
		
	def get_header (self, name, default = None):
		name = name.lower ()
		for k, v in self.hconf.headers.items ():
			if k.lower () == name:
				return v
		return default
		
	def set_attributes (self):
		url = self.uinfo.url
		self.uinfo.scheme, self.uinfo.netloc, self.uinfo.script, self.uinfo.params, self.uinfo.querystring, self.uinfo.fragment = urlparse (url)
		if self.uinfo.data and self.uinfo.method not in ("post", "put"):
			raise ValueError ("Form exists but method isn't post or get")
		if self.uinfo.method in ("post", "put") and not self.uinfo.data:
			raise ValueError ("No form data")
		if not self.uinfo.data and self.hconf.content_type:
			raise ValueError ("Needn't content-type")
		if self.uinfo.data and self.uinfo.method == "post" and self.hconf.content_type is None:
			self.hconf.content_type = "application/x-www-form-urlencoded; charset=utf-8"		
			
		if not self.uinfo.script: 
			self.uinfo.script = '/'
		if self.uinfo.querystring:
			try: self.uinfo.querystring = uitl.strencode (self.uinfo.querystring)
			except: pass
		
		uri = self.uinfo.script #real request uri
		if self.uinfo.params:
			uri += ';' + self.uinfo.params
		if self.uinfo.querystring:
			uri += '?' + self.uinfo.querystring
		self.uinfo.uri = uri
		
		position = self.uinfo.netloc.find('@')
		if position > -1:
			self.hconf.auth, self.uinfo.netloc = self.uinfo.netloc.split ("@", 1)
		
		if self.hconf.auth:
			if self.get_header ("authorization"):
				raise ValueError ("Authorization Information Conflict")
				
			try: 
				self.hconf.username, self.hconf.password = self.hconf.auth.split (':', 1)
			except ValueError:	
				pass
			else:	
				self.hconf.auth = (self.hconf.username, self.hconf.password)

		try:
			self.uinfo.netloc, self.uinfo.port = self.uinfo.netloc.split (':', 1)
		except ValueError:
			try:
				self.uinfo.netloc, self.uinfo.port = self.uinfo.netloc, DEFAULT_PORT_MAP [self.uinfo.scheme]
			except KeyError:
				raise ValueError ("Unknown URL Scheme")
		
		self.uinfo.netloc = self.uinfo.netloc.lower ()
		try: self.uinfo.port = int (self.uinfo.port)
		except: self.uinfo.port = 80
		
		if NON_IP_COMPONENT.search (self.uinfo.netloc):
			netloc = self.uinfo.netloc
			netloc2 = netloc.split (".")
			self.uinfo.topdomain = netloc2 [-1]
			
			if len (netloc2) == 1:
				self.uinfo.host = ""	
				self.uinfo.domain = netloc
				self.uinfo.subdomain = netloc				
			elif len (netloc2) == 2:
				self.uinfo.host = ""	
				self.uinfo.domain = netloc
				self.uinfo.subdomain = netloc2 [0]				
			elif len (netloc2 [-1]) >= 3:
				self.uinfo.domain = ".".join (netloc2 [-2:])
				self.uinfo.host = ".".join (netloc2 [:-2])
				self.uinfo.subdomain = netloc2 [-2]			
				if not self.uinfo.host:
					self.uinfo.host = "www"
			elif len (netloc2 [-1]) == 2:
				if len (netloc2) == 2:
					self.uinfo.domain = ".".join (netloc2)
					self.uinfo.subdomain = netloc2 [0]
					self.uinfo.host = "www"
				elif len (netloc2) == 3:
					if netloc2 [0] == "www":
						self.uinfo.domain = ".".join (netloc2 [-2:])
						self.uinfo.subdomain = netloc2 [-2]
					else:
						self.uinfo.domain = ".".join (netloc2)
						self.uinfo.subdomain = netloc2 [0]
					self.uinfo.host = "www"
				else:
					self.uinfo.domain = ".".join (netloc2 [-3:])
					self.uinfo.host = ".".join (netloc2 [:-3])
					self.uinfo.subdomain = netloc2 [-3]
		
		if DEFAULT_PORT_MAP [self.uinfo.scheme] == self.uinfo.port:
			self.uinfo.rfc = '%s://%s%s' % (self.uinfo.scheme, self.uinfo.netloc, self.uinfo.uri)
		else:
			self.uinfo.rfc = '%s://%s:%d%s' % (self.uinfo.scheme, self.uinfo.netloc, self.uinfo.port, self.uinfo.uri)	
		self.uinfo.page_id = self.geneate_page_id ()
		self.uinfo.path_id = self.geneate_page_id (False)
		if not DEBUG and localstorage.g:
			self.hconf.cookie = localstorage.g.get_cookie_as_string (self.uinfo.rfc)		
		
	def to_version_11 (self):
		self.hconf.version = "1.1"
		if self.hconf.connection and self.hconf.connection.lower () == "close":
			del self.hconf.connection
		self.__verson_changed = True
	
	def inc_retrys (self):
		self.uinfo.retrys += 1
	
	def dec_retrys (self):
		self.uinfo.retrys -= 1
				
	def inherit (self, rql, moved = False):
		new = RQL (rql)
				
		if moved:
			if len (self.uinfo.moved) >= MAX_MOVED:
				raise AssertionError ("Maximum Moved Exceeded")
			new.uinfo.moved = self.uinfo.moved + [self.uinfo.page_id]
			if new.uinfo.page_id in new.uinfo.moved:
				raise AssertionError ("Moved Recursively")
		else:
			new.uinfo.depth = self.uinfo.depth + 1
					
		# inherit user-data
		for k in dir (self.udata):
			if k not in dir (new.udata): # prevent overwriting
				setattr (new.udata, k, getattr (self.udata, k))
		
		# inherit options
		for k in dir (self.hconf):
			if k in ("cookie", "content-type"):
				continue # no need, managed by local storage
			elif k == "headers":
				for k2, v2 in self.hconf.headers.items ():
					if k2 not in new.hconf.headers:
						new.hconf.headers [k2] = v2						
			elif k not in dir (new.hconf): # prevent overwriting
				setattr (new.hconf, k, getattr (self.hconf, k))
						
		if self.__verson_changed:
			new.to_version_11 ()
				
		# inherit attributes		
		new.set_referer (self.uinfo.rfc, self.uinfo.page_id)							
		return new
	
	def get_connection (self):
		return self.hconf.connection
				
	def get_useragent (self):
		return self.hconf.user_agent
	
	def __sort_args (self, data):
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

	def geneate_page_id (self, include_data = True):		
		signature = [
			self.uinfo.method,
			self.uinfo.netloc.startswith ("www.") and self.uinfo.netloc [4:] or self.uinfo.netloc, 
			str (self.uinfo.port), 
			self.uinfo.script
		]
		if include_data:
			signature.append (self.uinfo.params)
			if self.uinfo.querystring:
				signature.append (self.__sort_args (self.uinfo.querystring))
			if self.uinfo.data:
				signature.append (self.__sort_args (self.uinfo.data))
		return md5 (":".join (signature).encode ("utf8")).hexdigest ()
		
	def show (self):
		for d in ("udata", "uinfo", "hconf"):
			o = getattr (self, d)
			print (d, "\n======")
			for k in dir (o):
				if k [:2] == "__": continue
				print("-%s: %s" % (k, getattr (o, k)))
			print ()	
					

def make_page_id (url):
	return RQL (url).uinfo.page_id
make_pid = 	make_page_id

def make_path_id (url):
	return RQL (url).uinfo.path_id
	
def norm_space (s):
		return re.sub ("\s+", " ", s)	
		
def encode (s):	
	return quote_plus (s)
	
def decode (s):
	return unquote_plus (s)
				

if __name__ == "__main__":
	f = RQL ("from referer get http://url.com --useragent 'fire\\' fox --connection close' --header-Content-Type 'text/html' --id ''")
	f.show ()
	
