import threading
import time
from . import asynpsycopg2, asynredis, synsqlite3, asynmongo
from ..client import socketpool
from . import DB_PGSQL, DB_SQLITE3, DB_REDIS, DB_MONGODB

class DBPool (socketpool.SocketPool):
		
	def get_name (self):
		return "__dbpool__"
			
	def create_asyncon (self, server, params, dbtype):
		if DB_SQLITE3 in (params [0], dbtype):
			params = ("",) + params [1:]
			return synsqlite3.SynConnect (server, params, self.lock, self.logger)
		
		try: 
			host, port = server.split (":", 1)
		except ValueError:
			host, port = server, 5432
		else:
			port = int (port)
		
		if params [0] == DB_REDIS:
			dbtype = params [0]
			params = ("",) + params [1:]			
		elif params [1] in (DB_MONGODB, DB_PGSQL):	
			dbtype = params [1]
			params = (params [0], "", params [2])
			
		if dbtype == DB_REDIS:
			con_class = asynredis.AsynConnect 
		elif dbtype == DB_MONGODB:			
			con_class = asynmongo.AsynConnect
		elif dbtype == DB_PGSQL:
			con_class = asynpsycopg2.AsynConnect
		asyncon = con_class ((host, port), params, self.lock, self.logger)
		self.backend and asyncon.set_backend ()
		return asyncon
		
	def get (self, server, dbname, auth, dbtype = DB_PGSQL):
		serverkey = "%s/%s/%s" % (server, dbname, auth)
		return self._get (serverkey, server, (dbname, auth), dbtype)


pool = None

def create (logger, backend):
	global pool
	if pool is None:
		pool = DBPool (logger, backend)

def get (server, dbname, auth, dbtype):	
	return pool.get (server, dbname, auth, dbtype)
		
def cleanup ():	
	pool.cleanup ()

		
	

if __name__ == "__main__":
	from skitai import lifetime
	from aquests.lib import logger
	from aquests.server.threads import trigger
	
	trigger.start_trigger ()
	pool = DBPool (logger.screen_logger ())
	
	def query ():
		conn = pool.get ("mydb.us-east-1.rds.amazonaws.com:5432", "mydb", "postgres", "")
		conn.execute ("SELECT * FROM cities;")
		rs = conn.fetchwait (5)
		print(rs.status, rs.result)
		
		conn.execute ("INSERT INTO weather VALUES ('San Francisco', 46, 50, 0.25, '1994-11-27');")		
		rs = conn.wait (5)
		print(rs.status, rs.result)
		
		conn.execute ("INSERT INTO weather VALUES ('San Francisco', 54, 67, 0.25, '1994-11-27');")		
		rs = conn.wait (5)
		print(rs.status, rs.result)
		
		
	threading.Thread (target = query).start ()	
	while threading.activeCount () > 1:
		lifetime.loop ()
		