from aquests.lib import compressors
from collections import Iterable
import struct

class grpc_producer:
	def __init__ (self, msg = None):
		self.closed = False
		self.compressor = compressors.GZipCompressor ()
		self.message = msg
		self.serialized = b""
		self.content_length = 0
		
	def content_length (self):
		if self.content_length:
			return self.content_length
		
		content_length = 0	
		while 1:
			d = self.more ()
			if not d:
				break
			self.serialized += d
			content_length += len (d)
		self.content_length = 0
		
	def send (self, msg):
		self.message.send (msg)
		
	def serialize (self, msg):
		serialized = msg.SerializeToString ()
		compressed = 0
		if len (serialized) > 2048:
			serialized = self.compressor.compress (serialized) + self.compressor.flush ()
			compressed = 1						
		return struct.pack ("!B", compressed) + struct.pack ("!I", len (serialized)) + serialized
				
	def more (self):	
		if self.content_length:
			self.close ()
			return self.serialized
				
		if self.closed and not self.message:
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
		
	def close (self):	
		self.content_length = 0	
		self.closed = True
		self.message = None


