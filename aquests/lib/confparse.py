#!/usr/bin/env python

import re, io, os

# exception classes
class NotFileError (Exception): pass
class FileNotFound (Exception): pass
class NotFileNameError (Exception): pass
class NotStringError (Exception): pass
class UnknownSectorType (Exception): pass
class MissingSectionHeaderError (Exception): pass
class ParsingError (Exception): pass
class SectionError (Exception): pass
class ChoiceObjectRequired (Exception): pass
class NotOptionSection (Exception): pass
class CondtionExpressionError (Exception): pass
class OptionNotFound (Exception): pass
class NotOptionType (Exception): pass

SECT = re.compile (r'\[(.+)\]')
OPTCRE = re.compile(r'(?P<option>[^:=\s][^:=]*)\s*(?P<vi>[:=])\s*(?P<value>.*)$')
LINESPLIT = re.compile (r'[\r\n]+')
TPAIR = 'pair'
TLINE = 'line'
TDATA = 'data'

class ConfParse:
	return_none = 1
	def __init__ (self, fn = None):
		self.conf = {}
		self.fn = fn
		self.sectionlist = []
		if self.fn: self.read (self.fn)		

	def refresh (self):
		if self.fn:
			self.conf = {}
			self.read (self.fn)

	def __getitem__ (self, sector):
		return self.conf [sector]

	def status (self):
		return self.conf
		
	def __delitem__ (self, sector):
		del self.conf [sector]
		try:
			idx = self.sectionlist.index (sector)
		except ValueError:
			pass
		else:
			del self.sectionlist [idx]
			
	def __setitem__ (self, sector, data):
		self.conf [sector] = data
		try:
			self.sectionlist.index (sector)
		except ValueError:
			self.sectionlist.append (sector)		

	def has_key (self, key):
		return key in self.conf

	def set_conf (self, conf):
		self.conf = conf

	def matched (self, search):
		return [ sect for sect in list(self.conf.keys ()) if sect.find (search) == 0 ]

	def keys (self):
		return list(self.conf.keys ())

	def items (self):
		return list(self.conf.items ())

	def _secttype (self, secttype):
		if secttype == TPAIR: return {}
		elif secttype == TLINE: return []
		else: return ''

	def read (self, fn = None):
		if fn:	self.fn = fn
		else: fn = self.fn
		
		self.conf = {}		
		try: fp = open (fn, 'r')
		except: raise FileNotFound
		self._read (fp)
		fp.close ()

	def read_from_string (self, data):
		fp = io.StringIO ()
		fp.write (data)
		fp.seek (0)
		self._read (fp)
		fp.close ()

	def read_from_stream (self, fp):
		self._read (fp)

	def _read (self, fp):
		cursect = None
		optname = None
		secttype = None

		while 1:
			line = fp.readline ()
			if not line: break
			# if data, do not any change for line

			if (not secttype or (secttype and secttype not in  (TDATA, TLINE))) and (line.strip() == '' or line[0] in '#;'):
				continue

			# if pair, continuation line?
			if secttype and secttype in (TPAIR, TLINE) and line[0].isspace() and cursect is not None:
				value = line.strip()
				if value:
					if secttype == TPAIR:
						if not optname: raise OptionNotFound
						self.conf[cursect][optname] += "%s" % value

					else:
						self.conf[cursect][0] += "%s" % value

			match = SECT.match(line)

			# sector
			if match:
				cursect = match.group(1)
				try:
					[ cursect, secttype ] = [x.strip() for x in cursect.split(':')]
				except ValueError:
					[ cursect, secttype ] = cursect.strip(), TPAIR
				secttype = secttype.strip()

				if secttype not in (TPAIR, TLINE, TDATA):
					raise UnknownSectorType("%s:%s" % (cursect, secttype))
				self.conf [cursect] = self._secttype (secttype)
				self.sectionlist.append (cursect)

			elif not cursect:
				raise MissingSectionHeaderError

			else:
				curconf = self.conf[cursect]
				if secttype == TLINE:
					line = line.strip()
					if line: curconf.append (line)

				elif secttype == TDATA:
					curconf += line

				else:
					match = OPTCRE.match (line)
					if match:
						optname, vi, optval = match.group('option', 'vi', 'value')
						if vi in ('=', ':') and ';' in optval:
							pos = optval.find(';')
							if pos != -1 and optval[pos-1].isspace():
								optval = optval[:pos]
						optval = optval.strip()

						if optval == '""': optval = ''

						optname = optname.rstrip()
						curconf[optname] = optval

					else:
						raise ParsingError
				self.conf[cursect] = curconf
		fp.close ()

	def sections (self):
		return list(self.conf.keys())

	def getboolean (self, section, option = None):
		if not option:
			raise OptionNotFound
		value = self.getopt (section, option)

		if not value: return False
		if value.lower () in ('1', 'yes'): return True
		return False

	def getint (self, section, option = None, default = None):
		if not option:
			raise OptionNotFound
		value = self.getopt (section, option)
		try: return int (value)
		except: return default

	def getfloat (self, section, option = None, default = None):
		if not option:
			raise OptionNotFound
		value = self.getopt (section, option)
		try: return float (value)
		except: return default

	def getopt (self, section, option = None, defualt = None, preserve_comment = False):
		try: self.conf[section]
		except KeyError:
			if self.return_none: return defualt
			raise SectionError

		if not option:
			opt = self.conf[section]
			if type (opt) == type (''):
				opt = opt.replace ('\r', '').strip () + '\n'
			elif type (opt) == type ([]):
				if not preserve_comment:
					opt = [x for x in opt if x and x [0] not in "#;"]
			return opt

		try:
			return self.conf[section][option]
		except KeyError:
			if self.return_none: return defualt
			raise OptionNotFound

	def makesect (self, section, secttype = TPAIR):
		if section not in self.conf:
			self.sectionlist.append (section)
		self.conf[section] = self._secttype (secttype)

	def setsect (self, section, data):
		if section not in self.conf:
			self.sectionlist.append (section)
		self.conf[section] = data		

	def setint (self, section, option, value):
		if type (self.conf[section]) == type ({}):
			self.conf[section][option.strip ()] = int (value.strip ())

	def setfloat (self, section, option, value):
		if type (self.conf[section]) == type ({}):
			self.conf[section][option.strip ()] = float (value.strip ())

	def setopt (self, section, option, value = ''):
		try: self.conf[section]
		except KeyError: raise SectionError

		if type (self.conf[section]) == type ({}):
			if type (option) == type ({}):
				self.conf[section] = option
			else:	
				if value is None: value = ""
				self.conf[section][option.strip ()] = value.strip ()

		elif type (self.conf[section]) == type (''):
			if option is None: option = ""
			self.conf[section] = option.strip ()

		elif type (self.conf[section]) == type ([]):
			if option is None: option = []
			if type (option) == type (""):
				option = LINESPLIT.split (option)
				option = [_f for _f in [x.strip() for x in option] if _f]
			self.conf[section] = option

	def write (self, fp):
		for sect in self.sectionlist:
			try:
				data = self.conf [sect]
			except KeyError:
				continue													
			if type (data) == type ({}):
				fp.write ("[%s]\n" % sect)
				for k, v in list(data.items ()): fp.write ("%s = %s\n" % (k, v))
				fp.write ("\n\n")

			elif type (data) == type ([]):
				fp.write ("[%s:%s]\n" % (sect, TLINE))
				for l in data: fp.write ("%s\n" % l)
				fp.write ("\n\n")

			elif type (data) == type (''):
				fp.write ("[%s:%s]\n" % (sect, TDATA))
				fp.write ("%s\n" % data.strip())
				fp.write ("\n\n")

	def update (self):
		if not self.fn:
			raise FileNotFound
		fp = open (self.fn, 'w')
		self.write (fp)
		fp.close ()

	def getfilename (self):
		return self.fn
	
	def delopt (self, section, option):
		try:
			del self.conf[section][option]
		except KeyError:	
			pass
		
		

if __name__ == '__main__':
	import os
	for file in os.listdir('../def/')[1:2]:
		print(file)
		if file[0] == '#': continue
		config = ConfParse('../def/' + file)
		print(config.conf)
