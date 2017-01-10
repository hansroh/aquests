from . import ipsec

class DenialOfService (ipsec.IPSEC):
	def __init__ (self, policy, name):
		ipsec.IPSEC.__init__ (self)
		self.policy = policy
		self.name = name
		self.createNewPolicy (self.policy, self.name)
		
	def createNewPolicy (self, policy, name):
		if not self.hasPolicy (policy):
			self.addPolicy (policy)		
		try:
			had = self.hasIP ("1.1.1.1")
		except Exception as why:
			if str (why).find ("05049") != -1 or str (why).find ("05067") != -1:
				had = False
			else:
				raise
					
		if not had:
			self.addFilterAction ("%s-DENY" % name, "block")
			self.addFilterList ("%s-ATTACKERS" % name)
			self.addFilter ("%s-ATTACKERS" % name)		
			self.addRule ("%s-RULE" % name, policy, "%s-ATTACKERS" % name, "%s-DENY" % name)
	
	def addIP (self, srcAddr):
		self.addFilter ("%s-ATTACKERS" % self.name, srcAddr, "Me", "TCP", "0", "80")
	
	def deleteIP (self, srcAddr):
		self.deleteFilter ("%s-ATTACKERS" % self.name, srcAddr, "Me", "TCP", "0", "80")
	
	def hasIP (self, srcAddr):
		return self.hasFilter ("%s-ATTACKERS" % self.name, srcAddr, "Me", "TCP", "0", "80")
	
	def getIP (self):
		return [x [0] for x in self.getFilters ("%s-ATTACKERS" % self.name)]


if __name__ == "__main__":
	f = DenialOfService ("Lufex IP Policy", "DOS")
	f.addIP ("121.138.194.106")
	print(f.hasIP ("121.138.194.106"))
	print(f.getIP ())
	f.deleteIP ("121.138.194.106")
	print(f.getIP ())
	