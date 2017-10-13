import sqlite3
import json
import zlib

class open:
	def __init__ (self, path):		
		self.conn = sqlite3.connect (path)
		self.c = self.conn.cursor ()
	
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


def blob (obj):
	sqlite3.Binary (util.serialize (obj))

def serialize (obj):
	return zlib.compress (json.dumps (obj).encode ("utf8"))	

def deserialize (data):
	return json.loads (zlib.decompress (data).decode ('utf8'))

