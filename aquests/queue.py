class Queue:
	def __init__ (self):
		self.q = []
	
	def add (self, req):
		self.q.append (req)
		
	def get (self):
		try:
			return self.q.pop (0)
		except IndexError:
			return None
			