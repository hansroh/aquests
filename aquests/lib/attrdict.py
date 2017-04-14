
class AttrDict (dict):
	def __init__(self, *args, **kwargs):
		super(AttrDict, self).__init__(*args, **kwargs)
		self.__dict__ = self
	

class CaseInsensitiveKey(object):
	def __init__(self, key):
		self.key = key
		
	def __hash__(self):
		return hash(self.key.lower())
	
	def __eq__(self, other):
		return self.key.lower() == other.key.lower()
	
	def __str__(self):
		return self.key
	
	def __repr__(self):
		return self.key	
	
	def __getattr__ (self, name):
		return getattr (self.key, name)
		

class NocaseDict(dict):
	def __setitem__(self, key, value):
		key = CaseInsensitiveKey(key)
		super(NocaseDict, self).__setitem__(key, value)
	
	def __getitem__(self, key):
		key = CaseInsensitiveKey(key)
		return super(NocaseDict, self).__getitem__(key)
		

if __name__ == "__main__":
	a = AttrDict ()
	a ["a-s"] = 1
	print (a.a_s)
	a.x = 4
	print (a['x'])
	
	b = NocaseDict ()
	b ['Content-Length'] = 100
	print (b ['content-length'])