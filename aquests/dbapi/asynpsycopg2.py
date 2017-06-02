#-------------------------------------------------------
# Asyn PostgresSQL Dispatcher
# Hans Roh (hansroh@gmail.com)
# 2015.6.9
#-------------------------------------------------------
		
DEBUG = False

try:
	import psycopg2
	
except ImportError:	
	class AsynConnect:
		def __init__ (self, address, params = None, lock = None, logger = None):
			logger ("[warn] cannot import psycopg2")
			raise ImportError ("cannot import psycopg2")

else:	
	import asyncore
	from . import dbconnect

	from psycopg2.extensions import POLL_OK, POLL_WRITE, POLL_READ
	_STATE_OK = (POLL_OK, POLL_WRITE, POLL_READ)
		
	class AsynConnect (dbconnect.AsynDBConnect, asyncore.dispatcher):
		def __init__ (self, address, params = None, lock = None, logger = None):
			dbconnect.AsynDBConnect.__init__ (self, address, params, lock, logger)			
			self.conn = None
			self.cur = None			
			asyncore.dispatcher.__init__ (self)
			
		def check_state (self, state):
			if state not in (_STATE_OK):				
				self.logger ("[warn] psycopg2.poll() returned %s" % state)
				self.handle_close ()
		
		def poll (self):
			try:
				return self.socket.poll ()
			except psycopg2.OperationalError:
				pass
			except:				
				self.logger.trace ()
			return -1
			
		def writable (self):			
			return self.out_buffer or not self.connected
			
		def readable (self):
			return self.connected and not self.out_buffer
		
		def add_channel (self, map = None):
			return asyncore.dispatcher.add_channel (self, map)
				
		def del_channel (self, map=None):
			fd = self._fileno
			if map is None:
				map = self._map
			if fd in map:
				del map[fd]
		
		def handle_expt_event (self):
			self.handle_expt ()
			
		def handle_connect_event (self):
			state = self.poll ()			
			if state == POLL_OK:	
				self.handle_connect ()
				self.connected = True
				self.connecting = False		
			else:				
				self.check_state (state)
		
		def handle_write_event (self):		
			if not self.connected:
				self.handle_connect_event ()
			else:	
				self.handle_write ()
		
		def handle_expt (self):
			self.handle_close (psycopg2.OperationalError, "socket panic")
			
		def handle_connect (self):
			self.del_channel ()
			self.conn = self.socket
			self.cur = self.conn.cursor()		
			self.set_socket (self.cur.connection)			
					
		def handle_read (self):
			state = self.poll ()
			if self.cur and state == POLL_OK:
				self.set_event_time ()
				self.has_result = True
				self.close_case_with_end_tran ()
			else:
				self.check_state (state)
				
		def handle_write (self):
			state = self.poll ()
			if self.cur and state == POLL_OK:
				self.set_event_time ()				
				self.cur.execute (self.out_buffer)
				self.out_buffer = ""
			else:				
				self.check_state (state)
				
		#-----------------------------------
		# Overriden
		#-----------------------------------
		def close_case (self):			
			if self.request:
				if self.has_result and self.cur.description:					
					self.request.handle_result (self.cur.description, self.exception_class, self.exception_str, self.fetchall ())					
				else:
					self.request.handle_result (None, self.exception_class, self.exception_str, None)
					self.has_result = False
				self.request = None
			self.set_active (False)
			
		def empty_cursor (self):
			if self.has_result:
				try:
					self.fetchall ()
				except psycopg2.ProgrammingError:
					pass				
		
		def fetchall (self):
			result = self.cur.fetchall ()
			self.has_result = False
			return result
							
		def close (self, deactive = 1):
			if self.cur:
				try:
					self.cur.close ()
				except psycopg2.ProgrammingError:
					pass						
				self.cur = None
			if self.conn:	
				self.conn.close ()
				self.conn = None	
				
			dbconnect.AsynDBConnect.close (self, deactive)
			asyncore.dispatcher.close (self)
			
		def connect (self, force = 0):
			host, port = self.address		
			sock = psycopg2.connect (
				dbname = self.dbname,
				user = self.user,
				password = self.password,
				host = host,
				port = port,
				async = 1
			)
			self.set_socket (sock)
		
		def end_tran (self):
			self.del_channel ()

		def begin_tran (self, request):
			dbconnect.AsynDBConnect.begin_tran (self, request)
			self.out_buffer = request.params [0]
								
		def execute (self, request):			
			self.begin_tran (request)			
			if not self.connected:
				self.connect ()				
			else:
				state = self.poll ()
				if state != POLL_OK:
					self.reconnect ()
				else:
					self.add_channel ()
