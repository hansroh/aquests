import win32pdh
import win32process
import win32event
import pywintypes

def timeout_execute (cmd, timeout = 0):
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


def get_child_pid (cpid):
	object = 'Process'
	items, instances = win32pdh.EnumObjectItems(None, None, object, 
	                                           win32pdh.PERF_DETAIL_WIZARD)
	instance_dict = {}
	for instance in instances:
		try:
			instance_dict[instance] = instance_dict[instance] + 1
		except KeyError:
			instance_dict[instance] = 0
	
	processinfos = []		
	for instance, max_instances in list(instance_dict.items()):
		for inum in range(max_instances+1):
			processinfo = []
			hq = win32pdh.OpenQuery()
			hcs = []
			for item in ['ID Process', 'Creating Process ID']:
				path = win32pdh.MakeCounterPath((None,object,instance,None,inum,item))
				hcs.append(win32pdh.AddCounter(hq,path))
			win32pdh.CollectQueryData(hq)
			processinfo.append (instance[:15].strip ())
			#print "%-15s\t" % (instance[:15]),
			for hc in hcs:
				type,val=win32pdh.GetFormattedCounterValue(hc,win32pdh.PDH_FMT_LONG)
				processinfo.append (int (val))
				#print "%5d" % (val),
				win32pdh.RemoveCounter(hc)
			#print
			win32pdh.CloseQuery(hq)
			processinfos.append (tuple (processinfo))
	
	def recusive (cpid):
		pids = []
		for name, pid, ppid in processinfos:
			if ppid == cpid:
				pids.append (pid)
		for pid in pids:
			pids += recusive (pid)		
		return pids	
	
	pids = recusive (cpid)	
	return pids

if __name__ == "__main__":
	print(get_child_pid (3172))
	

