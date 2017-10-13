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

defaults = Base.defaults
Base.DiscoverNameServers ()

socket_map = {}

class async_dns (asynchat.async_chat):
	zombie_timeout = 2
	
	def __init__ (self, addr, logger):
		self.addr = addr				
		self.logger = logger
		self.active = False
		self.creation_time = time.time ()		
		self._timeouted = 0
		self.event_time = time.time ()
		self.reply = b""
		self.header = None
		self.closed = False
		asynchat.async_chat.__init__ (self, None, socket_map)
		
	def query (self, request, args, callback):		
		self.callback = callback		
		self.request = request
		self.args = args				
		self.qname = self.args ["name"].decode ("utf8")
		args ['addr'] = self.addr
		
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
		self.reply += data
		if self.args ["protocol"] == "udp":
			self.callback (self.args, self.reply, self._timeouted)
			self.callback = None
			self.close ()
			
	def found_terminator (self):
		if self.args ["protocol"] == "tcp":
			if self.header:
				if self.callback:
					self.callback (self.args, self.header + self.reply, self._timeouted)
					self.callback = None
				self.close ()
				
			else:
				self.header, self.reply = self.reply, b""
				count = Lib.unpack16bit(self.header)
				self.set_terminator (count)			
			
	def handle_close (self):
		if self.callback:
			self.callback (self.args, b'', self._timeouted)
			self.callback = None
		self.close ()		
		
		
class Request:
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
		m.addHeader(0,
			  0, opcode, 0, 0, rd, 0, 0, 0,
			  1, 0, 0, 0)
		
		m.addQuestion (qname, qtype, Class.IN)
		request = m.getbuf ()
		
		args ['retry'] += 1
		conn = pool.get (args ['addr'])
		conn.query (request, args, self.processReply)
		
	def processReply (self, args, data, timeouted):		
		global pool
		
		err = None
		answers = []
		qname = args ['name'].decode ('utf8')
		if timeouted and self.retry < 3:
			err = 'timeout'
			
		else:	
			try:
				if not data:
					err = "no reply"
					
				else:	
					if args ["protocol"] == "tcp":
						header = data [:2]
						if len (header) < 2:
							raise Base.DNSError('%s, EOF' % qname)
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
						err = 'trucate'
						args ['protocol'] = 'tcp'
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
				raise Base.DNSError('%s, %s' % (qname, err))
			
		callback = args.get ("callback", None)		
		if callback:
			if type (callback) != type ([]):
				callback = [callback]
			for cb in callback:				
				cb (answers)


class Pool:
	def __init__ (self, servers, logger):
		self.servers = [(x, 53) for x in servers]
		self.logger = logger
		
	def get (self, exclude = None):
		if len (self.servers) > 1:			
			while 1:
				addr = random.choice (self.servers)
				if addr != exclude:
					break
		else:			
			addr = self.servers [0]
			
		return async_dns (addr, self.logger)
			
		
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
	r = Request ("www.advancedeyecenter.com", protocol = "udp", callback = test_callback, qtype="a")
	asyncore.loop (timeout = 0.1, map = socket_map)
	
	