class _Method:
	def __init__(self, send, name):
		self.__send = send
		self.__name = name
		
	def __getattr__(self, name):
		return _Method(self.__send, "%s.%s" % (self.__name, name))
		
	def __call__(self, *args):
		return self.__send(self.__name, args)


class Proxy:
	def __init__ (self, command, executor, *args, **kargs):
		self.__command = command
		self.__executor = executor
		self.__args = args
		self.__kargs = kargs		
	
	def __getattr__ (self, name):	  
		return _Method(self.__request, name)
	
	def __request (self, method, params):
		self.__executor (self.__command, method, params, *self.__args, **self.__kargs)
		