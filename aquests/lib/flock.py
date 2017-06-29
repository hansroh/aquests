import os, sys
from . import pathtool, processutil

isCurrentProcess = processutil.is_running	
	
class PidFile:
	def __init__ (self, path):
		self.path = path
	
	def make (self):
		import os, sys		
		if self.isalive ():
			raise AssertionError("process is runnig. terminated.")
					
		pathtool.mkdir (self.path)
		pidfile = os.path.join (self.path, "pid")			
		f = open (pidfile, "w")
		f.write ("%s" % os.getpid ())
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
			if isCurrentProcess (pid, match):
				return pid
		return None
			
	def isalive (self):
		return self.getpid () is not None and True or False
				

class Lock:
	def __init__ (self, home):
		self.home = home
		self.pidlock = None
		self.create_directory ()
	
	def create_directory (self):
		pathtool.mkdir (self.home)
	
	def get_pidlock (self):
		if self.pidlock is None:
			self.pidlock = PidFile (self.home)
		return self.pidlock
		
	def lock (self, name, msg = "do not delete"):
		if not self.islocked (name):
			f = open (os.path.join (self.home, "lock." + name), "w")
			f.write ("%s\n" % msg)
			f.close ()
		return 1

	def unlock (self, name):
		lock = os.path.join (self.home, "lock."  + name)
		if os.path.isfile (lock):
			os.remove (lock)
		return 1

	def unlockall (self):
		for file in os.listdir (self.home):
			s = file.find ("lock.")
			if  s != 0: continue
			os.remove (os.path.join (self.home, file))
		return 1

	def islocked (self, name):	
		try:
			return "lock."  + name in os.listdir (self.home)
		except (IOError, OSError):
			return False
	
	def isplocked (self, name):
		try:
			return [x for x in [lock.find ("lock." + name) for lock in os.listdir (self.home)] if x > -1]
		except (WindowsError, IOError, OSError):
			return False

	def locktime (self, name):
		lock = os.path.join (self.home, "lock."  + name)
		if os.path.isfile (lock):
			k = os.stat (lock)
			return k.st_mtime
		return 0

	def lockread (self, name):
		lock = os.path.join (self.home, "lock."  + name)
		if os.path.isfile (lock):
			f = open (lock)
			data = f.read ()
			f.close ()
			return data.strip ()
		return ""

	def locks (self, flt = ""):
		locks, errmsg = [], ''
		for file in os.listdir (self.home):
			if not file.startswith ("lock.%s" % flt):
				continue
			locks.append ((file [5:], self.locktime (file [5:])))
			if file [5:] == "panic":
				f = open (os.path.join (self.home, file))
				errmsg = f.read ()
				f.close ()
		return locks, errmsg


if __name__ == "__main__":
	f = Lock ("d:/")
	print(f.isplocked ("dup"))
	
	
	