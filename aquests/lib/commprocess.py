from . import killtree
import time
from subprocess import Popen, PIPE
import threading

class Process:
	def __init__ (self, logger = None, communicate = True):
		self.logger = logger
		self.p = None
		self.__lock = threading.Lock ()
		self.__active = False
		self.__last_activated = time.time ()
		self.__communicate = communicate
		self.__command = None
		
	def set_active (self, flag):
		with self.__lock:
			self.__active = flag
			if flag == False:
				self.p = None
		
	def is_active (self):
		with self.__lock:
			r = self.__active		
		return r
			
	def start (self, command = None):
		self.__command = command
		
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
		with self.__lock:
			p = self.p
			
		if not p:
			self.log ("[error] -- terminated with -1")
				
		else:
			while 1:
				try:
					with self.__lock:					
						exitcode = self.p.poll ()
				except AttributeError:	
					exitcode = -1
					break										
				if exitcode is not None:
					break
				time.sleep (1)
			self.log ("[info] -- terminated with %s" % exitcode)		
		
		self.set_active (False)
		
	def is_timeout (self, timeout):
		return time.time () - self.__last_activated > timeout
	
	def set_last_activate (self):
		self.__last_activated = time.time ()
			
	def log (self, line):
		if line[0].isdigit ():
			line = line [20:].strip ()
		if self.logger:
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
		    stdout=self.__communicate and PIPE or None, stderr=self.__communicate and PIPE or None,
		    shell = False
			)
		finally:
			self.__lock.release ()
		
		if not self.__communicate:
			return
			
		for line in iter (self.p.stdout.readline, ''):
			self.log (line)

		self.p.stdout.close ()			
		e = self.p.stderr.read ()
		if e: self.log (e)		
		self.p.stderr.close ()
	
	def shell_command (self):
		if self.__command:
			return self.__command
		raise NotImplementedError ('should return command like [sys.executable, "script.py", "-tw%s" % phase]')
		
		