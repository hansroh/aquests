from aquests.lib.attrdict import AttrDict

class HTTPResponse:
	def __init__ (self, handler):
		self.response = handler.response
		self.request = self.response.request
		self.meta = self.request.meta
		# compet with requests
		self.status_code = self.response.code
		self.status_msg = self.response.msg		
		
	def __getattr__ (self, name):
		return getattr (self.response, name)
