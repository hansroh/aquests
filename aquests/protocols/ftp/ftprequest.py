from rs4 import asyncore
from ..client.http import httprequest
from ..client.asynlib import asyncon
from . import asyncftp
from . import response

class asyncftp_download (asyncore.dispatcher):
	def __init__ (self, handler, host, port):
		asyncore.dispatcher.__init__ (self)
		self.handler = handler
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.connect((host, port))
	
	def writable (self):
		return 0

	def handle_connect (self):
		pass
	
	def trace (self):
		if self.handler:
			self.handler.trace ()

	def log_info (self, line, level = 'info'):
		self.log (line, level)

	def log (self, line, level = "info"):
		if self.handler:
			self.handler.log (line, level)
		
	def handle_expt (self):
		self.handler.trace ()
		self.handler.handle_complete (asyncon.ASYN_UNKNOWNERROR)
		self.close ()

	def handle_read (self):
		data = self.recv (8192)
		return self.handler.collect_incoming_data (data)

	def handle_close (self):
		self.close ()
		self.handler.handle_complete ()


class FTPRequest (httprequest.HTTPRequest):
	def __init__ (self, request):
		self.request = request
		self.response = None
		self.close_it = True
		self.start_request ()
	
	def create_channel (self):
		self.con = asyncftp.asyncftp (self)
		
	def start_request (self):
		self.create_channel ()
		self.con.connect (self.request.get_connect_address ())
	
	def get_user (self):
		return self.request.ustruct.uinfo.username
	
	def get_password (self):
		return self.request.ustruct.uinfo.password
	
	def get_remote_path (Self):
		return self.request.ustruct.uinfo.script
				
	def handle_establish_connection (self, host, port):
		self.response = response.Response (self.request)		
		asyncftp_download (self, host, port)
	
	def collect_incoming_data (self, data):
		self.response.write (data)
			
	def handle_complete (self, err):
		try:
			if not self.response:
				err = asyncon.ASYN_UNKNOWNERROR
				
			if err:
				if self.response:
					self.response.close ()
					self.response.remove ()
					
				self.response = response.FailedResponse (self.request, err, "Network Error")
		
		except:
			self.response = response.FailedResponse (self.request, asyncon.ASYN_PROGRAMERROR, "Program Error")
			self.trace ()
		
		try:		
			self.response.close ()
		except:
			self.response = response.FailedResponse (self.request, asyncon.ASYN_DECODEINGERROR, "Decoding Error")
			self.trace ()
			
		version, code, msg = self.response.get_response ()
		line = "%d %s %s" % (code, msg, self.response.ustruct.uinfo.rfc)
		if self.response.get_filename ():
			line += " saved file:///%s" % self.response.get_filename ()
		self.log (line, "info")
		
		if code >= 200 and not self.close_it:
			self.response.set_socket ((self.con.socket, self.con.ssl))
		
		self.close ()
		if self.request.callback:
			try:				
				self.request.callback (self.response)	
			except:
				self.trace ()

	