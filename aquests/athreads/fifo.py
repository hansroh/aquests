import threading
from collections import deque

class await_fifo:
	# this class has purpose handling a streaming like response
	# as single response object not as multiple bytes stream
	# it is questionable about efficience 
	# but it makes possible optimization response contents - compressing, http2 framing etc - delivery but just bytes relaying
		
	def __init__ (self):
		self.l = deque ()
		self.has_None = False
	
	def working (self):
		return (self.has_None or self.l) and 1 or 0
	
	def __len__ (self):
		if not self.l:
			if self.has_None:
				# for return None
				self.l.append (None)
				self.has_None = False
				return 1
			return 0
			
		for i in range (len (self.l)):
			try:
				readyfunc = getattr (self.l [0], 'ready')
			except AttributeError:
				return 1				
			if readyfunc ():
				return 1				
			self.l.rotate (-1)
		return 0
			
	def __getitem__(self, index):
		return self.l [index]
				
	def __setitem__(self, index, item):
		self.l [index] = item
		
	def __delitem__ (self, index):
		try:
			del self.l [index]
		except IndexError:			
			pass	
		
	def append (self, item):
		self.insert (-1, item)
	
	def appendleft (self, item):
		self.insert (0, item)
		
	def insert (self, index, item):
		if item is None:
			self.has_None = True
			return
			
		if self.has_None and index != 0:
			return # deny adding
		
		if not self.l:
			return self.l.append (item)
				
		if index == -1:	
			return self.l.append (item)
		
		try:
			readyfunc = getattr (item, 'ready')
		except AttributeError:
			pass
		else:	
			if not readyfunc ():
				return self.l.append (item)
				
		return self.l.appendleft (item)
		
	def clear (self):
		self.l.clear ()
		self.has_None = False
	
	
class await_ts_fifo (await_fifo):
	# HTTP/1.x needn't this class, because one channel handles only one request
	# this will be used for handling multiple requests like HTTP/2
	
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
