import os

if os.name == "nt":
	import win32process
	import win32event
	import pywintypes
	
	def execute (cmd, timeout = 0):
		if timeout == 0:
			timeout = win32event.INFINITE
			
		info  = win32process.CreateProcess(None, cmd, None, None, 0, 0, None, None, win32process.STARTUPINFO())
		subprocess = info [0]
		
		rc = win32event.WaitForSingleObject (subprocess, timeout)			
		
		if rc == win32event.WAIT_FAILED:	
			return -1
			
		if rc == win32event.WAIT_TIMEOUT:
			try:
				win32process.TerminateProcess (subprocess, 0)					
			except pywintypes.error:
				return -3
			return -2
		
		if rc == win32event.WAIT_OBJECT_0:
			return win32process.GetExitCodeProcess(subprocess)
	
