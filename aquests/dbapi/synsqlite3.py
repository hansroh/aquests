import sqlite3
from . import dbconnect, asynpsycopg2
import threading

DEBUG = False

class OperationalError (Exception):
	pass


class SynConnect (asynpsycopg2.AsynConnect, dbconnect.DBConnect):
	def __init__ (self, address, params = None, lock = None, logger = None):
		dbconnect.DBConnect.__init__ (self, address, params, lock, logger)
		self.connected = False
		self.conn = None
		self.cur = None
	
	def close_if_over_keep_live (self):
		# doesn't need disconnect with local file
		pass
			
	def is_channel_in_map (self, map = None):
		return False
			
	def close (self, deactive = 1):	
		if self.cur:
			self.cur.close ()
			self.cur = None
		if self.conn:	
			self.conn.close ()			
			self.conn = None	
		self.connected = False	
		dbconnect.DBConnect.close (self, deactive)
	
	def del_channel (self, map=None):
		pass
				
	def close_case (self):
		asynpsycopg2.AsynConnect.close_case (self)
				
	def connect (self):
		try:
			self.conn = sqlite3.connect (self.address, check_same_thread = False)
			self.cur = self.conn.cursor ()
		except:
			self.handle_error ()
		else:	
			self.connected = True
				
	def execute (self, request):
		self.begin_tran (request)		
		if not self.connected:
			self.connect ()
			self.conn.isolation_level = None
		
		sql = request.params [0].strip ()
		try:
			if len (request.params) > 1 or sql [:7].lower () == "select ":
				self.cur.execute (*request.params)
			else:			
				self.cur.executescript (sql)
		except:
			self.handle_error ()
		else:
			self.has_result = True
			self.close_case ()
		