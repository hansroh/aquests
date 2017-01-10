import winreg
from sys import exit
import time 
import win32api
import win32con
from . import win32service
wa, wc, ws = win32api, win32con, win32service

class WService:
	"""
	The WService Class is used for controlling WinNT, Win2k & WinXP like
	services. Just pass the name of the service you wish to control to the
	class instance and go from there. For example, if you want to control 
	the Workstation service try this:
	 
		import WService
		workstation = WService.WService("Workstation")
		workstation.start()
		workstation.fetchstatus("running", 10)
		workstation.stop()
		workstation.fetchstatus("stopped")

	Creating an instance of the WService class is done by passing the name of
	the service as it appears in the Management Console or the short name as
	it appears in the registry. Mixed case is ok.
		cvs = WService.WService("CVS NT Service 1.11.1.2 (Build 41)")		
			or
		cvs = WService.WService("cvs")

	If needing remote service control try this:
		cvs = WService.WService("cvs", r"\\CVS_SERVER")
			or
		cvs = WService.WService("cvs", "\\\\CVS_SERVER")  
		
	The WService Class supports these methods:
		
		start:		  Starts service.
		stop:		   Stops service.
		restart:		Stops and restarts service.
		pause:		  Pauses service (Only if service supports feature).
		resume:		 Resumes service that has been paused.
		status:		 Queries current status of service.
		fetchstatus:	Continually queries service until requested status(STARTING, RUNNING,
							STOPPING & STOPPED) is met or timeout value(in seconds) reached.
							Default timeout value is infinite.							  
		infotype:	   Queries service for process type. (Single, shared and/or 
							interactive process)
		infoctrl:	   Queries control information about a running service.
							i.e. Can it be paused, stopped, etc?
		infostartup:	Queries service Startup type. (Boot, System, 
							Automatic, Manual, Disabled)
		setstartup	  Changes/sets Startup type. (Boot, System, 
							Automatic, Manual, Disabled)					
		getname:		Gets the long and short service names used by Windows.
							(Generally used for internal purposes)
	"""	
		
	def __init__(self, service, machinename=None, dbname=None):
		self.userv = service
		self.scmhandle = ws.OpenSCManager(machinename, dbname, ws.SC_MANAGER_ALL_ACCESS)
		self.sserv, self.lserv = self.getname()
		if (self.sserv or self.lserv) == None: exit()
		self.handle = ws.OpenService(self.scmhandle, self.sserv, ws.SERVICE_ALL_ACCESS)
		self.sccss = "SYSTEM\\CurrentControlSet\\Services\\"
		
	def start(self):
		ws.StartService(self.handle, None)
		
	def stop(self):
		self.stat = ws.ControlService(self.handle, ws.SERVICE_CONTROL_STOP)

	def restart(self):
		self.stop()
		self.fetchstate("STOPPED")
		self.start()
		
	def pause(self):
		self.stat = ws.ControlService(self.handle, ws.SERVICE_CONTROL_PAUSE)
	
	def resume(self):
		self.stat = ws.ControlService(self.handle, ws.SERVICE_CONTROL_CONTINUE)
		
	def status(self, prn = 0):
		self.stat = ws.QueryServiceStatus(self.handle)
		if self.stat[1]==ws.SERVICE_STOPPED:
			if prn == 1:
				print("The", self.lserv, "service is stopped.")
			else:
				return "STOPPED"
		elif self.stat[1]==ws.SERVICE_START_PENDING:
			if prn == 1:
				print("The", self.lserv, "service is starting.")
			else:
				return "STARTING"
		elif self.stat[1]==ws.SERVICE_STOP_PENDING:
			if prn == 1:
				print("The", self.lserv, "service is stopping.")		
			else:
				return "STOPPING"
		elif self.stat[1]==ws.SERVICE_RUNNING:
			if prn == 1:
				print("The", self.lserv, "service is running.")		
			else:
				return "RUNNING"
				
	def fetchstatus(self, fstatus, timeout=None):
		self.fstatus = fstatus.upper()
		if timeout != None:
			timeout = int(timeout); timeout *= 2
		def to(timeout):
			time.sleep(.5)
			if timeout != None:
				if timeout > 1:
					timeout -= 1; return timeout
				else:
					return "TO"   
		if self.fstatus == "STOPPED":
			while 1:
				self.stat = ws.QueryServiceStatus(self.handle)
				if self.stat[1]==ws.SERVICE_STOPPED:
					self.fstate = "STOPPED"; break
				else:
					timeout=to(timeout)
					if timeout == "TO":
						return "TIMEDOUT"; break
		elif self.fstatus == "STOPPING":
			while 1:
				self.stat = ws.QueryServiceStatus(self.handle)
				if self.stat[1]==ws.SERVICE_STOP_PENDING:
					self.fstate = "STOPPING"; break
				else:
					timeout=to(timeout)
					if timeout == "TO":
						return "TIMEDOUT"; break					  
		elif self.fstatus == "RUNNING":
			while 1:
				self.stat = ws.QueryServiceStatus(self.handle)
				if self.stat[1]==ws.SERVICE_RUNNING:
					self.fstate = "RUNNING"; break
				else:
					timeout=to(timeout)
					if timeout == "TO":
						return "TIMEDOUT"; break					   
		elif self.fstatus == "STARTING":
			while 1:
				self.stat = ws.QueryServiceStatus(self.handle)
				if self.stat[1]==ws.SERVICE_START_PENDING:
					self.fstate = "STARTING"; break
				else:
					timeout=to(timeout)
					if timeout == "TO":
						return "TIMEDOUT"; break
		
	def infotype(self):
		self.stat = ws.QueryServiceStatus(self.handle)
		if self.stat[0] & ws.SERVICE_WIN32_OWN_PROCESS:
			print("The", self.lserv, "service runs in its own process.")
		if self.stat[0] & ws.SERVICE_WIN32_SHARE_PROCESS:
			print("The", self.lserv, "service shares a process with other services.")
		if self.stat[0] & ws.SERVICE_INTERACTIVE_PROCESS:
			print("The", self.lserv, "service can interact with the desktop.")
		
	def infoctrl(self):
		self.stat = ws.QueryServiceStatus(self.handle)
		if self.stat[2] & ws.SERVICE_ACCEPT_PAUSE_CONTINUE:
			print("The", self.lserv, "service can be paused.")
		if self.stat[2] & ws.SERVICE_ACCEPT_STOP:
			print("The", self.lserv, "service can be stopped.")
		if self.stat[2] & ws.SERVICE_ACCEPT_SHUTDOWN:
			print("The", self.lserv, "service can be shutdown.")	

	def infostartup(self):
		self.isuphandle = wa.RegOpenKeyEx(wc.HKEY_LOCAL_MACHINE, self.sccss + self.sserv, 0, wc.KEY_READ)
		self.isuptype = wa.RegQueryValueEx(self.isuphandle, "Start")[0]
		wa.RegCloseKey(self.isuphandle)
		if self.isuptype == 0:
			return "boot"
		elif self.isuptype == 1:
			return "system"
		elif self.isuptype == 2:
			return "automatic"
		elif self.isuptype == 3:
			return "manual"
		elif self.isuptype == 4:
			return "disabled"
		 
	def setstartup(self, startuptype):
		self.startuptype = startuptype.lower()
		if self.startuptype == "boot":
			self.suptype = 0
		elif self.startuptype == "system":
			self.suptype = 1
		elif self.startuptype == "automatic":
			self.suptype = 2
		elif self.startuptype == "manual":
			self.suptype = 3
		elif self.startuptype == "disabled":
			self.suptype = 4
		self.snc = ws.SERVICE_NO_CHANGE
		ws.ChangeServiceConfig(self.handle, self.snc, self.suptype, \
		self.snc, None, None, 0, None, None, None, self.lserv) 
		
	def getname(self):
		self.snames=ws.EnumServicesStatus(self.scmhandle)
		for i in self.snames:
			if i[0].lower() == self.userv.lower():
				return i[0], i[1]; break
			if i[1].lower() == self.userv.lower():
				return i[0], i[1]; break				
		print("Error: The", self.userv, "service doesn't seem to exist.")
		return None, None

		
if __name__ == "__main__":
	import sys
	
	try:
		ipaddr = sys.argv [1]
	except IndexError:
		print("IP Address is not provided")
		sys.exit (1)

	
			
