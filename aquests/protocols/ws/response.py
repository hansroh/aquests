from aquests.protocols.http import response

class Response (response.Response):
	def __init__ (self, request, code, msg, opcode, data = None):
		self.request = request
		self.code = code
		self.msg = msg
		self.__data = data
		self.version = "1.1"
		self.opcode = opcode
	
	@property
	def data (self):
		return self.__data
	
	@property
	def headers (self):
		return {}
		
	def done (self):
		pass
	