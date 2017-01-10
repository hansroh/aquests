import sys

PY3 = sys.version_info[0] >= 3
if PY3:
	string_types = str,
	integer_types = int,
	text_type = str
	xrange = range
	
	def reraise(tp, value, tb=None):
		if value.__traceback__ is not tb:
			raise value.with_traceback(tb)
		raise value
      
else:
	import __builtin__
	string_types = __builtin__.basestring,
	text_type = __builtin__.unicode
	integer_types = (int, __builtin__.long)
	xrange = __builtin__.xrange
	
	from py2utils import reraise
	
		
