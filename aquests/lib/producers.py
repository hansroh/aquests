# -*- Mode: Python; tab-width: 4 -*-

RCS_ID = '$Id: producers.py,v 1.10 1999/02/01 03:08:46 rushing Exp $'

import string
import time
import io
import gzip
from . import compressors, strutil
import mimetypes
import os
from collections import Iterable

"""
A collection of producers.
Each producer implements a particular feature:  They can be combined
in various ways to get interesting and useful behaviors.

For example, you can feed dynamically-produced output into the compressing
producer, then wrap this with the 'chunked' transfer-encoding producer.
"""

class simple_producer:
	"producer for a string"
	def __init__ (self, data, buffer_size = 4096):
		self.data = data
		self.buffer_size = buffer_size

	def more (self):
		if len (self.data) > self.buffer_size:
			result = self.data[:self.buffer_size]
			self.data = self.data[self.buffer_size:]
			return result
		else:
			result = self.data
			self.data = b''
			return result

class list_producer (simple_producer):
	def __init__ (self, data):
		self.data = data
		
	def more (self):
		if not self.data:
			return b''			
		data = self.data.pop (0)
		if strutil.is_encodable (data):
			return data.encode ("utf8")
		return data

class iter_producer (list_producer):
	def more (self):
		try:
			data = next (self.data)
			if strutil.is_encodable (data):
				return data.encode ("utf8")
			return data
		except StopIteration:		
			return b""

class closing_stream_producer (simple_producer):
	def __init__ (self, data, buffer_size = 4096):
		if not hasattr (data, "read"):
			raise AttributeError ("stream object should have `read()` returns bytes object and optional 'close()'")			
		simple_producer.__init__ (self, data, buffer_size)
		self.closed = False
			
	def more (self):
		if self.closed: 
			return b""
		data = self.data.read (self.buffer_size)
		if not data:
			self.close ()
		return data
	
	def close (self):
		if self.closed: return			
		try: self.data.close ()
		except AttributeError: pass	
		self.closed = True
	
class scanning_producer:
	"like simple_producer, but more efficient for large strings"
	def __init__ (self, data, buffer_size = 4096):
		self.data = data
		self.buffer_size = buffer_size
		self.pos = 0

	def more (self):
		if self.pos < len(self.data):
			lp = self.pos
			rp = min (
				len(self.data),
				self.pos + self.buffer_size
				)
			result = self.data[lp:rp]
			self.pos = self.pos + len(result)
			return result
		else:
			return b''

class lines_producer:
	"producer for a list of lines"

	def __init__ (self, lines):
		self.lines = lines

	def ready (self):
		return len(self.lines)

	def more (self):
		if self.lines:
			chunk = self.lines[:50]
			self.lines = self.lines[50:]
			return b'\r\n'.join (chunk) + b'\r\n'
		else:
			return b''

class buffer_list_producer:
	"producer for a list of buffers"

	# i.e., data == string.join (buffers, '')
	
	def __init__ (self, buffers):
		self.index = 0
		self.buffers = buffers

	def more (self):
		if self.index >= len(self.buffers):
			return b''
		else:
			data = self.buffers[self.index]
			self.index = self.index + 1
			return data

class file_producer:
	"producer wrapper for file[-like] objects"

	# match http_channel's outgoing buffer size
	buffer_size = 4096

	def __init__ (self, file):
		self.done = 0
		self.file = file

	def more (self):
		if self.done:
			return b''
		else:
			data = self.file.read (self.buffer_size)			
			if not data:
				self.file.close()
				del self.file
				self.done = 1
				return b''
			else:
				return data

# A simple output producer.  This one does not [yet] have
# the safety feature builtin to the monitor channel:  runaway
# output will not be caught.

# don't try to print from within any of the methods
# of this object.

class output_producer:
	"Acts like an output file; suitable for capturing sys.stdout"
	def __init__ (self):
		self.data = ''
			
	def write (self, data):
		lines = data.split (b'\n')
		data = b'\r\n'.join (lines)
		self.data = self.data + data
		
	def writeline (self, line):
		self.data = self.data + line + b'\r\n'
		
	def writelines (self, lines):
		self.data = self.data + string.joinfields (
			lines,
			b'\r\n'
			) + b'\r\n'

	def ready (self):
		return (len (self.data) > 0)

	def flush (self):
		pass

	def softspace (self, *args):
		pass

	def more (self):
		if self.data:
			result = self.data[:512]
			self.data = self.data[512:]
			return result
		else:
			return b''
		
class composite_producer:
	"combine a fifo of producers into one"
	def __init__ (self, producers):
		self.producers = producers
		self.bind_ready ()
	
	def bind_ready (self):	
		p = self.producers.first ()
		if hasattr (p, "ready"):
			self.ready = p.ready
			p.ready = None
						
	def more (self):
		while len(self.producers):
			p = self.producers.first()
			d = p.more()			
			if d:
				return d
			else:
				self.producers.pop()
		else:
			return b''

