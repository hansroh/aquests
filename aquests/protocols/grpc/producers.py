from rs4 import compressors
from collections import Iterable
import struct

class grpc_producer:
	def __init__ (self, message = None, use_compress = False):
		self.closed = False		
		self.use_compress = use_compress
		self.compressor = compressors.GZipCompressor ()
		self.message = message
		self.serialized = []
		self.content_length = 0
		
	def get_headers (self):
		headers = []
		if self.use_compress:			
			headers.append (("grpc-encoding", "gzip"))
		return headers	 
		
	def get_size (self):
		return self.content_length or -1
			
	def get_content_length (self):
		if self.closed:
			return self.content_length
		
	def send (self, msg):
		self.message.send (msg)
		
	def serialize (self, msg):
		compressed = 0
		serialized = msg.SerializeToString ()
		if self.use_compress and len (serialized) > 2048:
			serialized = self.compressor.compress (serialized) + self.compressor.flush ()
			compressed = 1		
		s = struct.pack ("!B", compressed) + struct.pack ("!I", len (serialized)) + serialized
		self.serialized.append (s)
		self.content_length += len (s)		
		return s
	
	def get_payload (self):			
		return b"".join (self.serialized)
		
	def more (self):
		if self.exhausted ():
			return b""
		
		if not isinstance (self.message, Iterable):
			msg = self.serialize (self.message)
			self.close ()
			return msg
		
		try:
			msg = next (self.message)			
			return self.serialize (msg)
		except StopIteration:
			self.close ()
			return b""
	
	def exhausted (self):
		return self.closed and not self.message
			
	def close (self):	
		self.content_length = 0	
		self.closed = True
		self.message = None


