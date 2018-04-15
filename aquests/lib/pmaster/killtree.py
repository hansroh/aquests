import os

if os.name == "nt":
	import subprocess
	def kill (pid):	
		subprocess.call(['taskkill', '/F', '/T', '/PID', str(pid)])		

else:
	import psutil
	
	def kill (pid, including_parent = True, timeout =10):	
		try: 
			parent = psutil.Process(pid)
		except psutil.NoSuchProcess:
			return
		
		# send SIGTERM
		children = parent.children (recursive = True)
		if including_parent:
			parent.terminate()
			try:
				parent.wait (timeout)
			except psutil.TimeoutExpired:
				pass
		
		# try to terminate children	
		for child in children:
			if not child.is_running ():
				continue			
			try:
				child.terminate()
			except psutil.NoSuchProcess:
				pass
		
		# send SIGKILL 
		if parent.is_running ():
			parent.kill ()
		gone, alive = psutil.wait_procs (children, timeout = timeout)
		for p in alive:			
			p.kill ()
