import urllib.request, urllib.parse, urllib.error
import re
import time
from ...client.http import ClientCookie
from ...lib import timeoutsocket, confparse
from ...lib import logger as loggerfactory
import tempfile
import os
import random
from ...lib import pathtool
from . import __init__
import math

n, p = pathtool.modpath (__init__)
PROXYURLS = "proxysite.dat"

rx_ip = r"[^0-9]([0-9]{2,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})"
rx_dns = r"[^a-z0-9]([0-9a-z][-a-z0-9_]{2,30}\.[a-z0-9_]{2,30}\.[a-z0-9_.]*?)"
rx_port = r"([0-9]{2,5})"

RX_PROXY = [
		re.compile ("%s:%s" % (rx_ip, rx_port), re.I),
		re.compile ("%s.+?:%s" % (rx_ip, rx_port)),
		re.compile ("%s</td>\s*?<td.*?>%s</td>" % (rx_ip, rx_port), re.M),	
		re.compile ("%s\s+port\s+%s</" % (rx_ip, rx_port)),	
		re.compile ("%s:%s" % (rx_dns, rx_port), re.I),
		re.compile ("%s</td>\s*?<td.*?>%s</td>" % (rx_dns, rx_port), re.I|re.M),
		re.compile ("%s\s+port\s+%s</" % (rx_dns, rx_port)),		
		re.compile ("%s.+?>\s*%s" % (rx_ip, rx_port), re.I|re.S),
]

def unhide_text (data):
	t=''
	s = urllib.parse.unquote (data)
	x = int (round(math.sqrt(49)))
	for c in s: 		
 		t += chr (ord(c)^x)
 	t = t.replace ("#", " ").replace ("!", " ").replace ("|", " ").replace ("-", "")
 	return t

def unhide_text2 (data):
	t=''
	s = urllib.parse.unquote (data)
	for c in s: 		
 		t += chr (ord(c)^4) 	
 	return t
 	

class ProxyFinder:
	def __init__ (self, logger = None):
		self.logger = logger
		self.failover = 1
		self.fn = os.path.join (tempfile.gettempdir (), "__proxy.dat")
		if not self.logger:
			self.logger = loggerfactory.screen_logger ()
		self.proxies = {}
		self.hits = 0
		self.hold = False
		self.cookies = ClientCookie.CookieJar()
		self.opener = ClientCookie.build_opener(ClientCookie.HTTPCookieProcessor(self.cookies))
		self.goods = {}
	
	def set_hold (self, flag):
		self.hold = flag
		
	def set_preserve_min_proxy (self, num):
		self.preserve = num
		
	def set_failover (self, num):
		self.failover = num
			
	def find (self, data):
		for rx in RX_PROXY:
			proxies = rx.findall (data)
			count = 0
			for server, port in proxies:
				try: port = int (port)
				except: continue				
				count += 1
				self.proxies [(server, port)] = 0
			if count: break
			
		self.logger ("[info] %d proxies found" % len (self.proxies))
		return count
	
	def find_various (self, data):
		self.find (data)
		self.find (urllib.parse.unquote (data))
		self.find (unhide_text2 (data))
		self.find (unhide_text (data))		
	
	rx_evalcode = re.compile ("::(.+?)::")	
	def proceed (self):
		timeoutsocket.setDefaultSocketTimeout (60)
		cf = confparse.ConfParse (PROXYURLS)
				
		proxypages = cf.getopt ("urls")
		random.shuffle (proxypages)
		for page in cf.getopt ("verify") + proxypages:
			for code in self.rx_evalcode.findall (page):
				res = eval (code)
				page = page.replace ("::"+code+"::", res)
				
			try:
				self.logger ("retrieve %s" % page)
				res = self.opener.open(page)
				data = res.read ()				
				self.find_various (data)
			except:
				self.logger.trace ("proxyfinder")
			else:
				time.sleep (3.0)

	def save (self):
		f = open (self.fn, "w")
		proxies = list(self.proxies.keys ())		
		for proxy in proxies:
			f.write ("%s:%s\n" % proxy)
		f.close ()
		if self.logger: self.logger ("[info] %d proxies saved" % len (self.proxies))
	
	def __len__ (self):
		return len (self.proxies)
		
	def load (self, max = 0):
		if len (self.goods) >= 20:
			for each in self.goods:
				self.proxies [each] = 0
			if self.logger: self.logger ("[info] %d good proxies loaded" % len (self.proxies))
			self.goods = {}
			return	
		
		try:
			f = open (self.fn)
		except (OSError, IOError):
			self.proceed ()
			self.save ()
			f = open (self.fn)			
		else:
			for line in f:
				h, p = line.strip ().split (":", 1)
				self.proxies [(h, int (p))] = 0
				if max and len (self.proxies) > max: break
			f.close ()
		
		if self.logger: self.logger ("[info] %d proxies loaded" % len (self.proxies))

	def get (self, trying = 1):
		if trying > 10: return None
		if self.proxies:
			l = list(self.proxies.keys ())
			proxy = random.choice (l)
			try: del self.proxies [proxy]
			except KeyError: pass
			return proxy
		
		elif self.hold:
			return None
				
		else:
			self.load ()
			trying += 1
			return self.get (trying)
	
	def report_fail (self, proxy):
		self.put (proxy, 1)
		
	def report_good (self, proxy):
		self.goods [proxy] = None
		self.put (proxy, 0)
			
	def put (self, proxy, error_level = 0):
		if not proxy: return
			
		if error_level == 0:
			self.proxies [proxy] = 0
			return
		
		args = proxy + (len (self.proxies),)
		if self.logger: self.logger ("[info] proxy removed... %s:%s, remain %d proxies" % args)
		try: del self.proxies [proxy]					
		except KeyError: pass			
		

class Proxy (ProxyFinder):
	pass
	

class QueueProxy (ProxyFinder):
	def __init__ (self, logger = None):
		ProxyFinder.__init__ (self, logger)
		self.proxies = []
		
	def report_good (self, proxy):
		pass
	
		
if __name__ == "__main__":
	f = ProxyFinder ()
	f.proceed ()
	f.save ()
