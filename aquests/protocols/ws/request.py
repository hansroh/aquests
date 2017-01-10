from aquests.protocols.http import request
from aquests.lib import strutil
import struct
import os

class Request (request.HTTPRequest):
	def __init__ (self, uri, message, headers = None, encoding = None, auth = None, logger = None, meta = {}):
		if uri.startswith ("ws://"):
			uri = "http://" + uri [5:]
		elif uri.startswith ("wss://"):
			uri = "https://" + uri [6:]
		request.HTTPRequest.__init__ (self, uri, "get", {}, headers, None, auth, logger, meta)		
		self.message = message		
		if not self.message:
			self.message = b""			
		elif strutil.is_encodable (self.message):
			self.message = self.message.encode ("utf8")
			
		if self.encoding is None:
			self.opcode = 1 # OP_TEXT
		else:
			self.opcode = self.encoding
		
		self.payload_length = 0		
		self.fin = 1
		self.rsv1 = 0
		self.rsv2 = 0
		self.rsv3 = 0
		
	def get_cache_key (self):
		return None		
			
	def get_message (self):	
		header = b''
		if self.fin > 0x1:
			raise ValueError('FIN bit parameter must be 0 or 1')
			
		if 0x3 <= self.opcode <= 0x7 or 0xB <= self.opcode:
			raise ValueError('Opcode cannot be a reserved opcode')
	
		header = struct.pack('!B', ((self.fin << 7)
					 | (self.rsv1 << 6)
					 | (self.rsv2 << 5)
					 | (self.rsv3 << 4)
					 | self.opcode))
		
		masking_key = os.urandom(4)		
		if masking_key: mask_bit = 1 << 7
		else: mask_bit = 0
	
		length = len (self.message)
		if length < 126:
			header += struct.pack('!B', (mask_bit | length))
		elif length < (1 << 16):
			header += struct.pack('!B', (mask_bit | 126)) + struct.pack('!H', length)
		elif length < (1 << 63):
			header += struct.pack('!B', (mask_bit | 127)) + struct.pack('!Q', length)
		else:
			raise AssertionError ("Message too large (%d bytes)" % length)
		
		masking_data = self.message
		if not masking_key:
			return bytesarray (header + masking_data)	
		masking_key = bytearray (masking_key)
		masking_data = bytearray (masking_data)
		return bytearray (header) + masking_key + bytearray ([masking_data[i] ^ masking_key [i%4] for i in range (len (masking_data))])
