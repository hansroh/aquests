import asyncore
import multiprocessing
import time
import sys
import os
from . import pathtool
import types
import codecs

PY_MAJOR_VERSION = sys.version_info.major

def trace ():
	(file,fun,line), t, v, tbinfo = asyncore.compact_traceback()
	try:
		v = str (v)
	except UnicodeEncodeError:
		pass
	return "%s %s Traceback: %s" % (t, v, tbinfo)
		
def now (detail = 1):
	if detail: return time.strftime("%Y.%m.%d %H:%M:%S", time.localtime(time.time()))
	else: return time.strftime("%Y%m%d", time.localtime(time.time()))

def ago (t):
	diff = time.time () - t
	if diff < 3600:
		return "%2.1f minutes ago" % (diff/60)
	elif diff < 3600	 * 24:
		return "%2.1f hours ago" % (diff/3600)
	elif diff < 3600	 * 72:
		return "%2.1f days ago" % (diff/(3600 * 24))	
	return time.strftime ("%Y-%m-%d", time.localtime (t))

	
class base_logger:
	def __init__(self, out, cacheline = 100, flushnow = 0):
		self.out = out
		self.cacheline = cacheline
		self.flushnow = flushnow
		self.lock = multiprocessing.Lock()
		self.filter = []
		self.__cache = []		
	
	def set_filter (self, *types):	
		self.filter = types
		
	def __call__(self, line, type="info", name=""):
		return self.log (line, type, name)
	
	def write (self, line, type="", name=""):
		return self.log (line, type, name)
	
	def cleanup (self):			
		self.close ()
		
	def flush (self): 
		try:
			self.out.flush ()
		except:
			pass	
	
	def cache (self, line):
		if self.cacheline:
			self.__cache.insert (0, line)
			self.__cache = self.__cache [:self.cacheline]
	
	def tag (self, type, name):
		try:
			name = str (name)
		except UnicodeEncodeError:
			pass
			
		tag = ""
		if type: 
			tag = "[%s%s] " % (type, name and ":" + name or "")
		return tag
		
	def log (self, line, type = "info", name = ""):
		line = str (line).strip ()
		line = "%s %s%s\n" % (now(), self.tag (type, name), line)
		
		if self.filter and type not in self.filter:
			return line
		
		self.lock.acquire ()	
		try:
			self.out.write (line)
		except UnicodeEncodeError:			
			self.out.write (repr (line.encode ("utf8")))
		if self.flushnow: self.flush ()
		self.cache (line)
		self.lock.release ()
		return line
		
	def close (self): 
		self.out.close ()
	
	def trace (self, name = ''):
		return self.log (trace (), "expt", name)	
	traceback = trace	
	
	def read (self):
		return self.__cache
		
	
class screen_logger (base_logger):
	def __init__ (self, cacheline = 200, flushnow = 1):
		base_logger.__init__(self, sys.stdout, cacheline, flushnow)
	
	def log (self, line, type = "info", name = ""):
		if type.startswith ("expt"):
			line = trace ().replace ("] [", "\n  - ")
			line = line.replace ("Traceback: [", "\n  -----------\n  + Traceback\n  ===========\n  - ")
			line = line [:-1] + "\n  -----------"
		base_logger.log (self, line, type, name)			
	
	def close (self): 
		pass


class null_logger (screen_logger):
	def log (self, line, type = "info", name = ""): 
		pass
		

class pipe_logger (screen_logger): 
	def __init__ (self):
		screen_logger.__init__(self, 0, 1)
	
	def log (self, line, type = "info", name = ""):		
		# do not write datetime
		if isinstance (line, str):
			line = line.encode ("ascii", "ignore")
			
		line = str (line).strip ()
		line = "%s%s\n" % (self.tag (type, name), line)
		
		if self.filter and type not in self.filter:
			return line
			
		self.lock.acquire ()
		self.out.write (line)
		if self.flushnow: self.flush ()
		self.cache (line)
		self.lock.release ()
		return line