class globbing_producer:
	"""
	'glob' the output from a producer into a particular buffer size.
	helps reduce the number of calls to send().  [this appears to
	gain about 30% performance on requests to a single channel]
	"""

	def __init__ (self, producer, buffer_size = 4096):
		self.producer = producer
		self.buffer = b''
		self.buffer_size = buffer_size
		self.bind_ready ()
	
	def bind_ready (self):	
		if hasattr (self.producer, "ready"):
			self.ready = self.producer.ready
			self.producer.ready = None
		
	def more (self):
		while len(self.buffer) < self.buffer_size:
			data = self.producer.more()
			if data:
				self.buffer = self.buffer + data
			else:
				break
		r = self.buffer
		self.buffer = b''
		return r


class hooked_producer (globbing_producer):
	"""
	A producer that will call <function> when it empties,.
	with an argument of the number of bytes produced.  Useful
	for logging/instrumentation purposes.
	"""

	def __init__ (self, producer, function):
		self.producer = producer
		self.function = function
		self.bytes = 0
		self.bind_ready ()
		
	def more (self):
		if self.producer:
			result = self.producer.more()			
			if not result:				
				self.producer = None				
				self.function (self.bytes)
			else:
				self.bytes = self.bytes + len(result)
			return result
		else:
			return b''

# HTTP 1.1 emphasizes that an advertised Content-Length header MUST be
# correct.  In the face of Strange Files, it is conceivable that
# reading a 'file' may produce an amount of data not matching that
# reported by os.stat() [text/binary mode issues, perhaps the file is
# being appended to, etc..]  This makes the chunked encoding a True
# Blessing, and it really ought to be used even with normal files.
# How beautifully it blends with the concept of the producer.

class chunked_producer (globbing_producer):
	"""A producer that implements the 'chunked' transfer coding for HTTP/1.1.
	Here is a sample usage:
		request['Transfer-Encoding'] = 'chunked'
		request.push (
			producers.chunked_producer (your_producer)
			)
		request.done()
	"""

	def __init__ (self, producer, footers=None):
		self.producer = producer
		self.footers = footers
		self.bind_ready ()
			
	def more (self):
		if self.producer:
			data = self.producer.more()
			if data:
				dlen = '%x' % len (data)
				return dlen.encode ("utf8") + b"\r\n" + data + b'\r\n'
			else:				
				self.producer = None
				if self.footers:
					return b'\r\n'.join (
						[b'0'] + self.footers
					) + b'\r\n\r\n'
				else:
					return b'0\r\n\r\n'
		else:
			return b''

# Unfortunately this isn't very useful right now (Aug 97), because
# apparently the browsers don't do on-the-fly decompression.  Which
# is sad, because this could _really_ speed things up, especially for
# low-bandwidth clients (i.e., most everyone).

try:
	import zlib
except ImportError:
	zlib = None

class compressed_producer (globbing_producer):
	"""
	Compress another producer on-the-fly, using ZLIB
	[Unfortunately, none of the current browsers seem to support this]
	"""

	# Note: It's not very efficient to have the server repeatedly
	# compressing your outgoing files: compress them ahead of time, or
	# use a compress-once-and-store scheme.  However, if you have low
	# bandwidth and low traffic, this may make more sense than
	# maintaining your source files compressed.
	#
	# Can also be used for compressing dynamically-produced output.

	def __init__ (self, producer, level=6):
		self.producer = producer
		self.compressor = zlib.compressobj (level, zlib.DEFLATED)
		self.bind_ready ()
	
	def more (self):
		if self.producer:
			cdata = b''
			# feed until we get some output
			while not cdata:
				data = self.producer.more()
				if not data:
					self.producer = None
					return self.compressor.flush()
				else:
					cdata = self.compressor.compress (data)					
			return cdata
		else:
			return b''


class gzipped_producer (compressed_producer):
	def __init__ (self, producer, level=5):
		self.producer = producer
		self.compressor = compressors.GZipCompressor (level)		
		self.bind_ready ()
			
	
class escaping_producer:

	"A producer that escapes a sequence of characters"
	" Common usage: escaping the CRLF.CRLF sequence in SMTP, NNTP, etc..."

	def __init__ (self, producer, esc_from='\r\n.', esc_to='\r\n..'):
		self.producer = producer
		self.esc_from = esc_from
		self.esc_to = esc_to
		self.buffer = b''
		from asynchat import find_prefix_at_end
		self.find_prefix_at_end = find_prefix_at_end		
		self.bind_ready ()
			
	def more (self):
		esc_from = self.esc_from
		esc_to   = self.esc_to

		buffer = self.buffer + self.producer.more()

		if buffer:
			buffer = string.replace (buffer, esc_from, esc_to)
			i = self.find_prefix_at_end (buffer, esc_from)
			if i:
				# we found a prefix
				self.buffer = buffer[-i:]
				return buffer[:-i]
			else:
				# no prefix, return it all
				self.buffer = b''
				return buffer
		else:
			return buffer


class fifo:
	def __init__ (self, list=None):
		if not list:
			self.list = []
		else:
			self.list = list
		
	def __len__ (self):
		return len(self.list)

	def first (self):
		return self.list[0]

	def push_front (self, object):
		self.list.insert (0, object)

	def push (self, data):
		self.list.append (data)

	def pop (self):
		if self.list:
			result = self.list[0]
			del self.list[0]
			return (1, result)
		else:
			return (0, None)
	
	def clear (self):
		self.list = []
			