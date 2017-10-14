"""
2008 added for asynchronous DNS query by Hans Roh
"""

import asynchat, asyncore
import socket
import time
import types
import random
import types
from .pydns import Base, Type, Class, Lib, Opcode
import random
import threading
from ...lib.athreads.socket_map import thread_safe_socket_map

defaults = Base.defaults
Base.DiscoverNameServers ()

socket_map = thread_safe_socket_map ()

class async_dns (asynchat.async_chat):
	zombie_timeout = 2
	
	def __init__ (self, addr, protocol, logger):
		self.addr = addr
		self.logger = logger
		self.protocol = protocol
		if protocol == 'udp':
			self.zombie_timeout = 1200
		self.active = False
		self.creation_time = time.time ()		
		self._timeouted = 0
		self.closed = False
		self.callbacks = {}
		asynchat.async_chat.__init__ (self, None, socket_map)
	
	def __repr__ (self):	
		return "<async_dns: connected %s:%d with %s>" % (self.addr [0], self.addr [1], self.protocol)
							
	def query (self, request, args, callback):	
		self.event_time = time.time ()
		self.reply = b""
		self.header = None
		
		self.callbacks [request [:2]] = (callback, time.time ())
		self.args = args				
		self.qname = self.args ["name"].decode ("utf8")
		args ['addr'] = self.addr
		
		if not self.connected:
			if args ["protocol"] == "tcp":
				self.set_terminator (2)
				self.connect_tcp ()
			else:
				self.set_terminator (None)
				self.connect_udp ()
		
		if self.args ["protocol"] == "tcp":
			self.push (Lib.pack16bit(len(request)) + request)
		else:	
			self.push (request)
			
	def connect_udp (self):				
		self.create_socket (socket.AF_INET, socket.SOCK_DGRAM)
		self._connect ()
	
	def connect_tcp (self):
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)				
		self._connect ()
	
	def _connect (self):		
		try:
			self.connect (self.addr)
		except:
			self.handle_error ()
					
	def trace (self):
		self.logger.trace (self.qname)
	
	def log_info (self, line, level = 'info'):
		self.log ("[%s:%s] %s" % (level, self.qname, line))
	          
	def log (self, line):
		self.logger (line)
		
	def handle_error (self):
		self.trace ()
		self.close ()
	
	def handle_timeout (self):
		self._timeouted = True
		self.handle_close ()
					
	def handle_connect (self):	
		self.event_time = time.time ()		
		
	def handle_expt (self):
		self.handle_close ()
	
	def collect_incoming_data (self, data):		
		if self.args ["protocol"] == "udp":
			try:
				callback, starttime = self.callbacks.pop (data [:2])
			except KeyError:
				pass
			else:							
				callback (self.args, data, 0)			
		else:
			self.reply += data	
			
	def found_terminator (self):
		if self.args ["protocol"] == "tcp":
			if self.header:
				try:
					callback, starttime = self.callbacks.pop (self.reply [:2])
				except KeyError:
					pass		
				else:
					callback (self.args, self.header + self.reply, 0)				
				self.close ()
				
			else:
				self.header, self.reply = self.reply, b""
				count = Lib.unpack16bit(self.header)
				self.set_terminator (count)			
			
	def handle_close (self):	
		for callback, starttime in self.callbacks.values ():
			callback (self.args, b'', self._timeouted)				
		self.close ()		
		
		
