import asyncore 
import re 
import time 
import sys 
import threading 	

DEBUG = False

class OperationalError (Exception):
	pass
	
class DBConnect:
	zombie_timeout = 120
	keep_alive = 120
	
	def __init__ (self, address, params = None, lock = None, logger = None):
		self.address = address
		self.params = params		
		self.dbname, self.user, self.password = "", "", ""
		
		if self.params:
			self.dbname, auth = self.params
			if auth:			
				if type (auth) is not tuple:
					self.user = auth
				else:
					try: self.user, self.password = auth
					except ValueError: self.username = auth
						
		self.lock = lock
		self.logger = logger
		
		self.request_count = 0
		self.execute_count = 0
		
		self._cv = threading.Condition ()
		
		# need if there's not any request yet
		self.active = 0
		self.retried = 0
		self.request = None
		self.has_result = False
		self.__history = []
		self.__no_more_request = False
		
		self.set_event_time ()
	
	def duplicate (self):
		new_asyncon = self.__class__ (self.address, self.params, self.lock, self.logger)
		new_asyncon.keep_alive = self.keep_alive
		return new_asyncon
		
	def get_proto (self):
		# call by culster_manager
		return None
	
	def handle_abort (self):		
		# call by dist_call
		self.close ()
		
	def close (self, deactive = 1):
		self.request = None
		addr = type (self.address) is tuple and ("%s:%d" % self.address) or str (self.address)
		self.logger ("[info] .....dbo %s has been closed" % addr)	
		if deactive:
			self.set_active (False)
					
	def get_history (self):
		return self.__history
		
	def clean_shutdown_control (self, phase, time_in_this_phase):
		self.__no_more_request = True
		if self.isactive ():
			return 1
		else:
			self.handle_close ()
			self.__no_more_request = False
			return 0
	
	def empty_cursor (self):
		if self.has_result:
			self.fetchall ()			
	
	def maintern (self, object_timeout):
		# query done but not used
		if self.has_result and self.isactive () and time.time () - self.event_time > self.zombie_timeout:			
			self.empty_cursor ()
			self.set_active (False)
			
		if time.time () - self.event_time > object_timeout:
			if not self.isactive ():
				self.disconnect ()
				return True # deletable
		return False	
	
	def reconnect (self):
		self.disconnect ()
		self.connect ()
	
	def disconnect (self):
		# keep request, just close temporary
		request = self.request
		self.close (deactive = 0)
		self.request = request
	
	def close_case (self):
		raise NotImplementedError
			
	def set_active (self, flag, nolock = False):
		if not flag: 
			self.set_timeout (self.keep_alive)
			self.retried = 0
			
		if flag:
			flag = time.time ()
		else:
			flag = 0
			
		if nolock or self.lock is None:
			self.active = flag
			return
		
		self.lock.acquire ()
		self.active = flag
		self.request_count += 1		
		self.lock.release ()
	
	def get_active (self, nolock = False):
		if nolock or self.lock is None:
			return self.active			
		self.lock.acquire ()	
		active = self.active
		self.lock.release ()	
		return active
	
	def isactive (self):	
		return self.get_active () > 0
		
	def isconnected (self):	
		# self.connected should be defined at __init__ or asyncore
		return self.connected
		
	def get_request_count (self):	
		return self.request_count
	
	def get_execute_count (self):	
		return self.execute_count
	
	def connect (self, force = 0):
		raise NotImplementedError("must be implemented in subclass")
	
	def set_timeout (self, timeout):
		self.zombie_timeout = timeout

	def handle_timeout (self):
		self.handle_close (OperationalError, "Operation Timeout")
	
	def handle_error (self):
		dummy, exception_class, exception_str, tbinfo = asyncore.compact_traceback()
		self.has_result = False
		self.logger.trace ()
		self.handle_close (exception_class, exception_str)
	
	def handle_close (self, expt = None, msg = ""):
		if not expt and not self.retried:			
			self.disconnect ()
			self.retried = 1
			self.execute (self.request)			
			return
			
		self.exception_class, self.exception_str = expt, msg		
		self.close_case_with_end_tran ()
		self.close ()
	
	def set_event_time (self):
		self.event_time = time.time ()			
	
	def log_history (self, msg):	
		self.__history.append ("BEGIN TRAN: %s" % sql)
	
	def close_case_with_end_tran (self):
		self.end_tran ()
		self.close_case ()
		
	#-----------------------------------------------------
	# DB methods
	#-----------------------------------------------------
	def fetchall (self):		
		raise NotImplementedError
	
	def end_tran (self):
		raise NotImplementedError
						
	def begin_tran (self, request):
		if self.__no_more_request:			
			try: 
				raise OperationalError ("Entered Shutdown Process")
			except: 
				self.handle_error ()
				return
		
		self.request = request	
		self.__history = []
		self.has_result = False
		self.exception_str = ""
		self.exception_class = None		
		self.execute_count += 1
		self.set_event_time ()		
		
	def execute (self, request):		
		self.begin_tran (request)		
		raise NotImplementedError("must be implemented in subclass")


class AsynDBConnect (DBConnect):
	def is_channel_in_map (self, map = None):
		if map is None:
			map = self._map
		return self._fileno in map
	
	def maintern (self, object_timeout):
		# when in map, mainteren by lifetime with zombie_timeout
		if self.is_channel_in_map ():
			return False
		return DBConnect.maintern (self, object_timeout)
		
	def del_channel (self, map=None):
		# do not remove self._fileno
		fd = self._fileno
		if map is None:
			map = self._map
		if fd in map:
			del map[fd]
	
	