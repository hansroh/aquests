from . import killtree
import time
from subprocess import Popen, PIPE
import threading

class Process:
	def __init__ (self, logger = None):
		self.logger = logger
		self.p = None
		self.__lock = threading.Lock ()
		self.__active = False
		self.__last_activated = time.time ()
		
	def set_active (self, flag):
		self.__lock.acquire ()
		self.__active = flag
		if flag == False:
			self.p = None
		self.__lock.release ()
	
	def is_active (self):
		self.__lock.acquire ()
		r = self.__active
		self.__lock.release ()
		return r
			
	def start (self):
		self.set_active (True)
		threading.Thread (target = self.threaded_run).start ()
		
	def threaded_run (self):
		try:
			self.create_process ()
		finally:
			self.wait ()

	def kill (self):
		if not (self.is_active and self.p):
			self.set_active (False)
			return
		killtree.kill (self.p.pid)
		
	def wait (self):
		if self.p:
			while 1:
				if self.p.poll () is not None:
					break
				time.sleep (1)
			self.log ("[info] -- terminated with %s" % self.p.poll ())
		else:
			self.log ("[error] -- terminated with -1")
		self.set_active (False)
		self.p = None
	
	def is_timeout (self, timeout):
		return time.time () - self.__last_activated > timeout
	
	def set_last_activate (self):
		self.__last_activated = time.time ()
			
	def log (self, line):
		self.logger (line, "")
		self.set_last_activate ()
			
	def create_process (self):		
		cmd = self.shell_command ()
		self.log ("[info] -- start process: %s" % " ".join (cmd))
		s_time = time.time ()
		self.__lock.acquire ()
		try:
			self.p = Popen (
				cmd,
		    universal_newlines=True,
		    stdout=PIPE, stderr=PIPE,
		    shell = False
			)
		finally:
			self.__lock.release ()
		
		for line in iter (self.p.stdout.readline, ''):
			self.log (line [20:].strip ())

		self.p.stdout.close ()			
		e = self.p.stderr.read ()
		if e: self.log (e)		
		self.p.stderr.close ()
	
	def shell_command (self):
		raise NotImplementedError ('should return command like [sys.executable, "script.py", "-tw%s" % phase]')
		
		