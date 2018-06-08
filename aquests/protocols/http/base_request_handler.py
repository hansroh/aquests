
class RequestHandler:
	def __init__ (self, logger):
		self.logger = logger
		
	def log (self, message, type = "info"):
		self.logger.log ("%s - %s" % (self.request.uri, message), type)

	def log_info (self, message, type='info'):
		self.log (message, type)

	def trace (self):
		self.logger.trace (self.request.uri)
	
	def working (self):
		return False
		