class rotate_logger (base_logger):
	def __init__(self, base, surfix = '', freq = "daily", cacheline = 200, flushnow = 0):
		self.base = base
		self.surfix = surfix
		self.freq = freq
		
		pathtool.mkdir (base)
		self.file = "%s/%s.log" % (self.base, self.surfix)
		
		base_logger.__init__ (self, codecs.open (self.file, "a", "utf8"), cacheline, flushnow)
				
		self.cv = multiprocessing.Condition (multiprocessing.RLock())
		self.using = 0
		self.numlog = 0
		self.maintern ()
		self.rotate_when = self.get_next_rotate (self.freq)
		
	def maybe_rotate (self):
		if self.freq and time.time() > self.rotate_when:
			self.rotate()
			self.rotate_when = self.get_next_rotate (self.freq)
		        
	def get_next_rotate (self, freq = "daily"):
		(yr, mo, day, hr, min, sec, wd, jday, dst) = time.localtime(time.time())
		if freq == 'daily':
			return time.mktime((yr,mo,day+1, 0,0,0, 0,0,-1))
			#return time.mktime((yr,mo,day, hr,min,sec+10, 0,0,-1))
		elif freq == 'weekly':
			return time.mktime((yr,mo,day-wd+7, 0,0,0, 0,0,-1))
		elif freq == 'monthly':
			return time.mktime((yr,mo+1,1, 0,0,0, 0,0,-1))
		else:
			return time.mktime((yr,mo,day+1, 0,0,0, 0,0,-1))
				
	def maintern (self):
		dlogs = []
		for file in os.listdir (self.base):
			if file.find (self.surfix + "-") != 0: continue 			
			dlogs.append (file) 
		
		if len (dlogs) <= 100: return
		dlogs.sort ()
		for file in dlogs [:-100]:
			try: os.remove (os.path.join (self.base, file))
			except: pass
		
	def rotate (self):
		self.cv.acquire ()
		try:
			self.out.close ()		
			(yr, mo, day, hr, min, sec, wd, jday, dst) = time.localtime(time.time())
			newfile = "%s/%s-%04d%02d%02d.log" % (self.base, self.surfix, yr, mo, day)
			if os.path.isfile (newfile):
				 newfile = "%s/%s-%04d%02d%02d-%02d%02d%02d.log" % (self.base, self.surfix, yr, mo, day,hr, min, sec)		
			try:
				os.rename (self.file, newfile)
			except:
				self.out = codecs.open (self.file, "a", "utf8")
			else:	
				self.out = codecs.open (self.file, "w", "utf8")
			self.maintern ()
			
		finally:			
			self.cv.release ()		
	
	def close (self):
		self.cv.acquire ()
		while self.using:
			self.cv.wait ()			
		try:
			base_logger.close (self)	
		finally:	
			self.cv.release ()
			
	def log (self, line, type="info", name=""):
		try:
			line = str (line)
		except UnicodeEncodeError:
			pass
		
		lline = "%s %s%s\n" % (now(), self.tag (type, name), line)		
		if self.filter and type not in self.filter:
			return lline
		
		self.cv.acquire ()
		self.using = 1		
		try:
			self.out.write (lline)
			if self.flushnow: self.flush ()
			self.cache (line)
		except:
			self.out.write ("%s %%s\n", (now(), self.tag (type, name), repr (line)))
			
		self.using = 0
		self.numlog += 1
		numlog = self.numlog
		self.cv.notify_all ()
		self.cv.release ()
		
		if numlog % 1000 == 0:
			self.maybe_rotate ()
			
		return line		


class file_logger (rotate_logger):
	def __init__ (self, base, surfix = '', *arg, **karg):
		rotate_logger.__init__ (self, base, surfix)
		
	
class multi_logger (base_logger):
	def __init__(self, loggers = [], cacheline = 100, flushnow = 0):
		self.loggers = []
		for logger in loggers:
			self.loggers.append (logger)
			
		base_logger.__init__ (self, None, cacheline, flushnow)
	
	def rotate (self):
		for logger in self.loggers:
			hasattr (logger, 'rotate') and logger.rotate ()
			
	def log (self, line, type="info", name=""):
		if self.filter and type not in self.filter:
			return line
		
		for logger in self.loggers:
			_lline = logger.log (line, type, name)	
				
		self.cache (_lline)
		
	def add_logger (self, logger):
		self.loggers.append (logger)		
		
	def close (self):
		for logger in self.loggers:
			logger.close ()




if __name__ == "__main__":
	l = file_logger ("x:/test/", "test")			
	for i in range (300):
		l.write ("asdsadasda")
	l.close ()
	
