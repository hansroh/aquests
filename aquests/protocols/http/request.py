import aquests
try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
try:
	import jsonrpclib
except ImportError:
	pass	
	
import struct
import base64
import json
try: 
	from urllib.parse import urlparse, quote, urljoin
except ImportError:
	from urllib import quote
	from urlparse import urlparse, urljoin
from rs4 import strutil, attrdict, compressors
from .producer import multipart_producer

class HistoricalResponse:
	def __init__ (self, response):
		self.status_code = response.status_code
		self.reason = response.reason
		self.url = response.url
		self.headers = response.headers
		self.content = response.content
	
	def __repr__ (self):
		return "<Response [%d]>" % self.status_code

	
class XMLRPCRequest:	
	user_agent = "Mozilla/5.0 (compatible; Aquests/%s.%s)" % aquests.version_info [:2]
	initial_http_version = "1.1"
	allow_redirects = True
	
	reauth_count = 0
	retry_count = 0
				
	def __init__ (self, uri, method, params = (), headers = None, auth = None, logger = None, meta = {}, http_version = None):
		# mount point generalizing, otherwise some servers reponse 301
		self.uri = uri
		self.method = method
		self.params = params		
		self.auth = (auth and type (auth) is not tuple and tuple (auth.split (":", 1)) or auth)
		self.logger = logger
		self.meta = meta
		self.http_version = http_version
		self.content_length = 0
		self.address, self.path = self.split (uri)		
		self._history = []
		self.__xmlrpc_serialized = False
		
		self.fit_headers (headers)
		self.payload = self.serialize ()
	
	def fit_headers (self, headers):
		if isinstance (headers, attrdict.CaseInsensitiveDict):
			self.headers = headers
			self.remove_header ("content-length", "connection")
			if not self.headers.get ("accept"):
				self.headers ["Accept"] = "*/*"
		else:	
			self.headers = attrdict.CaseInsensitiveDict ()			
			self.headers ["Accept-Encoding"] = "gzip"
			if headers:			
				for k, v in type (headers) is dict and headers.items () or headers:
					n = k.lower ()
					if n in ("content-length", "connection"):
						# reanalyze
						continue					
					self.headers [k] = v
					
	def add_history (self, response):
		self._history.append (HistoricalResponse (response))
	
	def get_history (self):	
		return self._history
	
	def _relocate (self, response, newloc):
		if len (self._history) > 5:
			raise RuntimeError ("Maximum Redirects Reached")
						
		if response.status_code in (301, 302):
			if self.get_method () in ("POST", "PUT"):			
				self.payload = b""
				self.set_content_length (0)
				self.remove_header ('content-type')
				self.remove_header ('content-length')
				self.remove_header ('transfer-encoding')
				self.remove_header ('content-encoding')
			self.method = "GET"
		
		if not newloc:
			newloc = response.get_header ('location')
		self.uri = urljoin (self.uri, newloc)
		self.address, self.path = self.split (self.uri)
		self.add_history (response)		
			
	def relocate (self, response, newloc = None):
		if response.status_code in (301, 302):
			raise TypeError ("XMLRPC Cannot Be Moved")
		return self._relocate (response, newloc)
		
	def set_content_length (self, length):
		self.content_length = length
	
	def get_content_length (self):
		return self.content_length
				
	def build_header (self):
		if self.get_header ("host") is None:
			address = self.get_address ()
			if address [1] in (80, 443):			
				self.headers ["Host"] = "%s" % address [0]
			else:
				self.headers ["Host"] = "%s:%d" % address
		
		if self.get_header ("user-agent") is None:
			self.headers ["User-Agent"] = self.user_agent
		
	def get_cache_key (self):
		if len (self.payload) > 4096:
			return None
		return "%s:%s%s/%s?%s" % (
			self.address [0], self.address [1],
			self.path, self.method, self.payload
		)
		
	def xmlrpc_serialized (self):
		return self.__xmlrpc_serialized
		
	def set_address (self, address):
		self.address = address
		
	def get_address (self):
		return self.address
		
	def get_method (self):
		return "POST"
		
	def split (self, uri):
		if uri.find ("://") == -1:
			return None, uri
			
		scheme, address, script, params, qs, fragment = urlparse (uri)
		if not script: script = "/"
		path = script
		if params: path += ";" + params
		if qs: path += "?" + qs
		
		try: 
			host, port = address.split (":", 1)
			port = int (port)
		except ValueError:
			host = address
			if scheme in ("http", "ws"):
				port = 80
			else:
				port = 443	
		
		return (host, port), path
		
	def serialize (self):
		self.__xmlrpc_serialized = True		
		if self.uri [-1] != "/":
			self.uri += "/"
			self.path += "/"
		data = xmlrpclib.dumps (self.params, self.method, allow_none = 1).encode ("utf8")
		self.headers ["Content-Type"] = "text/xml; charset=utf-8"
		cl = len (data)
		self.headers ["Content-Length"] = cl
		self.set_content_length (cl)
		return data
	
	def compress (self, data):
		if len (data) <= 2048:
			return data
		f = compressors.GZipCompressor ()
		data = f.compress (data) + f.flush ()
		self.headers ["Content-Encoding"] = "gzip"		
		return data
		
	def get_auth (self):
		return self.auth
		
	def get_payload (self):
		# check if producer payload
		try:
			self.payload.closed
		except AttributeError:
			return self.payload
		
		# if producer closed, use cached payload
		if self.payload.closed:
			return self.payload.get_payload ()
		else:
			return self.payload
			
	get_data = get_payload	
	
	def remove_header (self, *keys):
		for key in keys:
			try:
				del self.headers [key]
			except KeyError:
				pass			
		
	def get_header (self, k, with_key = False):
		if with_key:
			return k, self.headers.get (k)
		return self.headers.get (k)
		
	def get_headers (self):
		self.build_header ()
		return list (self.headers.items ())


