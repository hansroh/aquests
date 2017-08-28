import collections

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
		
# memory leaking?
class NocaseDict(dict):
	def __setitem__(self, key, value):
		key = CaseInsensitiveKey(key)
		super(NocaseDict, self).__setitem__(key, value)
	
	def __getitem__(self, key):
		key = CaseInsensitiveKey(key)
		return super(NocaseDict, self).__getitem__(key)


class CaseInsensitiveDict(collections.MutableMapping):
	def __init__(self, data=None, **kwargs):
		self._store = collections.OrderedDict()
		if data is None:
			data = {}
		self.update(data, **kwargs)

	def __setitem__(self, key, value):
		# Use the lowercased key for lookups, but store the actual
		# key alongside the value.
		self._store[key.lower()] = (key, value)

	def __getitem__(self, key):
		return self._store[key.lower()][1]

	def __delitem__(self, key):
		del self._store[key.lower()]

	def __iter__(self):
		return (casedkey for casedkey, mappedvalue in self._store.values())

	def __len__(self):
		return len(self._store)

	def lower_items(self):
		"""Like iteritems(), but with all lowercase keys."""
		return (
			(lowerkey, keyval[1])
			for (lowerkey, keyval)
			in self._store.items()
		)

	def __eq__(self, other):
		if isinstance(other, collections.Mapping):
			other = CaseInsensitiveDict(other)
		else:
			return NotImplemented
		# Compare insensitively
		return dict(self.lower_items()) == dict(other.lower_items())

	# Copy is required
	def copy(self):
		return CaseInsensitiveDict(self._store.values())

	def __repr__(self):
		return str(dict(self.items()))
				

if __name__ == "__main__":
	a = AttrDict ()
	a ["a-s"] = 1
	print (a.a_s)
	a.x = 4
	print (a['x'])
	
	b = NocaseDict ()
	b ['Content-Length'] = 100
	print (b ['content-length'])