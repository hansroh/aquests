from aquests.lib.attrdict import AttrDict

class HTTPResponse:
	def __init__ (self, handler):
		self.response = handler.response
		self.request = self.response.request
		
	def __getattr__ (self, name):
		return getattr (self.response, name)
