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

	from psycopg2.extensions import POLL_OK, POLL_READ, POLL_WRITE
	_STATE_OK = (POLL_OK, POLL_WRITE, POLL_READ)
	_STATE_RETRY = -1
	_STATE_IGNORE = -2
	REREY_TEST = False	

	class AsynConnect (dbconnect.AsynDBConnect, asyncore.dispatcher):
		def __init__ (self, address, params = None, lock = None, logger = None):
			dbconnect.AsynDBConnect.__init__ (self, address, params, lock, logger)			
			self.cur = None
			self.retries = 0
			asyncore.dispatcher.__init__ (self)

		def retry (self):
			if self.request is None:
				return
			self.retries += 1	
			self.logger ("[warn] closed psycopg2 connection, retrying...")
			self.disconnect ()
			request, self.request = self.request, None
			self.execute (request)
			return _STATE_RETRY

		def check_state (self, state):
			if state == _STATE_RETRY:				
				return
			if state not in (_STATE_OK):
				self.logger ("[warn] psycopg2.poll() returned %s" % state)
				self.handle_close ()
			
		def poll (self):
			# 2 cases, if on requesting raise immediatly, else handle silently
			try:
				if REREY_TEST and self.writable () and self.request.retry_count == 0:
					#raise psycopg2.InterfaceError
					self.disconnect ()
				return self.socket.poll ()
			except (psycopg2.OperationalError, psycopg2.InterfaceError):
				if self.request:
					if self.request.retry_count == 0:
						self.request.retry_count += 1
						return self.retry ()
					else:
						raise
				self.logger.trace ()				
			except:
				# else usually timeout	
				if self.request:
					raise
				self.logger.trace ()
			return _STATE_IGNORE
			
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
			self.handle_close (psycopg2.OperationalError ("Socket Panic"))
			
		def handle_connect (self):			
			self.create_cursor ()
			
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
			if state == POLL_OK:
				if not self.cur:
					self.create_cursor ()				
				self.set_event_time ()
				self.cur.execute (self.out_buffer)
				self.out_buffer = ""
			else:				
				self.check_state (state)
				
		#-----------------------------------
		# Overriden
		#-----------------------------------
		def create_cursor (self):
			if self.cur is None:
				try:
					self.cur = self.socket.cursor ()						
				except:
					self.handle_error ()

		def close_cursor (self):
			if self.cur:
				try:
					self.cur.close ()							
				except:
					self.logger.trace ()
				self.cur = None	

		def close_case (self):
			if self.request:
				description, data = self.cur and self.cur.description or None, None
				if description:
					try:
						data = self.fetchall ()
					except:
						self.logger.trace ()
						self.expt = asyncore.compact_traceback () [2]						
						data = None
				self.request.handle_result (description or None, self.expt, data)					
				self.request = None				
			self.close_cursor ()
			self.set_active (False)
		
		def fetchall (self):
			data = self.cur.fetchall ()				
			self.result = False
			return data

		def close (self, deactive = 1):					
			self.close_cursor ()
			asyncore.dispatcher.close (self)			
			dbconnect.AsynDBConnect.close (self, deactive)			
			
		def connect (self, force = 0):
			host, port = self.address		
			sock = psycopg2.connect (
				dbname = self.dbname,
				user = self.user,
				password = self.password,
				host = host,
				port = port,
				async_ = 1
			)			
			self.set_socket (sock)			
		
		def end_tran (self):			
			pass
		
		def _compile (self, request):
			sql = request.params [0]
			if isinstance (sql, (list, tuple)):
				sql = ";\n".join (map (str, sql)) + ";"
			try:
				sql = sql.strip ()
			except AttributeError:				
				raise dbconnect.SQLError ("Invalid SQL")
			if not sql:
				raise dbconnect.SQLError ("Empty SQL")
			return sql
		
		def execute (self, request):		
			dbconnect.DBConnect.begin_tran (self, request)
			self.out_buffer = self._compile (request)
			if not self.connected and not self.connecting:				
				self.connect ()
			else:
				state = self.poll ()
				if state != POLL_OK:
					self.reconnect ()
				else:
					self.create_cursor ()				
