from aquests.lib import logger as lf
import os, sys, time
from .puppet import Puppet
import types
from .daemon import Daemonizer

def get_due (s_time = None):
	global START_TIME
	if not s_time:
		s_time = START_TIME
	due = time.time () - s_time
	if due <= 60:
		due = "%d seconds" % due
	elif due <= 3600:
		due = "%2.1f minutes" % (due / 60)
	else:
		due = "%2.1f hours" % (due / 3600)
	return due

SLOTS = {}
TOTAL = 0
PUPPETS_CREATED = 0
MAX_SLOT_ITEMS = 2
HAS_ITEM = True
START_TIME = 0
LAST_REPORT = time.time ()
REPORT_INTERVAL = 3
TIMEOUT = 180
LOGGER = None

def item_empty ():
	global HAS_ITEM
	HAS_ITEM = False

def configure (puppets = 2, timeout = 180, total = 0, report_inveval = 3, logger = None):
	global MAX_SLOT_ITEMS, TIMEOUT, TOTAL, LAST_REPORT, LOGGER
			
	MAX_SLOT_ITEMS = puppets
	TIMEOUT = timeout
	TOTAL = total
	REPORT_INTERVAL = report_inveval
	if not logger:
		LOGGER = lf.screen_logger ()
			
def loop (make_puppet, reporter = None):
	global PUPPETS_CREATED, SLOTS, TOTAL, HAS_ITEM, TIMEOUT
	global START_TIME, LAST_REPORT, LOGGER
	
	if START_TIME == 0:
		START_TIME = time.time ()
	LAST_REPORT = time.time ()
	HAS_ITEM = True
	
	try:			
		while HAS_ITEM or SLOTS:
			if len (SLOTS) < MAX_SLOT_ITEMS and HAS_ITEM:
				if isinstance (make_puppet, (list, tuple)):
					try:
						puppet = make_puppet.pop (0)
					except IndexError:
						puppet = None
				
				elif isinstance (make_puppet, types.GeneratorType):
					try:
						puppet = next (make_puppet)
					except StopIteration:
						puppet = None
				
				else:
					puppet = make_puppet ()
				
				if puppet is None:
					item_empty ()
					continue
					
				PUPPETS_CREATED += 1
				puppet.logger = LOGGER
				SLOTS [id (puppet)] = puppet
				SLOTS [id (puppet)].start ()
			
			for sid in list (SLOTS.keys ()):
				if not SLOTS [sid].is_active ():
					LOGGER ('-- finished %s' % SLOTS [sid])
					SLOTS.pop (sid)
				elif SLOTS [sid].is_timeout (TIMEOUT):
					LOGGER ('-- %s is timeout' % SLOTS [sid])
					SLOTS [sid].kill ()
			
			if time.time () - LAST_REPORT > REPORT_INTERVAL:
				LOGGER ("-- %d active slots, %d processed for %s" % (len (SLOTS), PUPPETS_CREATED, get_due ()))
				if reporter:
					LOGGER (reporter ())
				LAST_REPORT = time.time ()
			time.sleep (PUPPETS_CREATED > MAX_SLOT_ITEMS and  0.1 or 2)
		
	except KeyboardInterrupt:
		for sid in list (SLOTS.keys ()):
			SLOTS [sid].kill ()
			LOGGER ('interrupted, killing %s ...' % SLOTS [sid])
		sys.exit ()
		
	except:	
		LOGGER.trace ()
	