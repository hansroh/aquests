import os, sys
from . import pathtool

def isCurrentProcess (pid, cmd = None):
	if cmd is None:
		cmd = sys.argv [0]
		
	if os.name == "nt":
		import win32process, win32api, win32con, pywintypes
		HAS_WMI = True
		try: import wmi	
		except ImportError: HAS_WMI = False
		
		if pid not in win32process.EnumProcesses ():
			return False
	
		if HAS_WMI:
			cl = [p.CommandLine for p in wmi.WMI ().Win32_Process () if p.ProcessID == pid]
			if cl and cl [0].find (cmd) != -1:
				return True
			return False
												
		else:	
			try:
				handle = win32api.OpenProcess (win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, 0, int (pid))
				exefilename = win32process.GetModuleFileNameEx (handle, 0)
				win32process.GetStartupInfo()
				if exefilename.find ("python.exe") != -1:
					return True
			except pywintypes.error: 
				# Windows service, Access is denied
				return False

	else:
		proc = "/proc/%s/cmdline" % pid
		if not os.path.isfile (proc):
			return False
		
		with open (proc) as f:
			exefilename = f.read ()		
		if exefilename.find (cmd) != -1:
			return True
		
	return False
	
	
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
	
	
	