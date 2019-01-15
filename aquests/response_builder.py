from rs4.attrdict import AttrDict

class HTTPResponse:	
	def __init__ (self, response):
		self.response = response
		self.request = response.request
	
	def __del__ (self):
		self.response.request = None
		self.request = None		
		self.response = None		
			
	def __getattr__ (self, name):
		return getattr (self.response, name)
