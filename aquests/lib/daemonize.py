import os
import sys

class Daemonizer:
	def __init__(self, chdir="/", umask=0o22):
		self.chdir = chdir
		self.umask = umask
		self.pidfile = os.path.join (chdir, '.pid')
		
	def runAsDaemon(self):
		self.fork_and_die()
		self.dettach_env ()		
		self.fork_and_die()	
		
		sys.stdout.flush()
		sys.stderr.flush()
		self.attach_stream('stdin', 'r')
		self.attach_stream('stdout', 'a+')
		self.attach_stream('stderr', 'a+')
		
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

if __name__ == "__main__"	:
	import time
	
	Daemonizer ().runAsDaemon ()	
	f = open ('/home/ubuntu/out', 'w')
	while 1:
		time.sleep (1)
		f.write ('asdkljaldjalkdjalkdsa\n')
		f.flush()
	f.close ()

		
