from ..http import buffers
import struct

class grpc_buffer (buffers.bytes_buffer):
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
		
