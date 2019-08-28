from rs4 import asyncore
import socket
from .select_trigger import trigger

the_trigger = None
the_logger = None

def start_trigger (logger = None):
	global the_trigger, the_logger
	the_logger = logger
	if the_trigger is None:
		the_trigger = trigger (logger)

def wakeup (thunk = None):
	global the_trigger, the_logger
		
	if the_trigger is None:
		if thunk:
			try:
				thunk ()
			except:
				if the_logger:
					the_logger.trace ('wakeup')
		return		

	try:
		the_trigger.pull_trigger(thunk)
	except OSError as why:
		if why.errno == 32:
			the_trigger.close ()
			the_trigger = trigger ()
			the_trigger.pull_trigger(thunk)
	except socket.error:
		the_trigger.close ()
		the_trigger = trigger ()
		the_trigger.pull_trigger(thunk)
			
def wakeselect ():
	for fd, obj in list(asyncore.socket_map.items()):
		if hasattr(obj, "pull_trigger"):
			obj.pull_trigger()
