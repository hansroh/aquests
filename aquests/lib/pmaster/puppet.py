from . import killtree
import time
from subprocess import Popen, PIPE
import threading

class Puppet:
	counter = 0
	def __init__ (self, logger = None, communicate = True):
		self.logger = logger
		self.p = None
		self.__lock = threading.Lock ()
		self.__active = False
		self.__last_activated = time.time ()
		self.__communicate = communicate		
		self.counter += 1
		self.__thread = None
		
	def __str__ (self):	
		return 'Puppet #%d' % self.counter
		
	def set_active (self, flag):
		with self.__lock:
			self.__active = flag
			if flag == False:
				self.p = None
		
	def is_active (self):
		with self.__lock:
			r = self.__active		
		return r
	
	def join (self):
		self.__thread.join ()
				
	def start (self, command):
		self.set_active (True)
		self.__thread = threading.Thread (target = self.threaded_run, args = (command,))
		self.__thread.start ()
		
	def threaded_run (self, command):
		try:
			self.create_process (command)
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
			self.log ("terminated with -1", "error")
				
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
			self.log ("-- terminated with %s" % exitcode, "info")		
		
		self.set_active (False)
		
	def is_timeout (self, timeout):
		return time.time () - self.__last_activated > timeout
	
	def set_last_activate (self):
		self.__last_activated = time.time ()
	
	def remove_date (self, line):	
		if line[0].isdigit ():
			# auqests.lib.logger classes
			line = line [20:].strip ()
		elif line [0] == "\x1b":
			line = line [29:].strip ()
		return line
				
	def log (self, line, type = ""):
		if self.logger:
			line = self.remove_date (line)
			if type:
				line = "[{}] {}".format (type, line)				
			self.logger (line, "")
		self.set_last_activate ()
	
	def read_stdout (self):
		for line in iter (self.p.stdout.readline, ''):
			self.log (line)
		
	def create_process (self, cmd):				
		self.log ("-- start process: %s" % " ".join (cmd), "info")
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
		
		self.read_stdout ()
		self.p.stdout.close ()
		e = self.p.stderr.read ()
		if e: self.log (e)		
		self.p.stderr.close ()
	