class JSONRPCRequest (XMLRPCRequest):
	def serialize (self):
		if self.uri [-1] != "/":
			self.uri += "/"
			self.path += "/"
		data = jsonrpclib.dumps (self.params, self.method).encode ("utf8")
		self.headers ["Content-Type"] = "application/json-rpc; charset=utf-8"
		cl = len (data)
		self.headers ["Content-Length"] = cl
		self.set_content_length (cl)
		return data
		
		
class HTTPRequest (XMLRPCRequest):		
	def relocate (self, response, newloc = None):
		return self._relocate (response, newloc)
		
	def get_method (self):
		return self.method.upper ()
	
	def get_cache_key (self):
		if len (self.payload) > 4096:
			return None			
		return "%s:%s/%s?%s" % (
			self.address [0], self.address [1], self.path, self.payload
		)
	
	def to_bytes (self, data, set_content_length = True):
		if type (self.params) is str:			
			data = self.params.encode ("utf8")			
			
		if set_content_length:
			# when only bytes type, in case proxy_request this value will be just bool type
			try:
				cl = len (data)				
			except TypeError:
				pass
			else:
				self.headers ["Content-Length"] = cl
				self.set_content_length (cl)	
				
		return data
	
	def urlencode (self, to_bytes = True):
		fm = []
		for k, v in list(self.params.items ()):			
			fm.append ("%s=%s" % (quote (k), quote (str (v))))				
		if to_bytes:	
			return "&".join (fm).encode ("utf8")
		return "&".join (fm)
	
	def nvpencode (self):
		fm = []
		for k, v in list(self.params.items ()):
			v = str (v).encode ("utf8")
			fm.append (k.encode ("utf8") + b"[" + str (len (v)).encode ("utf8") + b"]=" + v)
		return b"&".join (fm)
									
	def serialize (self):
		if not self.params:
			if self.get_method () in ("POST", "PUT", "PATCH"):
				self.headers ["Content-Length"] = 0
			return b""
		
		# formdata type can be string, dict, boolean
		if self.get_method () in ("GET", "DELETE"):
			if type (self.params) is dict:
				params = self.urlencode (to_bytes = False)
			else:
				params = self.params
			self.uri += "?" + params
			self.path += "?" + params
			self.params = None
			return b""
		
		data = self.params
		header_name, content_type = self.get_header ("content-type", True)
		
		if not content_type:
			content_type = "application/x-www-form-urlencoded"
						
		if type (self.params) is dict:			
			if content_type.startswith ("application/json"):
				data = json.dumps (self.params).encode ("utf8")				
				content_type = "application/json; charset=utf-8"
			elif content_type.startswith ("application/x-www-form-urlencoded"):
				data = self.urlencode ()				
				content_type = "application/x-www-form-urlencoded; charset=utf-8"
			elif content_type.startswith ("text/namevalue"):
				data = self.nvpencode ()				
				content_type = "text/namevalue; charset=utf-8"
		self.headers ["Content-Type"] = content_type		
		return self.to_bytes (data)
		
		
class HTTPMultipartRequest (HTTPRequest):
	boundary = "-------------------aquests--a1a80da4-ca3d-11e6-b245-001b216d6e71"
		
	def __init__ (self, uri, method, params = {}, headers = None, auth = None, logger = None, meta = {}, http_version = "1.1"):
		HTTPRequest.__init__ (self, uri, method, params, headers, auth, logger, meta, http_version)
		if type (self.params) is bytes:
			self.find_boundary ()
	
	def relocate (self, response):
		XMLRPCRequest.relocate (self, response)
		
	def get_cache_key (self):
		return None
		
	def get_method (self):
		return "POST"
			
	def find_boundary (self):
		s = self.params.find (b"\r\n")
		if s == -1:
			raise ValueError("Boundary Not Found")
		b = self.params [:s]			
		if b [:2] != b"--":
			raise ValueError("invalid multipart/form-data")
		self.boundary = b [2:s]
			
	def serialize (self):
		self.headers ["Content-Type"] = "multipart/form-data; boundary=" + self.boundary
		if type (self.params) is dict:
			p = multipart_producer (self.params, self.boundary)
			cl = p.get_content_length ()
			self.headers ["Content-Length"] = cl
			self.set_content_length (cl)
			return p
		return self.to_bytes (self.params)		
	