class Request:
	id = 0
	def __init__(self, name, **args):
		self.req (name, **args)				
		
	def argparse (self, name, args):
		args['name'] = name
		for i in list(defaults.keys()):
			if i not in args:
				args[i]=defaults[i]
		return args
		
	def req (self, name, **args):
		global pool
		
		if isinstance (name, str):
			name = name.encode ("utf8")
		args = self.argparse (name, args)
		
		protocol = args ['protocol']
		opcode = args ['opcode']
		rd = args ['rd']
		
		if type(args['qtype']) in (bytes, str):
			try:
				qtype = getattr (Type, args ['qtype'].upper ())
			except AttributeError:
				raise Base.DNSError('%s unknown query type' % name)
				
		else:
			qtype = args ['qtype']
			
		qname = args ['name']		
		m = Lib.Mpacker()
		Request.id += 1
		if Request.id == 32768:
			Request.id = 1
		m.addHeader(Request.id,
			  0, opcode, 0, 0, rd, 0, 0, 0,
			  1, 0, 0, 0)
		
		m.addQuestion (qname, qtype, Class.IN)
		request = m.getbuf ()
		
		args ['retry'] += 1
		conn = getattr (pool, args ['protocol']) ()
		conn.query (request, args, self.processReply)
		
	def processReply (self, args, data, timeouted):		
		global pool
		
		err = None
		answers = []
		qname = args ['name'].decode ('utf8')
		
		if timeouted:
			err = 'timeout'
			
		else:	
			try:
				if not data:
					err = "no reply"
					
				else:	
					if args ["protocol"] == "tcp":
						header = data [:2]
						if len (header) < 2:
							err = '%s, EOF' % qname
						count = Lib.unpack16bit(header)
						reply = data [2: 2 + count]
						if len (reply) != count:
							err = "incomplete reply"					
					else:
						reply = data
					
			except:
				pool.logger.trace ()
				err = 'exception'	
			
			if not err:
				try:	
					u = Lib.Munpacker(reply)
					r = Lib.DnsResult(u, args)
					r.args = args
					if r.header ['tc']:
						err = 'truncate'
						args ['protocol'] = 'tcp'
						pool.logger ('%s, trucated switch to TCP' % qname, 'warn')
						
					else:
						if r.header ['status'] != 'NOERROR':
							pool.logger ('%s, status %s' % (qname, r.header ['status']), 'warn')
						answers = r.answers
						
				except:
					pool.logger.trace ()
		
		if err:
			if args ['retry'] < 3:					
				self.req (**args)					
				return
			pool.logger ('%s, DNS %s error' % (qname, err), 'warn')
		
		callback = args.get ("callback", None)
		if callback:
			if type (callback) != type ([]):
				callback = [callback]
			for cb in callback:				
				cb (answers)


class Pool:
	def __init__ (self, servers, logger):
		#self.servers = [(x, 53) for x in servers]
		self.logger = logger
		self.udps = [async_dns ((x, 53), 'udp', self.logger) for x in servers]
		self.servers = [(x, 53) for x in servers]
	
	def __len__ (self):	
		for each in list (socket_map.values ()):
			if each.protocol == 'tcp':
				return 1				
			elif each.callbacks:
				return 1
		return 0
	
	def maintern (self, now):
		for each in socket_map.values ():
			if each.protocol == 'udp':
				for id, (callback, starttime) in list (each.callbacks.items ()):
					if now - starttime > 1:						
						del each.callbacks [id]
						callback (each.args, b'', True)
						
			else:
				if now - each.event_time > 1:				
					each.handle_timeout ()
				
	def tcp (self):
		addr = random.choice (self.servers)		
		return async_dns (addr, 'tcp', self.logger)
		
	def udp (self):
		return random.choice (self.udps)
			
		
PUBLIC_DNS_SERVERS = [
	'8.8.8.8', 
	'8.8.4.4'
]
pool = None			
def create_pool (dns_servers, logger):
	global pool, PUBLIC_DNS_SERVERS
	if not dns_servers:
		dns_servers = PUBLIC_DNS_SERVERS
	pool = Pool (dns_servers, logger)

testset = [
	"www.alexa.com",
	"www.yahoo.com",
	"www.microsoft.com",
	"www.amazon.com",
	"www.cnn.com",
	"www.gitlab.com",
	"www.github.com",
	"hub.docker.com",
]

def test_callback (ans):
	global testset, pool
	
	pprint.pprint (ans)	
	if testset:
		item = testset.pop ()		
		Request (item, protocol = "udp", callback = test_callback, qtype = "a")		

	
if __name__	== "__main__":
	from aquests.lib import logger
	import pprint
	
	create_pool (PUBLIC_DNS_SERVERS, logger.screen_logger ())
	#Request ("www.microsoft.com", protocol = "tcp", callback = print, qtype="a")
	#Request ("www.cnn.com", protocol = "udp", callback = print, qtype="a")
	#Request ("www.gitlab.com", protocol = "udp", callback = print, qtype="a")
	#Request ("www.alexa.com", protocol = "udp", callback = print, qtype="a")
	Request ("www.yahoo.com", protocol = "udp", callback = print, qtype="a")
	Request ("www.github.com", protocol = "udp", callback = print, qtype="a")
	Request ("www.google.com", protocol = "udp", callback = print, qtype="a")
	Request ("www.amazon.com", protocol = "udp", callback = print, qtype="a")
	print (socket_map)
	for i in range (10):
		asyncore.loop (timeout = 0.1, map = socket_map, count = 1)
		print (len (pool), socket_map)
		
	
	