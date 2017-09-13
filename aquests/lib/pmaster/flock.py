import os, sys
from . import pidfile

# FILE LOCK
class Lock:
	def __init__ (self, home):
		self.home = home
		self.pidlock = None
		self.create_directory ()
	
	def create_directory (self):
		pidfile.mkdir (self.home)
	
	def get_pidlock (self):
		if self.pidlock is None:
			self.pidlock = pidfile.PidFile (self.home)
		return self.pidlock
		
	def lock (self, name, msg = "do not delete"):	
		f = open (os.path.join (self.home, "lock." + name), "w")
		f.write ("%s\n" % msg)
		os.fsync (f.fileno ())
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
	
	
	