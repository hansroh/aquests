from aquests.protocols.http import response

class Response (response.Response):
	def __init__ (self, request, code, msg, opcode, data = None):
		self.request = request
		self.code = code
		self.msg = msg
		self.data = data
		self.version = "1.1"
		self.header = ["OPCODE: %s" % opcode]
	
	def get_content (self):
		return self.data
	
	def done (self):
		pass
	