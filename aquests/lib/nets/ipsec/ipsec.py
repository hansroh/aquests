import os

class IPSECError (Exception): pass

def execute (cmd):
	class Result: pass
	
	r = Result ()
	f = os.popen (cmd)
	r.data = f.read ()
	r.exitcode = f.close ()
	if r.exitcode is not None or r.data.find ("ERR") != -1:
		raise IPSECError("[%s] %s" % (r.exitcode, r.data))
	return r

	
class IPSEC:
	def __init__ (self):
		self.collect_existing_policies ()
		self.dirty_filter = True
		self.filters = []
	
	def collect_existing_policies (self):
		self.allpoicies = {}
		try:
			r = execute ('netsh ipsec static show policy all')
		except IPSECError as why:	
			if why.errno.find ("[05072]") != -1 or why.errno.find ("No Policies") != -1: # no policies
				return
												
		for each in r.data.split ("\n\n") [:-2]:
			for line in each.strip ().split ("\n"):
				k, v = [x.strip () for x in line.split (":", 1)]
				if k == "Policy Name":
					curkey = v
					self.allpoicies [curkey] = {}
				self.allpoicies [curkey][k] = v
					
	def hasPolicy (self, name):
		return name in self.allpoicies
	
	def importPolicy (self, file):
		r = execute ('netsh ipsec static importpolicy file="%s"' % file)		
	
	def exportPolicy (self, file):
		r = execute ('netsh ipsec static exportpolicy file="%s"' % file)
				
	def addPolicy (self, name, assign = True, pollinginterval = 180, description = "N/A"):
		r = execute ('netsh ipsec static add policy name="%s" assign=%s pollinginterval=%d description="%s"' % (name, assign and "yes" or "no", pollinginterval, description))
		self.collect_existing_policies ()
	
	def setPolicy (self, name, newname, assign = True, pollinginterval = 180, description = "N/A"):
		r = execute ('netsh ipsec static set policy name="%s" newname="%s" assign=%s pollinginterval=%d description="%s"' % (name, newname, assign and "yes" or "no", pollinginterval, description))
		self.collect_existing_policies ()
			
	def deletePolicy (self, name):
		r = execute ('netsh ipsec static delete policy name="%s"' % (name,))
		self.collect_existing_policies ()
		
	def getPolicy (self, name):
		return self.allpoicies.get (name, None)
		
	def addFilterAction (self, name, action, description = "N/A"):
		if action not in ("permit", "block", "negotiate"):
			raise ValueError("Must be one of permit, block, negotiate")
		try: 
			r = execute ('netsh ipsec static add filteraction name="%s" action=%s description="%s"' % (name, action, description))
		except Exception as why:
			if str (why).find ("05014") != -1:
				pass
			else:
				raise
	
	def setFilterAction (self, name, newname, action, description = "N/A"):
		if action not in ("permit", "block", "negotiate"):
			raise ValueError("Must be one of permit, block, negotiate")
		r = execute ('netsh ipsec static add filteraction name="%s" newname="%s" action=%s description="%s"' % (name, newname, action, description))
		
	def deleteFilterAction (self, name):
		r = execute ('netsh ipsec static delete filteraction name="%s"' % (name,))
	
	def hasFilterAction (self, name):
		try:
			r = execute ('netsh ipsec static show filteraction name="%s"' % (name,))
		except IPSECError:
			return False
		return True		
		
	def addFilterList (self, name, description = "N/A"):
		try:	
			r = execute ('netsh ipsec static add filterlist name="%s" description="%s"' % (name, description))		
		except Exception as why:
			if str (why).find ("05010") != -1:
				pass
			else:
				raise
	
	def hasFilterList (self, name, description = "N/A"):
		try:
			r = execute ('netsh ipsec static show filterlist name="%s"' % (name,))
		except IPSECError:
			return False
		return True
		
	def setFilterList (self, name, newname, description = "N/A"):
		r = execute ('netsh ipsec static add filterlist name="%s" newname="%s" description="%s"' % (name, newname, description))
		
	def deleteFilterList (self, name):
		r = execute ('netsh ipsec static delete filterlist name="%s"' % name)
	
	def getFilters (self, flName):
		if not self.dirty_filter: 
			return self.filters
			
		r = execute ('netsh ipsec static show filterlist name="%s" level=verbose' % flName)
		s = r.data.find ("---------")
		if s == -1:
			return False
		
		data = r.data [s + 10:]
		filters = []
		
		srcMask = "255.255.255.255"
		dstMask = "255.255.255.255"
		for each in data.split ("\n\n") [:-1]:
			for line in each.strip ().split ("\n"):				
				k, v = [x.strip () for x in line.split (":", 1)]				
				if k == "Source IP Address":
					if v == "<My IP Address>": v = "Me"
					srcAddr = v						
				elif k == "Source Mask":	
					srcMask = v
				elif k == "Destination IP Address":	
					if v == "<My IP Address>": v = "Me"
					dstAddr = v
				elif k == "Destination Mask":	
					dstMask = v
				elif k == "Protocol":	
					protocol = v					
				elif k == "Source Port":	
					if v == "ANY": v = "0"
					srcPort = v					
				elif k == "Destination Port":					
					if v == "ANY": v = "0"
					dstPort = v
			filters.append ((srcAddr, dstAddr, protocol, srcPort, dstPort, srcMask, dstMask))
		
		self.filters = filters
		self.dirty_filter = False
		return filters
			
	def hasFilter (self, flName, srcAddr = "1.1.1.1", dstAddr="Me", protocol="TCP", srcPort="0", dstPort="80", srcMask="255.255.255.255", dstMask="255.255.255.255"):
		for each in self.getFilters (flName):
			if each == (srcAddr, dstAddr, protocol, srcPort, dstPort, srcMask, dstMask):
				return True
		return False		
		
	def addFilter (self, flName, srcAddr = "1.1.1.1", dstAddr="Me", protocol="TCP", srcPort="0", dstPort="80", srcMask="255.255.255.255", dstMask="255.255.255.255", description = "N/A"):
		r = execute (
			'netsh ipsec static add filter filterlist="%s" srcaddr=%s srcmask=%s dstaddr=%s dstmask=%s protocol=%s srcport=%s dstport=%s description="%s"' % (
				flName, srcAddr, srcMask, dstAddr, dstMask, protocol, srcPort, dstPort, description
			)
		)
		self.dirty_filter = True
	
	def deleteFilter (self, flName, srcAddr = "1.1.1.1", dstAddr="Me", protocol="TCP", srcPort="0", dstPort="80", srcMask="255.255.255.255", dstMask="255.255.255.255"):
		r = execute (
			'netsh ipsec static delete filter filterlist="%s" srcaddr=%s srcmask=%s dstaddr=%s dstmask=%s protocol=%s srcport=%s dstport=%s' % (
				flName, srcAddr, srcMask, dstAddr, dstMask, protocol, srcPort, dstPort
			)
		)
		self.dirty_filter = True
	
	def addRule (self, name, policy, flName, faName, activate = True, description = "N/A"):
		r = execute ('netsh ipsec static add rule name="%s" policy="%s" filterlist="%s" filteraction="%s" activate=%s description="%s"' % (name, policy, flName, faName, activate and "yes" or "no", description))
	
	def setRule (self, name, newname, policy, flName, faName, activate = True, description = "N/A"):
		r = execute ('netsh ipsec static add rule name="%s" newname="%s" policy="%s" filterlist="%s" filteraction="%s" activate=%s description="%s"' % (name, newname, policy, flName, faName, activate and "yes" or "no", description))
		
	def deleteRule (self, name, policy):
		r = execute ('netsh ipsec static delete rule name="%s" policy="%s""' % (name, policy))	
	
	def hasRule (self, name, policy):
		try:
			r = execute ('netsh ipsec static show rule name="%s" policy="%s""' % (name, policy))
		except IPSECError:
			return False
		return True
		