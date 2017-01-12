class Queue:
	def __init__ (self):
		self.q = []
		self.__req_id = 0
	
	@property
	def req_id (self):
		return self.__req_id
		
	def add (self, req):
		self.q.append (req)
		self.__req_id += 1
		
	def get (self):
		try:
			return self.q.pop (0)
		except IndexError:
			return None
			