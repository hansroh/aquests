import os
import sys

class Daemon:
	def __init__(self, chdir="/", umask=0o22, pidfile = None ):
		self.chdir = chdir
		self.umask = umask
		self.pidfile = pidfile

	def runAsDaemon(self):
		self.fork_and_die()
		os.setsid()
		self.fork_and_die()
		os.chdir(self.chdir)
		os.umask(self.umask)		
	
	def fork_and_die(self):
		r = os.fork()
		if r == -1:
			raise OSError("Couldn't fork().")
		elif r > 0:  # I'm the parent
			if self.pidfile: open (self.pidfile, 'w').write (str(r))
			sys.exit(0)
		elif r < 0:
			raise OSError("Something bizarre happened while trying to fork().")
			# now only r = 0 (the child) survives.
		return r
	
