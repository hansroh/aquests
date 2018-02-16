from . import db3
import psycopg2
import warnings

warnings.simplefilter('default')
warnings.warn (
   "pg2 will be deprecated, use sqlphile.pg2",
    DeprecationWarning
)

class open (db3.open):
	def __init__ (self, dbname, user, password, host = '127.0.0.1', port = 5432):
		self.conn = psycopg2.connect (host=host, dbname=dbname, user=user, password=password, port = port)
		self.create_cursor ()
	
	def field_names (self):
		return [x.name for x in self.description]
