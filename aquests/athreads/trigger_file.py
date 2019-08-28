import re
from rs4 import asyncore
from . import trigger

class ConnectionError (Exception): pass
class AlreadyClosed (Exception): pass

class trigger_file:
	buffer_size = 4096
	def __init__ (self, channel):
		self.channel = channel
		self.buffer = ''
		
	def write (self, data):
		self.buffer = self.buffer + data
		if len(self.buffer) > self.buffer_size:
			self.flush ()

	def writeline (self, line):
		self.write (line+'\r\n')
		
	def writelines (self, lines):
		self.write (
			string.joinfields (
				lines,
				'\r\n'
				) + '\r\n'
			)

	def softspace (self, *args):
		pass
	
	def flush (self):
		if self.buffer:
			d, self.buffer = self.buffer, ''
			trigger.wakeup (lambda p=self.channel, d=d: p.push (d))
			
	def close (self):
		p, self.channel = self.channel, None
		d, self.buffer = self.buffer, ''
		trigger.wakeup (lambda p=p,d=d: (p.push(d), p.close_when_done()))


class buffered_trigger_file:
	def __init__ (self, channel):
		self.channel = channel
		self.buffer = ''
		
	def write (self, data):
		self.buffer = self.buffer + data		
	
		
HEADER_LINE = re.compile ('([A-Za-z0-9-]+): ([^\r\n]+)')
class header_scanning_file:
	def __init__ (self, request, file):
		self.buffer = ''
		self.request = request
		self.file = file
		self.got_header = 0
		self.bytes=0
		self.closed = 0
		
	def __call__ (self, data):
		self.write (data)
	
	def build_header (self, lines):
		status = '200 OK'
		saw_content_type = 0
		hl = HEADER_LINE
		for line in lines:
			mo = hl.match (line)
			if mo is not None:
				h = mo.group(1).lower()
				if h == 'status':
					status = mo.group(2)
				elif h == 'content-type':
					saw_content_type = 1
		lines.insert (0, 'HTTP/1.0 %s' % status)
		lines.append ('Server: ' + self.request ['Server'])
		lines.append ('Date: ' + self.request ['Date'])
		if not saw_content_type:
			lines.append ('Content-Type: text/html')
		lines.append ('Connection: close')
		return '\r\n'.join(lines)+'\r\n\r\n'
	
	def iswritable (self):
		if self.closed: raise AlreadyClosed
		if self.request.channel is None: raise ConnectionError		
			
	def write (self, data):		
		self.iswritable ()
			
		if self.got_header:			
			self.bytes+=len(data)
			self.file.write (data)
			
		else:			
			self.buffer = self.buffer + data
			lines = self.buffer.split('\n')			
			lines = lines[:-1]
			for i in range(len(lines)):
				li = lines[i]
				if (not li) or (HEADER_LINE.match (li) is None):
					self.got_header = 1
					h = self.build_header (lines[:i])
					self.file.write (h)
					d = '\n'.join (lines[i:])
					self.file.write (d)
					self.bytes+=len(d)
					self.buffer = ''
					break
	
	def writeline (self, data):
		self.iswritable ()
		self.file.writeline (data)
			
	def writelines (self, list):
		self.iswritable ()
		self.file.writelines (list)

	def flush (self):
		self.iswritable ()
		self.file.flush ()

	def close (self):
		self.iswritable ()
		if not self.got_header:
			response = ('<html><h1>Server Error</h1>\r\n'
			'<b>Bad Gateway:</b> No Header from CGI Script\r\n'
			'<pre>Data: %s</pre>'
			'</html>\r\n' % repr (self.buffer))
			
			self.file.write (self.build_header (['Status: 502', 'Content-Type: text/html']))
			self.file.write (response)
		
		self.request.log (self.bytes)
		self.file.close ()
		self.closed = 1
		