import os
import sys
import time
import signal
from . import killtree, processutil

class Daemonizer:
	def __init__(self, chdir="/", procname = None, umask=0o22):
		self.chdir = chdir
		self.procname = procname
		self.umask = umask
		self.pidfile = os.path.join (chdir, '.pid')
	
	def runAsDaemon(self):
		if status (self.chdir, self.procname):
			return 0
						
		self.fork_and_die()
		self.dettach_env ()		
		self.fork_and_die()	
		
		sys.stdout.flush()
		sys.stderr.flush()
		self.attach_stream('stdin', 'r')
		self.attach_stream('stdout', 'a+')
		self.attach_stream('stderr', 'a+')
		return 1
		
	def dettach_env (self):
		os.setsid()
		os.umask(self.umask)
		os.chdir(self.chdir)
	
	def attach_stream (self, name, mode, fd = '/dev/null'):
		stream = open(fd, mode)
		os.dup2(stream.fileno(), getattr(sys, name).fileno())
	
	def fork_and_die(self):
		r = os.fork()
		if r == -1:
			raise OSError("Couldn't fork().")
		elif r > 0:  # I'm the parent
			if self.pidfile: 
				open (self.pidfile, 'w').write (str(r))
			sys.exit(0)
		elif r < 0:
			raise OSError("Something bizarre happened while trying to fork().")
			# now only r = 0 (the child) survives.
		return r

def status (chdir, procname = None):
	pidfile =  os.path.join (chdir, '.pid')
	if not os.path.isfile (pidfile):		
		return 0
	with open (pidfile) as f:
		pid = int (f.read ())
	return processutil.is_running (pid, procname) and pid or 0

def kill (chdir, procname = None, include_children = True, signaling = True):
	import psutil
	
	for i in range (2):
		pid = status (chdir, procname)		
		if not pid:	
			break
		
		if signaling:	
			os.kill (pid, signal.SIGTERM)
			time.sleep (2)
			
		if include_children:
			try:
				killtree.kill (pid, True)
			except psutil.NoSuchProcess:
				pass	
		
		while processutil.is_running (pid, procname):
			time.sleep (1)
			
	try:
		os.remove (os.path.join (chdir, ".pid"))
	except FileNotFoundError:	
		pass
		
	
if __name__ == "__main__"	:
	import time
	
	Daemonizer ().runAsDaemon ()	
	f = open ('/home/ubuntu/out', 'w')
	while 1:
		time.sleep (1)
		f.write ('asdkljaldjalkdjalkdsa\n')
		f.flush()
	f.close ()

		
