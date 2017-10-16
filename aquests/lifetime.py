import sys, asyncore, time
import gc
import select
import os
import bisect
import socket
import time
import types
from .protocols.dns import asyndns

try:
	from pympler import muppy, summary, tracker
except ImportError:
	pass	

if os.name == "nt":
	from errno import WSAENOTSOCK
	
_shutdown_phase = 0
_shutdown_timeout = 30 # seconds per phase
_exit_code = 0
_last_maintern = 0
_maintern_interval = 3.0
_killed_zombies = 0
_select_errors = 0
_poll_count = 0
_polling = 0
_logger = None

EXHAUST_DNS = True
	
class Maintern:
	def __init__ (self):
		self.q = []
		
	def sched (self, interval, func, args = None):
		now = time.time ()
		self.q.append ((now + interval, interval, func, args))
		self.q.sort (key = lambda x: x [0])
		#bisect.insort (self.q, (now + interval, interval, func, args))
	
	def __call__ (self, now):
		excutes = 0
		for exetime, interval, func, args in self.q:
			if exetime > now: break
			excutes += 1
			if args: 
				func (now, *args)
			else:
				func (now)

		for i in range (excutes):
			exetime, interval, func, args = self.q.pop (0)
			#bisect.insort (self.q, (now + interval, interval, func, args))
			self.q.append ((now + interval, interval, func, args))
			self.q.sort (key = lambda x: x [0])
		
def maintern_gc (now):
	gc.collect ()
	
def maintern_zombie_channel (now, map = None):
	global _killed_zombies
	
	if map is None:
		map = asyncore.socket_map
			
	for channel in list(map.values()):
		if hasattr (channel, "handle_timeout"):
			try:
				# +3 is make gap between server & client
				iszombie = (now - channel.event_time) > channel.zombie_timeout
			except AttributeError:
				continue
			if iszombie:				
				_killed_zombies += 1
				try:
					channel.handle_timeout ()
				except:
					channel.handle_error ()

maintern = None
def init (kill_zombie_interval = 10.0, logger = None):
	global maintern, _logger
	
	_logger = logger
	maintern = Maintern ()
	maintern.sched (kill_zombie_interval, maintern_zombie_channel)
	maintern.sched (300.0, maintern_gc)

summary_tracker = None
def summary_track (now):
	global summary_tracker
	
	all_objects = muppy.get_objects ()
	#all_objects = muppy.filter (all_objects, Type = dict)
	#for each in all_objects:
	#	print (each)
	sum1 = summary.summarize (all_objects)
	summary.print_ (sum1)
	print ('-' * 79)	
	if summary_tracker is None:
		summary_tracker = tracker.SummaryTracker ()
	summary_tracker.print_diff ()	
	
def enable_memory_track (interval = 10.0):
	global maintern	
	maintern.sched (interval, summary_track)	

def shutdown (exit_code, shutdown_timeout = 30.0):
	global _shutdown_phase
	global _shutdown_timeout
	global _exit_code
	
	if _shutdown_phase:
		# aready entered
		return
		
	if _shutdown_phase == 0:
		_exit_code = exit_code
		_shutdown_phase = 1
		
	_shutdown_timeout = shutdown_timeout

def loop (timeout = 30.0):
	global _shutdown_phase
	global _shutdown_timeout
	global _exit_code
	global _polling
	global maintern
	
	if maintern is None:
		init ()
		
	_shutdown_phase = 0
	_shutdown_timeout = 30
	_exit_code = 0	
	_polling = 1
	
	try: 
		lifetime_loop(timeout)
	except KeyboardInterrupt:
		graceful_shutdown_loop()
	else:
		graceful_shutdown_loop()
	
	_polling = 0
	
poll_fun = asyncore.poll

def remove_notsocks (map):
	global _select_errors, _logger
	
	# on Windows we can get WSAENOTSOCK if the client
	# rapidly connect and disconnects
	killed = 0
	for fd, obj in list(map.items()):	
		r = []; w = []; e = []	
		is_r = obj.readable()
		is_w = obj.writable()
		if is_r:
			r = [fd]
		# accepting sockets should not be writable
		if is_w and not obj.accepting:
			w = [fd]
		if is_r or is_w:
			e = [fd]
		
		try:			
			select.select (r, w, e, 0)			
									
		except:
			#_logger and _logger.trace ()			
			killed += 1
			_select_errors += 1
						
			try:
				try: obj.handle_expt ()
				except: obj.handle_error ()
			except:
				_logger and _logger.trace ()
				
			try: del map [fd]
			except KeyError: pass
					
	return killed

def poll_fun_wrap (timeout, map = None):
	global _logger

	if map is None:
		map = asyncore.socket_map	
	
	if EXHAUST_DNS:
		asyndns.pop_all ()	
	
	try:		
		poll_fun (timeout, map)
	except (TypeError, OSError) as why:
		# WSAENOTSOCK
		remove_notsocks (map)
	
	except ValueError:
		# negative file descriptor, testing all sockets
		killed = remove_notsocks (map)
		# or too many file descriptors in select(), divide and conquer
		if not killed:			
			half = int (len (map) / 2)
			tmap = {}
			cc = 0			
			for k, v in list(map.items ()):
				tmap [k] = v
				cc += 1
				if cc == half:
					poll_fun_wrap (timeout, tmap)
					tmap = {}
			poll_fun_wrap (timeout, tmap)
	
	except:
		_logger and _logger.trace ()
		raise
		
def lifetime_loop (timeout = 30.0, count = 0):
	global _last_maintern
	global _maintern_interval

	loop = 0
	map = asyncore.socket_map
	
	while map and _shutdown_phase == 0:		
		poll_fun_wrap (timeout, map)
		now = time.time()
		if (now - _last_maintern) > _maintern_interval:
			maintern (now)
			_last_maintern = time.time ()
		loop += 1
		if count and loop > count:
			break	
		
def graceful_shutdown_loop ():
	global _shutdown_phase
	timestamp = time.time()
	timeout = 1.0
	map = asyncore.socket_map	
	while map and _shutdown_phase < 4:
		time_in_this_phase = time.time() - timestamp
		veto = 0
		for fd,obj in list(map.items()):
			try:
				fn = getattr (obj,'clean_shutdown_control')
			except AttributeError:
				pass
			else:
				try:
					veto = veto or fn (_shutdown_phase, time_in_this_phase)
				except:					
					obj.handle_error()
					
		if veto and time_in_this_phase < _shutdown_timeout:
			poll_fun_wrap (timeout, map)					
		else:
			_shutdown_phase += 1
			timestamp = time.time()
