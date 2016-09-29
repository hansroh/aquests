"""
2015. 12. 7 Hans Roh


ResponseContainer
	logger
	
	callback
	
	udata
	
	uinfo
		url
		scheme
		path
		script
		params
		querystring
		fragment
		method
		netloc
		domain
		host
		port
		auth
		rfc
		referer
		page_id
		referer_id
		depth
		moved
			
	request	
		version
		connection
		user_agent
		proxy
		header		
		content_type
		encoding
		body
		
	response
		version
		code
		msg
		connection
		header
		content_type
		charset
		body
	
	set_cookie (self, k, v)
	get_cookie (self, k)
	set_item (self, k, v)
	get_item (self, k)
	advance (self, surl)	
	sleep (self, timeout)
			
"""
has_lxml = True
try:
	from . import treebuilder
	import html5lib
except ImportError:
	has_lxml = False
import math		
import json
import time

try:
	import xmlrpclib
except ImportError:
	import xmlrpc.client as xmlrpclib
from . import localstorage
try:
	from urllib.parse import urljoin
except ImportError:
	from urlparse import urljoin	
	
class RCRequest:
	def __init__ (self, obj):
		self._header_cache = {}
		self.set (obj)
		
	def set (self, handler):	
		self.header = handler.header
		self.uri = handler.uri
		self.version = handler.http_version
		self.proxy = handler.request.rql.hconf.proxy
		self.connection = handler.request.rql.hconf.connection
		self.user_agent = handler.request.rql.hconf.user_agent
		
		self.body = handler.request.get_data ()
		self.content_type = handler.request.get_content_type ()
		self.encoding = handler.request.encoding
	
	def get_header_with_attr (self, header, default = None):
		d = {}
		v = self.get_header (header)
		if v is None:
			return default, d
			
		v2 = v.split (";")
		if len (v2) == 1:
			return v, d
		for each in v2 [1:]:
			try:
				a, b = each.strip ().split ("=", 1)
			except ValueError:
				a, b = each.strip (), None
			d [a] = b
		return v2 [0], d	
			
	def get_header (self, header, default = None):
		header = header.lower()
		hc = self._header_cache
		if header not in hc:
			h = header + ':'
			hl = len(h)
			for line in self.header:
				if line [:hl].lower() == h:
					r = line [hl:].strip ()
					hc [header] = r
					return r
			hc [header] = None
			return default
		else:
			return hc[header] is not None and hc[header] or default


class RCResponse (RCRequest):
	def set (self, handler):	
		r = handler.response
		self.__baseurl = handler.request.rql.uinfo.rfc
		self.header = r.header
		self.version, self.code, self.msg = r.version, r.code, r.msg		
		self.content_type = None
		self.charset = None 
		self.__parser, self.__html, self.__etree = None, None, None
		
		ct = self.get_header ("content-type")
		if ct:
			ctl = ct.split (";")
			self.content_type = ctl [0]
			for param in ctl [1:]:
				if param.strip ().startswith ("charset="):
					self.charset = param.split ("=", 1)[-1].strip ().lower ()
					
		self.connection = self.get_header ("connection")				
		try:
			self.body = r.get_content ()
		except:
			handler.request.logger.trace ()
			self.body = b""
			self.code, self.msg = 720, "Response Content Error"
	
	def __len__ (self):
		return len (self.body)
	
	def __str__ (self):
		return self.string ()
			
	def html (self):
		global has_lxml		
		assert has_lxml is True, "missing lxml or html5lib"
		if self.__html: return self.__parser, self.__html		
		self.__parser, self.__html = treebuilder.Parser, treebuilder.html (self.body, self.__baseurl, self.charset)
		return self.__parser, self.__html
	
	def etree (self):
		global has_lxml		
		assert has_lxml is True, "missing lxml or html5lib"		
		if self.__etree: return self.__parser, self.__etree
		self.__parser, self.__etree = treebuilder.Parser, treebuilder.etree (self.body, self.charset)
		return self.__parser, self.__etree
			
	def binary (self):
		return self.body
	
	def string (self):
		return treebuilder.to_str (self.body, self.charset)
		
	def json (self):
		return json.loads (self.text ())
	
	def xmlrpc (self):
		return xmlrpclib.loads (self.text ())	
	
	def to_binary (self, s):
		if type (s) is str:
			return s.encode ("utf8")
		return s	
					
	def save_to (self, path, header = None, footer = None):
		if type (self.body) is None:
			return
			
		if type (self.body) is bytes:
			f = open (path, "wb")
			if header:
				f.write (self.to_binary (header))	
			f.write (self.body)
			if footer:
				f.write (self.to_binary (footer))
			f.close ()
			
		else:						
			raise TypeError ("Content is not bytes")
			
						
class ResponseContainer:
	def __init__ (self, handler, callback):
		self.__rql = handler.request.rql
		self.__asyncon = handler.asyncon
		
		self.uinfo = self.__rql.uinfo
		self.udata = self.__rql.udata
		self.hconf = self.__rql.hconf
		self.request = RCRequest (handler)
		self.response = RCResponse (handler)
		self.logger = handler.request.logger
		self.callback = callback
		
		for header in handler.response.get_header ():
			if header.lower ().startswith ("set-cookie: "):
				localstorage.g.set_cookie_from_string (
					self.uinfo.rfc,
					header [12:]
				)
		
	def set_cookie (self, k, v):
		localstorage.g.set_cookie (self.uinfo.rfc, k, v)
	
	def get_cookie (self, k):	
		localstorage.g.get_cookie (self.uinfo.rfc, k)
	
	def set_item (self, k, v):
		localstorage.g.set_item (self.uinfo.rfc, k, v)
	
	def get_item (self, k):	
		localstorage.g.get_item (self.uinfo.rfc, k)
		
	def stall (self, timeout):
		a, b = math.modf (timeout)
		for i in range (int (b)):
			self.__asyncon.set_event_time ()
			time.sleep (1)
		time.sleep (a)
	
	def resolve (self, url):
		return urljoin (self.uinfo.rfc, url)
	
	def inherit (self, surl):
		return self.__rql.inherit (surl)
		
	def relocate (self, url):
		from skitai import requests
		requests.add (self.__rql.inherit (self.resolve (url), True), self.callback, front = True)
		
	def visit (self, surl, callback = None):
		from skitai import requests
		requests.add (self.inherit (surl), callback and callback or self.callback)
	
	def retry (self):
		from skitai import requests
		self.uinfo.eurl.inc_retrys ()
		requests.add (self.__rql, self.callback, front = True)
	
	
	