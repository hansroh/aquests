import threading
from collections import deque

class await_fifo:
	# On http2, it is impossible to bind channel.ready function, 
	# Because http2 channels handle multiple responses concurrently
	# Practically USE http2_producer_fifo
	
	def __init__ (self):
		self.l = deque ()
		self.has_None = False
	
	def working (self):
		return (self.has_None or self.l) and 1 or 0
	
	def __len__ (self):
		for i in range (len (self.l)):
			if not hasattr (self.l [0], 'ready'):
				return len (self.l)				
			elif self.l [0].ready ():
				return len (self.l)
			else:	
				self.l.append (self.l.popleft ())
		
		if self.has_None and not self.l:
			# for return None
			self.l.append (None)
			self.has_None = False
			return 1
			
		return 0
			
	def __getitem__(self, index):
		return self.l [index]
				
	def __setitem__(self, index, item):
		self.l [index] = item
		
	def __delitem__ (self, index):
		del self.l [index]
	
	def append (self, item):
		self.insert (-1, item)
	
	def appendleft (self, item):
		self.insert (0, item)
	
	def insert_into (self, lst, index, item):		
		if index == 0:
			lst.appendleft (item)
		else:
			lst.append (item)	
		
	def insert (self, index, item):
		if item is None:
			self.has_None = True
			return			
		if self.has_None and index != 0:
			return # deny adding
		if index == 0:
			if type (item) is bytes:
				return self.l.appendleft (item)
			elif hasattr (item, "ready") and not item.ready:
				return self.l.append (item)
		self.insert_into (self.l, index, item)
		
	def clear (self):
		self.l.clear ()
		self.has_None = False
	
	
class await_ts_fifo (await_fifo):
	def __init__ (self):
		await_fifo.__init__ (self)
		self._lock = threading.Lock ()
	
	def working (self):
		with self._lock:
			return await_fifo.working (self)
		
	def __len__ (self):
		with self._lock:
			return await_fifo.__len__ (self)
			
	def __getitem__(self, index):
		with self._lock:
			return await_fifo.__getitem__ (self, index)
		
	def __setitem__(self, index, item):
		with self._lock:
			await_fifo.__setitem__ (self, index, item)
		
	def __delitem__ (self, index):
		with self._lock:
			await_fifo.__delitem__ (self, index)
	
	def clear (self):
		with self._lock:
			await_fifo.clear (self)
			
	def insert (self, index, item):
		with self._lock:
			await_fifo.insert (self, index, item)