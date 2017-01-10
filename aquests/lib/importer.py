import sys, os
from aquests.lib import pathtool
import importlib

try: _reloader = importlib.reload
except AttributeError: _reloader = reload
	
def importer (directory, libpath):
	sys.path.insert(0, directory)	
	__import__ (libpath, globals ())
	libpath, abspath = pathtool.modpath (libpath)
	module = sys.modules [libpath]	
	if abspath [-4:] in (".pyc", ".pyo"):
		abspath = abspath [:-1]		
	sys.path.pop (0)		
	return module, abspath

def reimporter (module):
	directory, libpath = os.path.split (module.__file__)[0], module.__name__
	del sys.modules [module.__name__]
	importer (directory, libpath)
	
def reloader (module):
	directory = os.path.split (module.__file__) [0]
	sys.path.insert(0, directory)
	_reloader (module)
	sys.path.pop (0)		
	
	
