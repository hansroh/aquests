from .synsqlite3 import SynConnect
from .dbconnect import DBConnect

class Postgres (SynConnect):
	def connect (self):
		try:
			host, port = self.address		
			self.conn = psycopg2.connect (
				dbname = self.dbname,
				user = self.user,
				password = self.password,
				host = host,
				port = port
			)
		except:
			self.handle_error ()
		else:	
			self.connected = True

    def close_if_over_keep_live (self):
		DBConnect.close_if_over_keep_live (self)	

    def execute (self, request):
		dbconnect.DBConnect.begin_tran (self, request)			
		sql = self._compile (request)
		
		if not self.connected:
			self.connect ()
			self.conn.isolation_level = None
				
		try:
			if self.cur is None:
				self.cur = self.conn.cursor ()
				self.cur.execute (sql, *request.params [1:])
				self.has_result = True
		except:
			self.handle_error ()
		else:			
			self.close_case ()

