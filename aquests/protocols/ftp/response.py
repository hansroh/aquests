import mimetypes
from ..client.http import response

class Unacceptable (Exception): pass
class FilenameError (Exception): pass

FailedResponse = response.FailedResponse
	
class Response (response.Response):
	fs = None
	accept = "*/*"
	
	def __init__ (self, request):
		self.request = request
		self.sock = None
		self.ustruct = self.request.ustruct
		self.storage = self.request.storage
		self.logger = self.request.logger
		
		self.buffer = None
		self.textbuffer = ""
		self.filename = None
		self.closed = 0
		self.compressed = False
		self.fake_http_response ()
		self.open ()
	
	def fake_http_response (self):
		self.version, self.code, self.msg = "1.1", 200, "OK"
		self.head = {"content-type": self.detect_content_type ()}
		
	def detect_content_type (self):
		fn = self.ustruct.uinfo.script.split ("/") [-1].split (".")
		if len (fn) == 1:
			return "text/plain"
		ext = fn [-1]	
		maybe_type, maybe_some = mimetypes.guess_type ("." + ext)
		if not maybe_type:
			return "text/plain"
		return maybe_type

