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
DEFAULT_PROXYSITES = os.path.join (os.path.split (p) [0], "proxysite.dat")

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

class ProxyCollector:
	def __init__ (self, logger = None):
		self.logger = logger
		self.proxies = {}
		self.cookies = ClientCookie.CookieJar()
		self.opener = ClientCookie.build_opener(ClientCookie.HTTPCookieProcessor(self.cookies))
		
	def save (self, output = None):
		if output is None:
			output = os.path.join (os.environ ["systemroot"], "sharedproxy.dat")
		proxies = list(self.proxies.keys ())
		f = open (output, "w")		
		for proxy in proxies:
			f.write ("%s:%s\n" % proxy)
		f.close ()
		if self.logger: self.logger ("[info] %d proxies saved" % len (self.proxies))
			
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
			
		if self.logger: self.logger ("[info] %d proxies found" % len (self.proxies))
		return count
	
	def find_various (self, data):
		self.find (data)
		self.find (urllib.parse.unquote (data))
		self.find (unhide_text2 (data))
		self.find (unhide_text (data))		
	
	rx_evalcode = re.compile ("::(.+?)::")	
	def collect (self, src = None):
		if src is None:
			src = DEFAULT_PROXYSITES
			
		timeoutsocket.setDefaultSocketTimeout (60)
		cf = confparse.ConfParse (src)
		
		proxypages = cf.getopt ("urls")
		random.shuffle (proxypages)
		for page in cf.getopt ("verify") + proxypages:
			for code in self.rx_evalcode.findall (page):
				res = eval (code)
				page = page.replace ("::"+code+"::", res)
				
			try:
				if self.logger: self.logger ("[info] retrieve %s" % page)
				res = self.opener.open(page)
				data = res.read ()				
				self.find_various (data)
			except:
				if self.logger: 
					self.logger.trace ("proxyfinder")
				else:
					raise	
			else:
				time.sleep (3.0)

		
if __name__ == "__main__":
	f = ProxyCollector ()
	f.collect ()
	f.save ()
	
