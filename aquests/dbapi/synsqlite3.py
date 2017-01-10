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
		
	def close (self):	
		if self.cur:
			self.cur.close ()
			self.cur = None
		if self.conn:	
			self.conn.close ()			
			self.conn = None	
		self.connected = False	
		dbconnect.DBConnect.close (self)
	
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
				
	def execute (self, callback, sql):
		self.begin_tran (callback, sql)		
		if not self.connected:
			self.connect ()
		
		tranaction = False
		sql= sql.strip ()
		try:
			if sql [:7].lower () == "select ":
				self.cur.execute (sql)
			else:	
				tranaction = True
				self.cur.executescript (sql)
		except:
			if tranaction: self.conn.rollback ()
			self.handle_error ()
		else:
			if tranaction: self.conn.commit ()
			self.has_result = True		
			self.close_case ()
		