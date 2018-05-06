import sys

PY_MAJOR_VERSION = sys.version_info [0]

if PY_MAJOR_VERSION >= 3:
	def makes (arg, encoding = None):
		argtype = type (arg)
		if argtype is str:
			return arg.strip ()
		if argtype is bytes and encoding:
			return arg.decode (encoding)
		if arg is None: 
			return ""		
		if argtype is int:
			return str (arg)
			
		raise TypeError ("Must be String, Int, None or Bytes with encoding")	
				
else:		
	def makes (arg, encoding = "utf8"):
		argtype = type (arg)
		if argtype is unicode:
			return arg.encode ("utf8").strip ()
		if argtype is str:
			if encoding in (None, "utf8"):
				return arg.strip ()
			return arg.decode (encoding).encode ("utf8")
		if arg is None:
			return ""
		if argtype is int:
			return str (arg)		
			
		raise TypeError ("Must be Unicode, Int, None or String with encoding")	
		
