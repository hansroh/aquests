from aquests.lib import compressors
from collections import Iterable
import struct

class grpc_producer:
	def __init__ (self, msg = None):
		self.closed = False
		self.compressor = compressors.GZipCompressor ()
		self.message = msg

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
		self.closed = True
		self.message = None


