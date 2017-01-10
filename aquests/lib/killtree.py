import os

if os.name == "nt":
	import subprocess
	def kill (pid):	
		subprocess.call(['taskkill', '/F', '/T', '/PID', str(pid)])		

else:
	import psutil
	
	def kill (pid, including_parent = True):	
		parent = psutil.Process(pid)
		children = parent.children(recursive=True)
		for child in children:
			child.kill()
		psutil.wait_procs(children, timeout=5)
		if including_parent:
			parent.kill()
			parent.wait(5)
