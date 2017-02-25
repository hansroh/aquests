import re
from . import http_date
from ...lib import compressors
import time
import json
import struct
from ..grpc import discover
from ..grpc.buffers import grpc_buffer
from . import buffers, treebuilder
from . import localstorage as ls

try:
	from cStringIO import StringIO as BytesIO
except ImportError:
	from io import BytesIO

class HTTPRepsonseError (Exception): 
	pass

RESPONSE = re.compile ('HTTP/([0-9.]+) ([0-9]{3})\s?(.*)')
def crack_response (data):
	global RESPONSE
	[ version, code, msg ] = RESPONSE.findall(data)[0]
	return version, int(code), msg


class Response:
	SIZE_LIMIT = 2**19
	
	def __init__ (self, request, header):	
		self.request = request
		if header [:2] == "\r\n":
			header = header [2:]
		header = header.split ("\r\n")	
		self.response = header [0]
		self.header = header [1:]
		self._header_cache = {}
		self.version, self.code, self.msg = crack_response (self.response)
		self.size = 0
		self.got_all_data = False
		self.max_age = 0
		self.decompressor = None
		self.is_xmlrpc_return = False
		self.__headerdict = None
		self.__encoding = None
		self.__data_cache = None
		self.save_cookies ()
	
	def __repr__ (self):
		return "<Response [%d]>" % self.status_code
		
	def set_max_age (self):
		self.max_age = 0
		if self.code != 200:
			return
		
		expires = self.get_header ("expires")		
		if expires:
			try:
				val = http_date.parse_http_date (expires)
			except:
				val = 0
	
			if val:
				max_age = val - time.time ()
				if max_age > 0:
					self.max_age = int (max_age)
					return
	
		cache_control = self.get_header ("cache-control")
		if not cache_control:
			return
			
		for each in cache_control.split (","):			
			try: 
				k, v = each.split("=")					
				if k.strip () == "max-age":
					max_age  = int (v)
					if max_age > 0:
						self.max_age = max_age
						break
			except ValueError: 
				continue
		
		if self.max_age > 0:
			age = self.get_header ("age")
			if age:
				try: age = int (age)	
				except: pass	
				else:
					self.max_age -= age
				
	def done (self):
		# it must be called finally
		self.got_all_data = True
		if self.decompressor:
			try:
				data = self.decompressor.flush ()
			except:					
				pass
			else:
				self.p.feed (data)			
			self.decompressor = None
	
	def init_buffer (self):
		self.set_max_age ()
		ct = self.get_header ("content-type", "")
		if ct.startswith ('application/grpc'):
			self.p, self.u = buffers.getfakeparser (grpc_buffer, cache = self.max_age)
		elif ct == 'text/xml' and self.request.xmlrpc_serialized ():
			self.p = self.u = buffers.cachable_xmlrpc_buffer (self.max_age)
			self.is_xmlrpc_return = True
		else:			
			self.p, self.u = buffers.getfakeparser (buffers.bytes_buffer, cache = self.max_age)
					
		if self.get_header ("Content-Encoding") == "gzip":			
			self.decompressor = compressors.GZipDecompressor ()
			
	def collect_incoming_data (self, data):		
		if self.size == 0:
			self.init_buffer ()		
		self.size += len (data)
		
		if self.decompressor:
			data = self.decompressor.decompress (data)
		
		if self.max_age and self.size > self.SIZE_LIMIT:
			self.max_age = 0
			self.u.no_cache ()
		
		if data:
			# sometimes decompressor return "",
			# null byte is signal of producer's ending, so ignore.
			self.p.feed (data)
	
	def get_header_with_attr (self, header, default = None):
		d = {}
		v = self.get_header (header)
		if v is None:
			return default, d
			
		v2 = v.split (";")
		for each in v2:
			if not each: continue
			each = each.strip ()
			print (each)
			try:
				a, b = each.split ("=", 1)
			except ValueError:
				a, b = each, None				
			d [a.lower ()] = b
		return v2 [0], d
				
	def get_header (self, header = None, default = None):
		if header is None:
			return self.header
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
	
	def set_cookie (self, key, val, domain = None, path = "/"):
		if ls.g:
			ls.g.set_cookie (self.url, key, val, domain, path)
		else:
			raise SystemError ("Cookie Storage Not Initiated")
	
	def get_cookie (self, key):
		if ls.g:
			ls.g.get_cookie (self.url, key)
		else:
			raise SystemError ("Cookie Storage Not Initiated")
		
	def json (self):
		return json.loads (self.raw.read ())
	
	def raise_for_status (self):
		if self.status_code >= 300:
			raise HTTPRepsonseError ("%d %s" % (self.status_code, self.reason))
	reraise = raise_for_status
	
	def get_error_as_string (self):
		if self.status_code >= 300:
			return "<HTTPRepsonseError> %d %s" % (self.status_code, self.reason)		
		return ""	
			
	def save_cookies (self):
		if not ls.g: 
			return
		for line in self.header:
			if line [:12].lower() == 'set-cookie: ':
				ls.g.set_cookie_from_string (self.url, line [12:])
	
	def __nonzero__ (self):
		return self.status_code < 300 and self.data and True or False
	
	@property
	def meta (self):
		return self.request.meta
			
	@property
	def cookies (self):
		if ls.g:
			return ls.g.get_cookie_as_dict (self.url)
		raise SystemError ("Cookie Storage Not Initiated")
	
	@property
	def history (self):		
		return self.request.get_history ()
		
	@property
	def url (self):		
		return self.request.uri
	
	@property
	def method (self):
		return self.request.method
			
	@property
	def status_code (self):		
		return self.code
	
	@property
	def reason (self):
		return self.msg
		
	@property
	def encoding (self):
		if self.__encoding:
			return self.__encoding
		val, attr = self.get_header_with_attr ('content-type')
		self.__encoding = attr.get ('charset')
		return self.__encoding
		
	@property
	def headers (self):
		if self.__headerdict:
			return self.__headerdict
		headerdict = {}
		for line in self.header:
			k, v = line.split (": ", 1)
			if k in headerdict:
				try: headerdict [k].append (v)
				except AttributeError:
					headerdict [k] = [headerdict [k], v]
			else:		
				headerdict [k] = v
		self.__headerdict = headerdict	
		return headerdict		
	
	@property
	def raw (self):
		return self.u.raw ()
	
	@property
	def content (self):
		try:
			return self.raw.read ()
		except AttributeError:
			return b''	
	
	@property
	def binary (self):
		return self.content
		
	@property
	def text (self):
		return treebuilder.to_str (self.content, self.encoding)		
	
	@encoding.setter
	def encoding (self, value):
		self.__encoding = value
	
	@property
	def dom (self):
		if treebuilder.HAS_SKILLSET:
			return treebuilder.html (self.raw, self.request.uri, self.encoding)
			
	@property
	def data (self):
		if self.__data_cache:
			return self.__data_cache
			
		if self.code >= 700:
			return None
		
		if self.size == 0:
			return b""
				
		self.p.close ()
		result = self.u.close ()
		ct = self.get_header ("content-type")
		
		if self.is_xmlrpc_return:
			if len (result) == 1:
				result = result [0]
			return result
			
		elif ct.startswith ("application/json"):
			return json.loads (result)
			
		elif ct.startswith ('application/grpc'):			
			msgs = []
			for msg in result:
				descriptor, isstream = discover.find_output (self.request.path [1:])					
				f = descriptor ()
				f.ParseFromString (msg)
				msgs.append (f)
								
			if not isstream:
				return msgs [0]
			return msgs	
		
		self.__data_cache = result	
		return result
	

class FailedResponse (Response):
	def __init__ (self, errcode, msg, request = None):
		self.version, self.code, self.msg, self.header = "1.0", errcode, msg, []
		self.request = request
		self.buffer = None
		self.got_all_data = True
		self.max_age = 0
	
	@property
	def data (self):
		return None
	
	@property
	def content (self):
		return None
			
	def collect_incoming_data (self, data):
		raise IOError("This Is Failed Response")
	
	def more (self):
		return b""
	
	def done (self):
		pass

