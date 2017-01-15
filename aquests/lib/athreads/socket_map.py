import threading
import asyncore

class thread_safe_socket_map (dict):
	def __init__ (self):
		self.lock = threading.RLock ()
	
	def __setitem__ (self, k, v):	
		with self.lock:
			dict.__setitem__ (self, k, v)		
	
	def __len__ (self):	
		with self.lock:
			v = dict.__len__ (self)		
		return v
	
	def __nonzero__(self):
		with self.lock:
			v = dict.__len__ (self)
		return v
			
	def __getitem__ (self, k):	
		with self.lock:
			v = dict.__getitem__ (self, k)
		return v
		
	def __delitem__ (self, k):
		with self.lock:
			dict.__delitem__ (self, k)	
	
	def has_key (self, k):
		with self.lock:
			v = dict.has_key (self, k)			
		return v
			
	def get (self, k, d = None):
		with self.lock:
			v = dict.get (self, k, d)
		return v
	
	def popitem (self, k):
		with self.lock:
			v = dict.popitem (self, k)
		return v
		
	def items (self):
		with self.lock:
			v = dict.items (self)		
		return v
			
	def keys (self):
		with self.lock:
			v = dict.keys (self)
		return v
	
	def values (self):
		with self.lock:
			v = dict.values (self)		
		return v


if not hasattr (asyncore, "_socket_map"):
	asyncore._socket_map = asyncore.socket_map
	del asyncore.socket_map
	asyncore.socket_map = thread_safe_socket_map ()
