from . import confparse
import os
import time
import threading
from functools import reduce

class TimeManager:
	def __init__ (self, confpath, logger = None):
		self.confpath = confpath
		self.conf = None
		self.default_dayplan = 0
		self.todayplan = 0
		self.logger = logger
		self.missions = {}
		self.attain_status = {}
		self.cntobserve = 0
		self.lock = threading.Lock ()
	
	def chk_config (self):
		if self.conf is None:
			self.config_mtime = os.path.getmtime (self.confpath)
			self.conf = confparse.ConfParse (self.confpath)
			return self.set_config ()
		
		ctime = os.path.getmtime (self.confpath)	
		if ctime != self.config_mtime:
			self.logger ("CONFIGURE HAS BEEN CHANGED, REFRESHED...")
			self.conf.refresh ()
			self.config_mtime = ctime
			self.set_config ()
				
	def get_hour (self):
		ch = time.strftime ("%Y%m%d%H", time.localtime (time.time ()))
		self.lock.acquire ()
		if ch not in self.attain_status:
			self.attain_status [ch] = 0
		has_mission = ch in self.missions
		self.lock.release ()
		if not has_mission:
			self.set_mission (ch)
		return ch
	
	def get_date (self):
		cd = time.strftime ("%Y%m%d", time.localtime (time.time ()))
		self.lock.acquire ()
		if cd not in self.attain_status:
			self.attain_status [cd] = 0
		self.lock.release ()
		return cd	
		
	def observe (self):
		while 1:			
			self.cntobserve += 1
			if self.cntobserve == 10:
				self.maintern ()
				self.cntobserve = 0
			
			if self.executable ():
				self.execute ()
			else:
				time.sleep (self.get_loose_time ())
		
	def get_varioubles (self):
		current_time = time.localtime (time.time ())
		hour = current_time [3]
		seconds = current_time [4] * 60 + current_time [5]
		
		hourplan = self.get_hourplan (hour)
		if hourplan == 0:
			time_resource = 0
		else:	
			time_resource = int ((3600. - seconds) / (3600. / hourplan))			
		return hourplan, time_resource, 3600 - seconds
						
	def set_mission (self, ch):
		self.set_todayplan ()
		if self.todayplan <= 0: return
		minutes = time.localtime (time.time ()) [4]
		hourplan, time_resource, remain_sec = self.get_varioubles ()
		self.lock.acquire ()
		self.missions [ch] = round (float (hourplan) * (remain_sec / 3600.))
		self.lock.release ()
		
	def get_loose_time (self):
		hourplan, time_resource, remain_sec = self.get_varioubles ()
		if time_resource == 0:
			if remain_sec > 60:				
				loose_time = 60
			else:
				loose_time = remain_sec
		else:
			loose_time = float (remain_sec) / time_resource
			
		if loose_time >= 60.0:
			loose_time = 60.
		elif loose_time < 1.0:
			loose_time = 1.0
			
		return loose_time
		
	def executable (self, log = True):
		self.chk_config ()
		if self.todayplan <= 0:
			if log:
				self.logger ("NO TODAY'S PLAN TO EXECUTE...")
			return False
			
		h = self.get_hour ()
		d = self.get_date ()				
		hourplan, time_resource, remain_min = self.get_varioubles ()		
		
		self.lock.acquire ()
		attain_day, attain_hour, missions_hour = self.attain_status [d], self.attain_status [h], self.missions [h]
		self.lock.release ()
		
		if log:
			self.logger ("DAY: %d/%d HOUR: %d(%dLFT)/%d TM RSRCS: %dLFT" % (
					attain_day, self.todayplan, attain_hour, missions_hour, hourplan, time_resource
				)
			)			
		if hourplan <= 0:
			return False
		
		return missions_hour > time_resource
	
	def maintern (self):
		h = self.get_hour ()
		self.lock.acquire ()
		for hour in list(self.missions.keys ()):
			if hour != h: 
				del self.missions [hour]
		self.lock.release ()
		
	def dec_mission (self):
		h = self.get_hour ()
		d = self.get_date ()
		
		self.lock.acquire ()		
		self.missions [h] -= 1
		self.attain_status [h] += 1
		self.attain_status [d] += 1
		self.lock.release ()
	
	def inc_mission (self):
		h = self.get_hour ()
		d = self.get_date ()
		
		self.lock.acquire ()
		self.missions [h] += 1
		self.attain_status [h] -= 1
		self.attain_status [d] -= 1
		self.lock.release ()
		
	def refresh_mission (self):
		self.set_mission (self.get_hour ())
		self.executable ()
	
	def _which_mean (self, val):
		percentage = False
		if val [-1] == "%":
			percentage = True
			val = val [:-1]
		val = int (val)
		return val, percentage
	
	def set_todayplan (self):		
		today = self.get_date ()
		val = self.conf.getopt ("holydayplan", today)
		if not val:
			val = self.conf.getopt ("holydayplan", "*" + today [4:])						
		if val:
			num, percentage = self._which_mean (val)
			if percentage:
				self.todayplan = self.default_dayplan * (num/100.)
				return
			else:
				self.todayplan = num
				return
		
		weekday = int (time.strftime ("%w", time.localtime (time.time ())))
		self.todayplan = self.dayplan [weekday]
		
	def gapfill (self, lst, default):
		hasval = [x for x in lst if x != -1]
		if not hasval:
			for i in range (len (lst)):
				lst [i] = default
			return
		
		elif len (hasval) == 1:
			for i in range (len (lst)):
				lst [i] = hasval [0]
			return			
		
		if lst [0] == -1 or lst [-1] == -1:
			fgaps = 0
			for val in lst:
				if val != -1: 
					lval = val
					break					
				fgaps += 1
			
			tmp = lst [:]
			tmp.reverse ()
			
			bgaps = 0
			for val in tmp:
				if val != -1: 
					fval = val
					break					
				bgaps += 1
		
			step = float (lval - fval) / (fgaps + bgaps + 1)
			for i in range (fgaps):
				lst [i] = int (fval + (step * (bgaps + i + 1)))
			
			j = 0
			for i in range (len (lst) - bgaps, len (lst)):
				j += 1
				lst [i] = int (fval + (step * j))
		
		while [x for x in lst if x == -1]:
			for index in range (len (lst)):
				if lst [index] == -1: 
					fval = lst [index - 1]
					break	
			
			gaps = 0
			for index2 in range (index, len (lst)):
				if lst [index2] != -1: 
					lval = lst [index2]
					break	
				gaps += 1
			
			if gaps:
				step = float (lval - fval) / (gaps + 1)
				j = 0
				for idx in range (index, index2):
					j += 1
					lst [idx] = int (fval + (step * j))			
		
		return lst		
		
	WEEK = ["sun","mon","tue","wen","thu","fri","sat"]			
	def set_config (self):	
		def calc_dayplan (val):
			num, percentage = self._which_mean (val)
			if percentage:
				plan = self.default_dayplan * (num/100.)				
			else:
				plan = num
			return int (plan)
				
		self.default_dayplan = self.conf.getint ("setting", "default_dayplan")
		self.dayplan = [-1] * 7
		self.timeplan = [-1] * 24		
		for k, v in list(self.conf.getopt ("dayplan").items ()):
			self.dayplan [self.WEEK.index (k.lower ())] = calc_dayplan (v)		
		self.gapfill (self.dayplan, self.default_dayplan)
		
		for k, v in list(self.conf.getopt ("timeplan").items ()):
			self.timeplan [int (k [:-1])] = v.count ("-") * 10
			
		self.gapfill (self.timeplan, 100)
		sum = reduce (lambda x, y: x + y, self.timeplan)
		if sum != 0:
			self.timeplan = [float (x) / sum for x in self.timeplan]				
		self.set_user_config ()
		self.set_todayplan () 
		self.refresh_mission ()
	
	def set_user_config (self):	
		pass
										
	def execute (self):
		global req_queue
		if self.executable (False):
			pass
	
	def get_hourplan (self, hour):
		return int (self.todayplan * self.timeplan [hour])
		
	def notify (self, success):			
		if success:
			self.dec_mission ()
		else:
			self.inc_mission ()	
		
