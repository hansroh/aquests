import struct
try:
	from cStringIO import StringIO as BytesIO
except ImportError:
	from io import BytesIO
try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
	
		
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
		
	
class list_buffer:
	def __init__(self, cache = 0):
		self.cache = cache
		self.raw = []
		self.cdata = None
	
	def __len__ (self):
		return len (self.data)
		
	def feed(self, data):
		self.raw.append(data)
	
	def raw (self):
		f = BytesIO (b"".join (self.raw))
		f.seek (0)
		return f
		
	def read (self):	
		# consume data, used by proxy response
		data = self.build_data ()
		self.raw = []
		return data
		
	def build_data (self):
		return b''.join(self.raw)
	
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


class bytes_buffer:
	def __init__(self, cache = 0):
		self.cache = cache
		self.fp = BytesIO ()
		self.current_buffer_size = 0
		self.cdata = None		
	
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


class grpc_buffer (bytes_buffer):
	def build_data (self):
		msgs = []
		fp = self.fp
		fp.seek (0)
		
		byte = fp.read (1)
		while byte:
			iscompressed = struct.unpack ("<B", byte) [0]
			length = struct.unpack ("<i", fp.read (4)) [0]
			msg = fp.read (length)
			msgs.append (msg)
			byte = fp.read (1)
		return tuple (msgs)
	
	def close (self):
		if self.cdata:
			return self.cdata
		res = self.build_data ()
		if self.cache:
			self.cdata = res
		return res
		
def getfakeparser (target_class, cache = False):
	target = target_class (cache)
	return FakeParser (target), target

