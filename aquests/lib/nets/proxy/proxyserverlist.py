import urllib.request, urllib.parse, urllib.error
import re
import time
from ...lib import logger as loggerfactory
import os
import random
from ...lib import pathtool
import math

class ProxyServerList:
	def __init__ (self, logger = None):
		self.logger = logger
		self.proxies = []
		self.proxy_reused = 0
	
	def __len__ (self):
		return len (self.proxies)
			
	def pop (self):
		if not self.proxies:
			self.load ()		
		proxy = self.proxies.pop (0)
		if self.logger: self.logger ("[info] %d proxies was remained" % len (self.proxies))
		return proxy		
	
	def getr (self):
		if not self.proxies:
			self.load ()		
		proxy = random.choice (self.proxies)
		return proxy		
	
	def putr (self, proxy):
		index = random.randrange (len (self.proxies))
		self.insert (index, proxy)
	
	get = getr
	put = putr
	
	def append (self, proxy):
		self.proxies.append (proxy)
	
	def insert (self,index, proxy):
		self.proxies.insert (index, proxy)	
		
	def load (self, path = None):
		if path is None:
			path = os.path.join (os.environ ["systemroot"], "sharedproxy.dat")
		f = open (path)
		for line in f:
			h, p = line.strip ().split (":", 1)
			self.proxies.append ((h, int (p)))
		f.close ()
		random.shuffle (self.proxies)
		if self.logger: self.logger ("[info] %d proxies loaded" % len (self.proxies))
	
	def save (self, path):
		f = open (path, "w")
		for proxy in self.proxies:
			f.write ("%s:%s\n" % proxy)
		f.close ()
		
	def duplicate (self, output, path = None):
		if path is None:
			path = os.path.join (os.environ ["systemroot"], "sharedproxy.dat")
		self.proxy_reused += 1
		f = open (path)
		data = f.read ()
		f.close ()
		f = open (output, "w")
		f.write (data)
		f.close ()	
	
		
if __name__ == "__main__":
	f = ProxyServerList ()
	f.load ()
