import sys, os
from . import pathtool
import importlib
import importlib.machinery

try: _reloader = importlib.reload
except AttributeError: _reloader = reload

def importer (directory, libpath, module = None):
	fn = not libpath.endswith (".py") and libpath + ".py" or libpath
	modpath = os.path.join (directory, fn)
	hname = fn.split (".")[0]
	p = directory.replace ("\\", "/")
	if p.find (":") !=- 1:
		p = "/" + p.replace (":", "")
	while 1:
		if hname in sys.modules:				
			p, l = os.path.split (p)
			if not l:
				raise SystemError ('module %s already imported, use reload')
			hname = l + "." + hname
		else:
			break
	
	loader = importlib.machinery.SourceFileLoader(hname, modpath)
	mod = loader.load_module ()
	
	return mod, mod.__file__
	
def reimporter (module, directory, libpath):
	try: 
		del sys.modules [module.__name__]
	except KeyError:
		pass	
	return importer (directory, libpath)
	

#----------------------------------------------
# will be deprecated
#----------------------------------------------
	
def importer_old (directory, libpath):	
	sys.path.insert(0, directory)	
	__import__ (libpath, globals ())
	libpath, abspath = pathtool.modpath (libpath)
	module = sys.modules [libpath]	
	if abspath [-4:] in (".pyc", ".pyo"):
		abspath = abspath [:-1]		
	sys.path.pop (0)		
	return module, abspath

def reloader (module):
	directory = os.path.split (module.__file__) [0]
	sys.path.insert(0, directory)
	_reloader (module)
	sys.path.pop (0)		
