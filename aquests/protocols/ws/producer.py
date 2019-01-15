from collections import Iterable
from ..grpc.producers import grpc_producer
from rs4 import strutil
from . import OPCODE_TEXT, OPCODE_BINARY
import struct
import os

class ws_producer (grpc_producer):
	def __init__ (self, message = None):
		self.closed = False
		if type (message) in (str, bytes, tuple):
			message = iter ([message])
		elif type (message) is list:
			message = iter (message)
		self.message = message
		self.serialized = []
		self.content_length = 0	
		
		self.fin = 1
		self.rsv1 = 0
		self.rsv2 = 0
		self.rsv3 = 0
	
	def serialize (self, msg):
		if type (msg) is tuple:
			opcode, msg = msg
		else:
			if type (msg) is bytes:
				opcode, msg = OPCODE_BINARY, msg
			elif type (msg) is str:
				opcode, msg = OPCODE_TEXT, msg				
			else:
				raise TypeError ("Websocket Messags OP Code Not Specified")		
		if strutil.is_encodable (msg):
			msg = msg.encode ("utf8")
					
		header = b''
		if self.fin > 0x1:
			raise ValueError('FIN bit parameter must be 0 or 1')
			
		if 0x3 <= opcode <= 0x7 or 0xB <= opcode:
			raise ValueError('Opcode cannot be a reserved opcode')
	
		header = struct.pack('!B', ((self.fin << 7)
					 | (self.rsv1 << 6)
					 | (self.rsv2 << 5)
					 | (self.rsv3 << 4)
					 | opcode))
		
		masking_key = os.urandom(4)		
		if masking_key: mask_bit = 1 << 7
		else: mask_bit = 0
	
		length = len (msg)
		if length < 126:
			header += struct.pack('!B', (mask_bit | length))
		elif length < (1 << 16):
			header += struct.pack('!B', (mask_bit | 126)) + struct.pack('!H', length)
		elif length < (1 << 63):
			header += struct.pack('!B', (mask_bit | 127)) + struct.pack('!Q', length)
		else:
			raise AssertionError ("Message too large (%d bytes)" % length)
		
		masking_data = msg
		if not masking_key:
			return bytesarray (header + masking_data)	
		masking_key = bytearray (masking_key)
		masking_data = bytearray (masking_data)
		
		s = bytearray (header) + masking_key + bytearray ([masking_data[i] ^ masking_key [i%4] for i in range (len (masking_data))])
		self.serialized.append (s)
		self.content_length += len (s)
		return s
