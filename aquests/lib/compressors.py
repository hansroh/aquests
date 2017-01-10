import zlib
import gzip
import io
import time
import struct
import sys

PY_MAJOR_VERSION = sys.version_info.major

class DeflateCompressor:
	def __init__ (self, level = 5):
		self.compressor = zlib.compressobj (5, zlib.DEFLATED)
		
	def compress (self, buf):	
		return self.compressor.compress (buf)
	
	def flush (self):
		return self.compressor.flush ()


class DeflateDeompressor:
	def __init__ (self):
		self.decompressor = zlib.decompressobj ()	
		
	def compress (self, buf):	
		d = self.decompressor.decompress (buf)
		if d == b"":
			return self.flush ()
		return d	
	
	def flush (self):
		return self.decompressor.flush ()
		
				
class GZipCompressor:
	#HEADER = b"\037\213\010" + chr (0) + struct.pack ("<L", int (time.time ())) + b"\002\377"
	HEADER = b"\037\213\010" + b'\x00' + struct.pack ("<L", int (time.time ())) + b"\002\377"	
	def __init__ (self, level = 5):
		self.size = 0
		self.crc = zlib.crc32(b"")
		self.compressor = zlib.compressobj (level, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
		self.first_data = True
			
	def compress (self, buf):
		self.size = self.size + len(buf)
		self.crc = zlib.crc32(buf, self.crc)
		d = self.compressor.compress (buf)
		if self.first_data:
			d = self.HEADER + d
			self.first_data = False
		return d
	
	def flush (self):
		d = self.compressor.flush ()
		if PY_MAJOR_VERSION	>= 3:
			return d + struct.pack ("<L", self.crc) + struct.pack ("<L", self.size & 0xFFFFFFFF)
		else:
			return d + struct.pack ("<l", self.crc) + struct.pack ("<L", self.size & 0xFFFFFFFF)	
		

def U32(i):
	if i < 0:
		i += 1 << 32
	return i
    
class GZipDecompressor:	
	def __init__ (self, level = 5):
		self.size = 0
		self.crc = zlib.crc32(b"")
		self.decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
		self.first_data = True
		self.maybe_eof = b""
		self.extra = False
			
	def decompress (self, buf):
		if self.first_data:
			buf = buf [10:]
			self.first_data = False
		elif self.extra:
			if len (buf) == 8:
				return ""
			else:
				self.extra = False
				buf = b"\x03\x00" + buf
		
		if buf == b"\x03\x00":
			# what is it?	
			self.extra = True
				
		if len (buf) > 8:
			self.maybe_eof = buf [-8:]
		else:
			self.maybe_eof += buf
			self.maybe_eof = self.maybe_eof [-8:]
		
		d = self.decompressor.decompress (buf)
		self.size += len (d)
		self.crc = zlib.crc32(d, self.crc)
		if d == b"":			
			return self.decompressor.flush ()
		return d
	
	def flush (self):
		crcs, isizes = self.maybe_eof [:4], self.maybe_eof [4:]
		if PY_MAJOR_VERSION	>= 3:
			crc32 = struct.unpack ("<L", crcs)[0]
		else:
			crc32 = struct.unpack ("<l", crcs)[0]	
		isize = U32 (struct.unpack ("<L", isizes)[0])
		if U32 (crc32) != U32 (self.crc):
			raise IOError("CRC check failed")
		elif isize != (self.size & 0xFFFFFFFF):
			raise IOError("Incorrect length of data produced")
		return b""
			

if __name__ == "__main__":
	import urllib.request, urllib.parse, urllib.error
	f =urllib.request.urlopen ("http://www.gmarket.co.kr/index.asp/")
	d = f.read ()
	
	a = GZipCompressor ()
	x = a.compress (d) + a.flush ()	
	b = GZipDecompressor ()	
	while x:
		k, x = x [:10], x [10:]		
		b.decompress (k)
	print(repr(b.flush ()))
	print(repr(b.flush ()))
	print(repr(b.flush ()))	
	a = zlib.compressobj ()
	x = a.compress (d) + a.flush ()	
	b = zlib.decompressobj ()	
	while x:
		k, x = x [:10], x [10:]				
		b.decompress (k)
	b.decompress ("")	
	b.decompress ("")	
	print(repr(b.flush ()))
	print(repr(b.flush ()))
	print(repr(b.flush ()))
	
