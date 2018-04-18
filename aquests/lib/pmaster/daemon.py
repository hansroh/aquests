import os
import sys
import time
import signal
import getopt
from . import killtree, processutil
from .. import pathtool

class Daemonizer:
	def __init__(self, chdir="/", procname = None, umask=0o22, lockpath = None):
		self.chdir = chdir
		self.procname = procname
		self.umask = umask
		self.lockpath = lockpath or chdir
		self.pidfile = os.path.join (self.lockpath, '.pid')
	
	def runAsDaemon(self):
		if status (self.lockpath, self.procname):
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

def status (lockpath, procname = None):
	pidfile =  os.path.join (lockpath, '.pid')
	if not os.path.isfile (pidfile):		
		return 0
	with open (pidfile) as f:
		pid = int (f.read ())
	return processutil.is_running (pid, procname) and pid or 0

def kill (lockpath, procname = None, include_children = True, signaling = True):
	import psutil
	
	for i in range (2):
		pid = status (lockpath, procname)		
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
		os.remove (os.path.join (lockpath, ".pid"))
	except FileNotFoundError:	
		pass

def handle_commandline (argopt, working_dir, procname, lockpath = None):
	def _start (working_dir, procname, lockpath):
		if not Daemonizer (working_dir, procname, lockpath = lockpath).runAsDaemon ():
			print ("already running")
			sys.exit ()

	def _stop (lockpath, procname):
		kill (lockpath, procname, True)
	
	def _status (lockpath, procname):
		pid = status (lockpath, procname)
		if pid:
			print ("running [%d]" % pid)
		else:
			print ("stopped")
	
	def _restart (working_dir, procname, lockpath):
		_stop (lockpath, procname)
		time.sleep (2)
		_start (working_dir, procname, lockpath)
	
	pathtool.mkdir (working_dir)
	argdict = []
	arglist = []
	daemonics = []
	
	for k, v in argopt [0]:
		if k == "-d":
			daemonics.append ("start")
		else:
			argdict.append ((k, v))
		
	for arg in argopt [1]:
	 	if arg in ("start", "restart", "stop", "status"):
	 		daemonics.append (arg)
	 	else:
	 		arglist.append (arg)
	 		
	lockpath = lockpath or working_dir		
	if "start" in daemonics: 
		_start (working_dir, procname, lockpath)			
	elif "restart" in daemonics: 
		_restart (working_dir, procname, lockpath)			
	elif "stop" in daemonics:
		_stop (lockpath, procname)
		sys.exit ()			
	elif "status" in daemonics:		
		_status (lockpath, procname)
		sys.exit ()
	
	return (argdict, arglist)

if __name__ == "__main__"	:
	import time
	
	Daemonizer ().runAsDaemon ()	
	f = open ('/home/ubuntu/out', 'w')
	while 1:
		time.sleep (1)
		f.write ('asdkljaldjalkdjalkdsa\n')
		f.flush()
	f.close ()

		
