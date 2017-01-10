import odbc, dbi
from . import logger
import sys
import threading
import re

RX_NONASC = re.compile (r"[^\x01-\x80]")
def sqlsafe_value (value):
	global RX_NONASC	
	if value in ('', None):
		value = 'NULL'
	
	elif type (value) == type (''):
		value = RX_NONASC.sub (' ', value)
		value = value.replace (chr(0) ,"").replace ("'", "''").strip ()		
		if not value:
			value = 'NULL'
		else:
			value = "'%s'" % value
			
	else:
		value = str (value)
		
	return value	

def sqlsafe (*values):
	result = []
	for value in values:
		result.append (sqlsafe_value (value))
	return tuple (result)


class NoError (Exception): pass
class IntegrityError (Exception): pass
class ProgramError (Exception): pass
class OperationError (Exception): pass
class InternalError (Exception): pass
class DBServerError (Exception): pass

class QueryLogger:
	def __init__ (self, logger = None):
		self.logger = logger

	def __call__ (self, catch, query):
		self.log (catch, query)

	def log (self, catch, query):
		if self.logger:
			self.logger.log ("%s %s" % (catch, query))

class odbcf:
	def __init__ (self, conninfo, logger = None, log_query = 1):
		self.conninfo = conninfo
		self.logger = logger
		self.log_query = log_query
		self.quqeylogger = QueryLogger (logger)
		self.conn = None
		self.cx = None
		self.cv = threading.Lock ()
		self.connected = 0
		self.autocommit = False

	def __getattr__ (self, attr):
		if self.cx:
			return getattr (self.cx, attr)
		else:
			raise AttributeError
	
	def setautocommit (self, flag):
		self.autocommit = flag		
		
	def log (self, line, type="info", name=""):
		if self.logger:
			self.logger.log (line, type, name)
		else:
			print(line)

	def trace (self, name = ""):
		if self.logger:
			self.logger.trace (name)
		else:
			print(logger.trace ())

	#----------------------------------------------------------------
	# database connect
	#----------------------------------------------------------------
	def connect (self):
		connopt = self.conninfo.split ("/")
		
		try:
			self.conn = odbc.odbc ("/".join (connopt [:3]))
			self.conn.setautocommit (self.autocommit)
			self.cx = self.conn.cursor ()
			self.connected = 1
			
			if len (connopt) == 4:
				self.execute ("use %s" % connopt [-1])
				self.commit ()
				
			self.execute ("set ANSI_NULLS ON; SET ANSI_WARNINGS ON;")
			self.commit ()
			
		except (dbi.opError, dbi.internalError) as why:
			raise DBServerError(str (sys.exc_info()[0]) + ", " + str (why))
		
		except (dbi.noError, dbi.integrityError, dbi.progError) as why:
			self.close ()
			raise DBServerError(str (sys.exc_info()[0]) + ", " + str (why))
		
	def reconnect (self):
		self.close ()
		self.connect ()
	
	def abort (self):
		self.cx = None
		self.conn = None
		self.connected = 0		
		return
		
	def close (self):		
		if not self.connected: 
			return
		
		try:	
			if self.cx:
				self.execute ("set ANSI_NULLS OFF; SET ANSI_WARNINGS OFF;")
				self.commit ()
				try: 
					self.cx.close ()
				except: 
					pass				
	
			if self.conn:
				try: 
					self.conn.close ()					
				except: 
					pass				
	
		finally:
			self.abort ()
			
	def commit (self):
		if not self.autocommit:
			self.conn.commit ()		

	def rollback (self):
		if not self.autocommit:
			self.conn.rollback ()
	
	def handle_expt (self, why, query):	
		errstr = str (why)
		if self.log_query: self.quqeylogger (errstr, query)			
		return errstr
		
	def execute (self, query):
		if not self.connected: 
			raise DBServerError("Not Connected")
			
		try:
			self.cx.execute (query)
		
		except dbi.opError as why:
			errmsg = self.handle_expt (why, query)
			raise OperationError(errmsg)
		
		except dbi.internalError as why:
			errmsg = self.handle_expt (why, query)
			raise InternalError(errmsg)
			
		except dbi.noError as why:
			errmsg = self.handle_expt (why, query)
			raise NoError(errmsg)
			
		except dbi.integrityError as why:
			errmsg = self.handle_expt (why, query)
			raise IntegrityError(errmsg)
		
		except dbi.progError as why:
			errmsg = self.handle_expt (why, query)
			raise ProgramError(errmsg)

