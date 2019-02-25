from ..http import response

class Response (response.Response):
	def __init__ (self, request, code, msg, opcode = None, data = None):
		self.request = request
		self.code = code
		self.msg = msg
		self.__data = []
		if opcode:
			self.__data.append ((opcode, data))		
		self.version = "1.1"		
		
	def add_message (self, opcode, data = None):
		self.__data.append ((opcode, data))
		
	@property
	def content (self):
		if not self.__data:
			return None
		return self.__data [0]
		
	@property
	def data (self):
		if not self.__data:
			return None
		return self.content [0][1]
	
	@property
	def opcode (self):
		if not self.__data:
			return None
		return self.content [0][0]
	
	@property
	def headers (self):
		return {}
		
	def done (self):
		pass
	