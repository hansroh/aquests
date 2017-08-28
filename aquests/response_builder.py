from .lib.attrdict import AttrDict

class HTTPResponse:	
	def __init__ (self, handler):
		self.handler = handler
		self.response = handler.response
		self.request = self.response.request
	
	def __del__ (self):
		self.response.request = None
		self.request = None		
		self.handler.response = None
		self.response = None
		self.handler = None
			
	def __getattr__ (self, name):
		return getattr (self.response, name)
