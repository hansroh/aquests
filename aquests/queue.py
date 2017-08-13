from collections import deque
import random

class Queue:
	def __init__ (self):
		self._init ()
		self._req_id = 0
		self._consumed = 0
	
	def qsize (self):
		return len (self.q)
		
	@property
	def req_id (self):
		req_id = self._req_id
		self._req_id += 1
		return req_id
			
	def add (self, req):		
		self._add (req)		
	
	def first (self, req):	
		self._first (req)		
		
	def get (self):
		try:
			self._consumed += 1
			return self._get ()
		except IndexError:
			return None
	
	def _init (self):
		self.q = deque ()
	
	def _add (self, req):
		self.q.append (req)
	
	def _first (self, req):
		self.q.append (req)
		self.q.rotate (1)
		
	def _get (self):
		return self.q.popleft ()
		

class RandomQueue (Queue):
	def _init (self):
		self.q = []
		
	def _add (self, req):
		lq = len (self.q)
		if lq == 0:
			self.q.append (req)
		else:
			self.q.insert(random.randrange (lq), req)
	
	def _first (self, req):
		self.q.insert (0, req)
		
	def _get (self):		
		return self.q.pop (0)
		
	