import struct
try:
	from cStringIO import StringIO as BytesIO
except ImportError:
	from io import BytesIO
try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
try:
	import jsonrpclib
	from jsonrpclib.jsonrpc import  JSONTarget, JSONParser 
except ImportError:
	pass		
		
class FakeParser(object):
	def __init__(self, target):
		self.target = target

	def feed(self, data):
		self.target.feed(data)

	def close(self):
		pass


class cachable_xmlrpc_buffer:
	def __init__ (self, cache = 0):
		self.parser, self.buf = xmlrpclib.getparser()
		self.fp = BytesIO ()
		self.cache = cache
		self.cdata = None
	
	def __del__ (self):
		self.fp.close ()
		
	def feed (self, data):
		self.fp.write (data)
		self.parser.feed (data)
				
	def close (self):
		if self.cdata:
			return self.cdata
		res = self.buf.close ()
		if self.cache:
			self.cdata = res		
		return res
	
	def raw (self):
		self.fp.seek (0)
		return self.fp
		
	def no_cache (self):
		self.cache = 0
		self.cdata = None
		

class cachable_jsonrpc_buffer (cachable_xmlrpc_buffer):
	def __init__ (self, cache = 0):
		target = JSONTarget()
		self.parser, self.buf = JSONParser(target), target
		self.fp = BytesIO ()
		self.cache = cache
		self.cdata = None
	

class list_buffer:
	def __init__(self, cache = 0):
		self.cache = cache
		self.data = []
		self.cdata = b''
		self.fp = None
	
	def __del__ (self):
		if self.fp:
			self.fp.close ()
			self.fp = None
			
	def __len__ (self):
		return len (self.data)
		
	def feed(self, data):
		if self.cache:
			self.cdata += data
		self.data.append (data)
	
	def raw (self):
		if self.cdata:
			self.fp = BytesIO (self.cdata)			
		else:
			self.fp = BytesIO (b"".join (self.data))
		self.fp.seek (0)
		return self.fp
		
	def read (self):	
		# consume data, used by proxy response
		data = b''.join(self.data)
		self.data = []
		return data
		
	def build_data (self):
		if self.cdata:
			return self.cdata
		return b''.join(self.data)
	
	def close (self):
		if self.cdata:
			return self.cdata
		return self.build_data ()		
	
	def no_cache (self):
		self.cache = 0
		self.cdata = b''


class bytes_buffer:
	def __init__(self, cache = 0):
		self.cache = cache
		self.fp = BytesIO ()
		self.current_buffer_size = 0
		self.cdata = None
	
	def __del__ (self):
		self.fp.close ()		
			
	def __len__ (self):
		return self.current_buffer_size
	
	def raw (self):
		self.fp.seek (0)
		return self.fp
				
	def feed (self, data):
		self.current_buffer_size += len (data)
		self.fp.write (data)
			
	def build_data (self):
		return self.fp.getvalue ()
	
	def close (self):
		if self.cdata:
			return self.cdata
		res = self.build_data ()
		if self.cache:
			self.cdata = res		
		return res
	
	def no_cache (self):
		self.cache = 0
		self.cdata = []
		
def getfakeparser (target_class, cache = False):
	target = target_class (cache)
	return FakeParser (target), target

