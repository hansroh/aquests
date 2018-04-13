import mimetypes
import os

"""-----------------------------286502649418924
Content-Disposition: form-data; name="submit-hidden"

Genious
-----------------------------286502649418924
Content-Disposition: form-data; name="submit-name"

Hans Roh
-----------------------------286502649418924
Content-Disposition: form-data; name="file1"; filename="House.2x01.acceptance.DVDRip-iMa.smi"
Content-Type: application/smil

asdadasda
-----------------------------286502649418924
Content-Disposition: form-data; name="file2"; filename=""
Content-Type: application/octet-stream


-----------------------------286502649418924--"""


class multipart_producer:
	buffer_size = 4096
	
	def __init__ (self, data, boundary):
		# self.data = {"name": "Hans Roh", "file1": <open (path, "rb")>}
		self.data = data
		self.closed = False
		self.serialized = []
		self.dlist = []
		self.boundary = boundary		
		self.current_file = None
		self.content_length = self.calculate_size ()
		#self.bytes_out = 0
		
	def calculate_size (self):
		size = (len (self.boundary.encode ("utf8")) + 4) * (len (self.data) + 1) # --boundary + (\r\n or last --)
		for name, value in list(self.data.items ()):
			size += (41 + len (name.encode ("utf8"))) #Content-Disposition: form-data; name=""\r\n
			if type (value) is not type (""):
				fsize = os.path.getsize (value.name)
				size += (fsize + 2) # file size + \r\n
				fn = os.path.split (value.name) [-1]
				size += len (fn.encode ("utf8")) + 13 # ; filename=""\r\n
				mimetype = mimetypes.guess_type (fn) [0]
				if not mimetype:
					mimetype = "application/octet-stream"
				size += (16 + len (mimetype)) # Content-Type: application/octet-stream\r\n				
				self.dlist.append ((1, name, (value.name, fn, mimetype)))
				value.close ()
			
			else:
				size += len (value.encode ("utf8")) + 2 # value + \r\n
				self.dlist.append ((0, name, value))

			size += 2 # header end \r\n	
			
		return size	

	def get_content_length (self):
		return self.content_length
	
	def get_payload (self):
		if not self.serialized:
			raise ValueError ('Expired Multipart Content')
		return b"".join (self.serialized)
	
	def exhausted (self):
		return self.closed
	
	def more (self):
		d = self.__more ()
		if d and self.content_length <= 4096000: # MAX 4M
			self.serialized.append (d)
		return d
			
	def __more (self):
		if not self.dlist: 
			self.closed = True
			return b''
			
		if self.current_file:
			d = self.current_file.read (self.buffer_size)
			if d:
				return d
			else:
				self.current_file.close ()
				self.current_file = None
				self.dlist.pop (0)
				d = "\r\n"
				if not self.dlist:
					d += "--%s--" % self.boundary
				#self.bytes_out += len (d)
				return d.encode ("utf8")
			
		if self.dlist:
			first = self.dlist [0]
			if first [0] == 0: # formvalue
				d = '--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (self.boundary, first [1], first [2])
				self.dlist.pop (0)
				if not self.dlist:
					d += "--%s--" % self.boundary
				#self.bytes_out += len (d)
				return d.encode ("utf8")
			else:
				path, filename, mimetype = first [2]
				self.current_file = open (path, "rb")
				return ('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\nContent-Type: %s\r\n\r\n' % (
					self.boundary, first [1], filename, mimetype
				)).encode ("utf8")
				#self.bytes_out += len (d)
				#return d
		