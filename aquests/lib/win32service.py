import win32serviceutil

def is_service_running (service, machine=''):
	if win32serviceutil.QueryServiceStatus(service, machine)[1] == 4:
		return True
	else:
		return False
	
def service_control(service, action, machine=''):
	if action == 'stop':
		try:
			win32serviceutil.StopService(service, machine)
			return True
		except:
			return False
	elif action == 'start':
		try:
			win32serviceutil.StartService(service, machine)
			return True
		except:
			return False             
	elif action == 'restart':
		try:
			win32serviceutil.RestartService(service, machine)
			return True
		except:
			return False
	elif action == 'status':
		if win32serviceutil.QueryServiceStatus(service, machine)[1] == 4:
			return True
		else:
			return False
	
	else:
		raise ValueError("Unknown Command")



	    