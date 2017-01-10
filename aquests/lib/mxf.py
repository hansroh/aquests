import mx.ODBC.Windows as odbc
import asyncore
import sys

class QueryLogger:
	def __init__ (self, logger = None):
		self.logger = logger
	
	def __call__ (self, catch, query):
		self.log (catch, query)
				
	def log (self, catch, query):
		if self.logger:
			self.logger.log ("%s %s" % (catch, query))

class QueryError (Exception): pass		
class DBServerError (Exception): pass
		
class odbcf:
	def __init__ (self, conninfo, logger = None, log_query = 1):	
		self.conninfo = conninfo
		self.logger = logger
		self.log_query = log_query
		self.quqeylogger = QueryLogger (logger)
		self.conn = None
		self.cx = None
		self.connected = 0
	
	def __getattr__ (self, attr):
		if self.cx:
			return getattr (self.cx, attr)
		else:
			raise AttributeError	
	
	def log (self, line):	
		if self.logger:
			self.logger.log (line)
		else:
			print(line)	
	
	def trace (self, name = ""):
		if self.logger:
			self.logger.trace (name)
		else:
			print(asyncore.compact_traceback ())
				
	#----------------------------------------------------------------
	# database connect
	#----------------------------------------------------------------	
	def connect (self):
		connopt = self.conninfo.split ("/")
		self.conn = odbc.connect (*tuple (connopt [:3]))
		self.cx = self.conn.cursor ()
		
		if len (connopt) == 4:
			try:
				self.cx.execute ("use %s" % connopt [-1])
			except odbc.Warning:
				pass
			except:
				self.c.close ()
				self.conn.close ()
				raise
		
		self.execute ("set ANSI_NULLS ON; SET ANSI_WARNINGS ON; SET XACT_ABORT ON")
		self.commit ()		
		self.connected = 1
		
	def reconnect (self):
		self.close ()
		self.connect ()
		
	def close (self):
		if not self.connected: return
		
		if self.cx:
			self.execute ("set ANSI_NULLS OFF; SET ANSI_WARNINGS OFF; SET XACT_ABORT OFF")			
			self.commit ()
			try: self.cx.close ()
			except: pass
			self.cx = None
		
		if self.conn: 
			try: self.conn.close ()
			except: pass
			self.cx = None
			
		self.connected = 0
	
	def commit (self):
		self.conn.commit ()
	
	def rollback (self):
		self.conn.rollback ()
	
	def execute (self, query):
		try:
			self.cx.execute (query)			
		
		except odbc.OperationalError:
			raise DBServerError("mxODBC.OperationalError, %s %s %s %s" % tuple (why [:4]))
			
		except Exception as why:
			errstr = "%s %s %s %s" % tuple (why [:4])
			if self.log_query: self.quqeylogger (errstr, query)
			try: raise
			except: what = sys.exc_info()[0]
			raise QueryError("%s, %s" % (what, errstr))
	