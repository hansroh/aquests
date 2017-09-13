import os, sys
from .processutil import is_running

# FILE LOCK

def mkdir (tdir, mod = -1):
	while tdir:
		if tdir [-1] in ("\\/"):
			tdir = tdir [:-1]
		else:
			break	

	if os.path.isdir (tdir): return	
	chain = [tdir]	
	while 1:
		tdir, last = os.path.split (tdir)		
		if not last: 
			break
		if tdir:
			chain.insert (0, tdir)
	
	for dir in chain [1:]:
		try: 
			os.mkdir (dir)
			if os.name == "posix" and mod != -1:
				os.chmod (dir, mod)				
		except OSError as why:
			if why.errno in (17, 183): continue
			else: raise


class PidFile:
	def __init__ (self, path):
		self.path = path
	
	def make (self):
		if self.isalive ():
			raise AssertionError("process is runnig. terminated.")
					
		pathtool.mkdir (self.path)
		pidfile = os.path.join (self.path, "pid")			
		f = open (pidfile, "w")
		f.write ("%s" % os.getpid ())
		os.fsync (f.fileno ())
		f.close ()
	
	def remove (self):		
		pidfile = os.path.join (self.path, "pid")
		if os.path.isfile (pidfile):
			os.remove (pidfile)
		
	def getpid (self, match = None):
		pidfile = os.path.join (self.path, "pid")
		if os.path.isfile (pidfile):
			f = open (pidfile)
			pid = f.read ()
			f.close ()
			pid = int (pid)
			if is_running (pid, match):
				return pid
		return None
			
	def isalive (self):
		return self.getpid () is not None and True or False
				