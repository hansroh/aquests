import os
import pickle as translator
from bsddb import db
from . import pathtool

#--------------------------------------------------------------
# DB creation func
#--------------------------------------------------------------
def _checkflag(flag):
	if flag == 'r':
		flags = db.DB_RDONLY
	elif flag == 'rw':
		flags = 0
	elif flag == 'w':
		flags =  db.DB_CREATE
	elif flag == 'c':
		flags =  db.DB_CREATE
	elif flag == 'n':
		flags = db.DB_CREATE | db.DB_TRUNCATE
	else:
		raise error("flags should be one of 'r', 'w', 'c' or 'n'")
	return flags | db.DB_THREAD

def btopen(file, flag='c', mode=0o666,
			btflags=0, cachesize=None, maxkey=None, minkey=None,
			pgsize=None, lorder=None):

	flags = _checkflag(flag)
	d = db.DB()
	if cachesize is not None: d.set_cachesize(0, cachesize)
	if pgsize is not None: d.set_pagesize(pgsize)
	if lorder is not None: d.set_lorder(lorder)
	d.set_flags(btflags)
	if minkey is not None: d.set_bt_minkey (minkey)
	d.open(file, db.DB_BTREE, db.DB_THREAD | flags, mode)   
	return d 


def zbtopen(*arg, **karg):
	return ZObject (btopen (*arg, **karg))
	
	
#--------------------------------------------------------------
# Z Object Handler Wrapper Classes
#--------------------------------------------------------------
class ZCursor:
	def __init__(self, cursor):
		self.dbc = cursor

	def __del__(self):
		self.close()
		
	def __getattr__(self, name):
		return getattr(self.dbc, name)
		
	def dup(self, flags=0):
		return Zcursor(self.dbc.dup(flags))

	def put(self, key, value, flags=0):
		data = translator.dumps(value, 1)
		return self.dbc.put(key, data, flags)

	def get(self, *args):
		count = len(args)  # a method overloading hack
		method = getattr(self, 'get_%d' % count)
		method(*args)

	def get_1(self, flags):
		rec = self.dbc.get(flags)
		return self._extract(rec)

	def get_2(self, key, flags):
		rec = self.dbc.get(key, flags)
		return self._extract(rec)

	def get_3(self, key, value, flags):
		data = translator.dumps(value, 1)
		rec = self.dbc.get(key, flags)
		return self._extract(rec)

	def current(self, flags=0): return self.get_1(flags|db.DB_CURRENT)
	def first(self, flags=0): return self.get_1(flags|db.DB_FIRST)
	def last(self, flags=0): return self.get_1(flags|db.DB_LAST)
	def next(self, flags=0): return self.get_1(flags|db.DB_NEXT)
	def prev(self, flags=0): return self.get_1(flags|db.DB_PREV)
	def consume(self, flags=0): return self.get_1(flags|db.DB_CONSUME)
	def next_dup(self, flags=0): return self.get_1(flags|db.DB_NEXT_DUP)
	def next_nodup(self, flags=0): return self.get_1(flags|db.DB_NEXT_NODUP)
	def prev_nodup(self, flags=0): return self.get_1(flags|db.DB_PREV_NODUP)

	def get_both(self, key, value, flags=0):
		data = translator.dumps(value, 1)
		rec = self.dbc.get_both(key, flags)
		return self._extract(rec)

	def set(self, key, flags=0):
		rec = self.dbc.set(key, flags)
		return self._extract(rec)

	def set_range(self, key, flags=0):
		rec = self.dbc.set_range(key, flags)
		return self._extract(rec)

	def set_recno(self, recno, flags=0):
		rec = self.dbc.set_recno(recno, flags)
		return self._extract(rec)

	set_both = get_both

	def _extract(self, rec):
		if rec is None:
			return None
		else:
			key, data = rec
			return key, translator.loads(data)
			

class ZObject:
	def __init__ (self, db):
		self.db = db
	
	def __len__(self):
		return len(self.db)
		
	def __setitem__ (self, key, value):
		self.db [key] = translator.dumps (value, 1)
		
	def __getattr__ (self, name):	
		return getattr (self.db, name)
	
	def __delitem__ (self, key):
		del self.db [key]
			
	def __getitem__ (self, key):
		return translator.loads (self.db [key])
		
	def values (self):
		return list(map (translator.loads, list(self.db.values ())))
		
	def items (self):
		return [(k, translator.loads (v)) for k, v in list(self.db.items ())]
	
	def get (self, *args, **kw):
		data = self.db.get(*args, **kw)
		if data:
			return translator.loads (data)
		else:
			return None	
		
	def put(self, key, value, txn=None, flags=0):
		data = translator.dumps (value, 1)
		return self.db.put(key, data, txn, flags)
	
	def cursor(self):
		c = ZCursor(self.db.cursor())		
		return c


#--------------------------------------------------------------
# BTREE bsd file group handler
#--------------------------------------------------------------	
class BT:
	def __init__ (self, home):
		self.home = home
		pathtool.mkdir (home)
		self.setup ()
		self.opened = []
		
	def setup (self):
		pass
					
	def open (self, filename, flag="c", zflag = 0, **karg):
		dbfile = os.path.join (self.home, filename)
		
		if zflag:
			d = ZObject (btopen (dbfile, flag, **karg))
		else:
			d = btopen (dbfile, flag, **karg)
		self.opened.append ((d, dbfile))
		return d
		
	def close (self):
		for db, dbfile in self.opened:			
			try: db.close ()				
			except: pass
		
	
	def remove (self):
		for db, dbfile in self.opened:			
			db.remove (dbfile)			

#--------------------------------------------------------------
# ZObject BTREE bsd file group handler
#--------------------------------------------------------------	
class ZBT (BT):
	def open (self, filename, flag="c"):
		return BT.open (self, filename, flag, 1)	
	

#--------------------------------------------------------------
# Environmental BTREE bsd file group handler
#--------------------------------------------------------------	
class EBT (BT):		
	dbopenflags = db.DB_THREAD
	envflags	= db.DB_THREAD | db.DB_INIT_CDB | db.DB_INIT_MPOOL	
	dbtype  = db.DB_BTREE
	dbsetflags   = 0
	
	def setup (self):
		self.env = db.DBEnv()
		self.setEnvOpts()
		self.env.open (self.home, self.envflags | db.DB_CREATE)
	
	def setEnvOpts(self):
		self.env.set_lk_detect(db.DB_LOCK_DEFAULT)
	
	def open (self, filename, flag="c"):
		d = db.DB(self.env)
		if self.dbsetflags:
			d.set_flags(self.dbsetflags)
		d.open(filename, self.dbtype, self.dbopenflags | _checkflag (flag))
		self.opened.append (d)
		return d
	
	def close (self):
		for db in self.opened:
			try: db.close ()
			except: pass
		try: self.env.close ()
		except: pass

		
if __name__ == "__main__":
	d = ZBT ("test")
	z = d.open ("test", "r")
	z ['a'] = [0,1,2,3,4,5,6]
	z ['b'] = {}
	print(z ['a'])
	print(z ['b'])
	print(list(z.keys ()))
	print(list(z.items ()))
	print(list(z.values ()))
	c = z.cursor ()
	while 1:
		r =  next(c)
		if not r: break
		print(r)
		print(c.current ())
	c.close ()	
	d.close ()