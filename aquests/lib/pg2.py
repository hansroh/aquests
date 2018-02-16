from . import db3
import psycopg2

class open (db3.open):
	def __init__ (self, dbname, user, password, host = '127.0.0.1', port = 5432):
		self.conn = psycopg2.connect (host=host, dbname=dbname, user=user, password=password, port = port)
		self.create_cursor ()
	
	def as_dict (conn, row):
		return dict ([(f, row [i]) for i, f in enumerate ([x.name for x in conn.description])])	
	
		