import sqlite3
import json
import zlib
import warnings

warnings.simplefilter('default')
warnings.warn (
   "db3 will be deprecated, use sqlphile.db3",
    DeprecationWarning
)

class open:
	def __init__ (self, path):		
		self.conn = sqlite3.connect (path, check_same_thread = False)
		self.create_cursor ()
	
	def create_cursor (self):	
		self.cursor = self.c = self.conn.cursor ()
	
	def to_safe_tuple (self, karg):
		revised = []
		for k, v in karg.items ():
			if isinstance (v, sqlite3.Binary):
				pass
			elif k in (None, ''):
				v = 'null'
			elif isinstance (v, str):
				v = "'{}'".format (v.replace ("'", "''"))
			else:
				v = str (v)
			revised.append ((k, v))
		return revised	
	
	def to_tuple (self, karg):
		revised = []
		for k, v in karg.items ():			
			revised.append ((k, v))
		return revised	
		
	def patch (self, tbl, karg, cond = None):
		tp = self.to_tuple (karg)
		sql = "update {} {}".format (
			tbl,
			",".join (["%s=?".format (k, v) for k, v in tp]),
			cond and "where " + cond or ""
		)
		self.c.execute (sql, tuple ([v for k, v in tp]))
		
	def post (self, tbl, karg):
		tp = self.to_tuple (karg)
		sql = "insert into {} ({}) values ({})".format (
			tbl,
			",".join ([k for k, v in tp]),
			",".join (["?"] * len (tp))
		)		
		self.c.execute (sql, tuple ([v for k, v in tp]))
	
	def __enter__ (self):
		return self
	
	def __exit__ (self, type, value, tb):
		self.c.close ()
		self.conn.close ()
		
	def __getattr__ (self, name):
		return getattr (self.c, name)
	
	def commit (self):	
		return self.conn.commit ()
	
	def rollback (self):	
		return self.conn.rollback ()	

	def serialize (self, obj):
		return zlib.compress (json.dumps (obj).encode ("utf8"))	
	
	def deserialize (self, data):
		return json.loads (zlib.decompress (data).decode ('utf8'))
	
	def blob (self, obj):
		return sqlite3.Binary (obj)
	
	def field_names (self):
		return [x [0] for x in self.description]
		
	def as_dict (self, row, field_names = None):		
		return dict ([(f, row [i]) for i, f in enumerate (field_names or self.field_names ())])
	
	def fetchone (self, as_dict = False):
		return self.fetchmany (1, as_dict)[0]
		
	def fetchall (self, as_dict = False):
		return self.fetchmany (0, as_dict)
	
	def fetchmany (self, limit, as_dict = False):
		rows = limit and self.cursor.fetchmany (limit) or self.cursor.fetchall ()
		if not as_dict:
			return rows		
		field_names = self.field_names ()
		return [self.as_dict (row, field_names) for row in rows]
			
		