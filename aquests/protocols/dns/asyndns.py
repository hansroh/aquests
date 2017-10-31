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
from ... import lifetime

defaults = Base.defaults
Base.DiscoverNameServers ()

class UDPClient (asynchat.async_chat):
	protocol = "udp"
	zombie_timeout = 1200
	ac_in_buffer_size = 512
	
	def __init__ (self, addr, logger):
		self.addr = addr
		self.logger = logger				
		self.event_time = time.time ()
		self.creation_time = time.time ()		
		self.closed = False
		self._timeouted = False
		self.requests = {}
		self.callback = None
		asynchat.async_chat.__init__ (self)
							
	def query (self, request, args, callback):	
		if self.callback is None:
			self.callback = callback
		self.event_time = time.time ()		
		self.header = None
		
		self.requests [request [:2]] = [args, time.time ()]
		qname = args ["name"].decode ("utf8")
		args ['addr'] = self.addr
		self.push (request)
			
		if not self.connected:
			self.set_terminator (None)
			self.create_socket (socket.AF_INET, socket.SOCK_DGRAM)
			self._connect ()
				
	def _connect (self):		
		try:
			self.connect (self.addr)
		except:
			self.handle_error ()
					
	def trace (self):
		self.logger.trace ()
	
	def log_info (self, line, level = 'info'):
		self.log ("[%s] %s" % (level, line))
	          
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
		
	def collect_incoming_data (self, data, id = None):
		try:
			args, starttime = self.requests.pop (id or data [:2])				
		except KeyError:
			# alerady timeouted
			pass
		else:	
			self.callback (args, data, id is not None)
			
	def handle_close (self):	
		for args, starttime in self.requests.values ():
			self.callback (args, b'', True)
		self.close ()

		
class TCPClient (UDPClient):
	protocol = "tcp"
	zombie_timeout = 10
	ac_in_buffer_size = 65536
	
	def __init__ (self, addr, logger):		
		UDPClient.__init__ (self, addr, logger)
		self.callback = None
		self.args = None
		self.request = None
		self.header = None
		self.reply = b''
							
	def query (self, request, args, callback):	
		self.event_time = time.time ()
		self.reply = b""
		self.header = None
		self.request = request
		self.args = args
		self.callback = callback
		
		args ['addr'] = self.addr		
		self.push (Lib.pack16bit(len(request)) + request)
		if not self.connected:
			self.set_terminator (2)
			self.create_socket (socket.AF_INET, socket.SOCK_STREAM)				
			self._connect ()
		
	def collect_incoming_data (self, data):		
		self.reply += data
			
	def found_terminator (self):	
		if self.header:
			self.callback (self.args, self.header + self.reply, self._timeouted)
			self.close ()
			
		else:
			self.header, self.reply = self.reply, b""
			count = Lib.unpack16bit(self.header)
			self.set_terminator (count)			
		
	def handle_close (self):	
		self.callback (self.args, b'', self._timeouted)				
		self.close ()

		
class RequestHandler:
	def __init__(self, lock, logger):
		self.lock = lock
		self.logger = logger
		self.id = 0
	
	def get_id (self):
		with self.lock:
			self.id += 1
			if self.id == 32768:
				self.id = 1	
			return self.id
		
	def argparse (self, name, args):
		args['name'] = name
		if 'errors' not in args:
			args ['errors'] = []
			
		for i in list(defaults.keys()):
			if i not in args:
				args[i]=defaults[i]
		return args
		
	def handle_request (self, name, **args):
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
		m.addHeader(self.get_id (),
			  0, opcode, 0, 0, rd, 0, 0, 0,
			  1, 0, 0, 0)
		
		m.addQuestion (qname, qtype, Class.IN)
		request = m.getbuf ()
		
		conn = getattr (pool, args ['protocol']) (args.get ('addr'))
		conn.query (request, args, self.process_reply)
		
	def process_reply (self, args, data, timeouted):		
		global pool
		
		err = None
		answers = []
		qname = args ['name'].decode ('utf8')
		
		if timeouted:
			err = 'timeout'			
		else:	
			try:
				if not data:
					err = "no-reply"					
				else:	
					if args ["protocol"] == "tcp":
						header = data [:2]
						if len (header) < 2:
							err = 'EOF-invalid-header' % qname
						count = Lib.unpack16bit(header)
						reply = data [2: 2 + count]
						if len (reply) != count:
							err = "incomplete-reply"					
					else:
						reply = data
					
			except:
				self.logger.trace ()
				err = 'exception'	
			
			if not err:
				try:	
					u = Lib.Munpacker(reply)
					r = Lib.DnsResult(u, args)
					r.args = args
					if r.header ['tc']:
						err = 'truncate'
						args ['protocol'] = 'tcp'
						self.logger ('%s, trucated switch to TCP' % qname, 'warn')
						
					else:
						if r.header ['status'] != 'NOERROR':
							self.logger ('%s, status %s' % (qname, r.header ['status']), 'warn')
						answers = r.answers
						
				except:
					self.logger.trace ()
		
		if err:
			if len (args ['errors']) < 2:
				args ['errors'].append (err)
				# switch protocol
				args ['protocol'] = args ['protocol'] == "tcp" and "udp" or "tcp"
				query (**args)
				return
				
			self.logger ('%s, DNS %s errors' % (qname, args ['errors']), 'warn')
		
		callback = args.get ("callback", None)
		if callback:
			if type (callback) != type ([]):
				callback = [callback]
			for cb in callback:				
				cb (answers)


class Pool:
	query_timeout = 1
	
	def __init__ (self, servers, logger):
		self.logger = logger
		self.lock = threading.Lock ()
		self.handler = RequestHandler (self.lock, self.logger)
		self.servers = [(x, 53) for x in servers]
		self.udps = [UDPClient (x, self.logger) for x in self.servers]						
		self.queue = []
		
	def add (self, item):
		with self.lock:
			self.queue.append (item)
	
	def has_job (self):
		with self.lock:
			for client in self.udps:
				if len (client.requests):
					return 1
		return 0
	
	def jobs (self):
		t = []		
		with self.lock:
			for client in self.udps:
				t.extend (list (client.requests.keys ()))
		return t	
			
	def pop_all (self):
		# DNS query maybe not allowed delay between request and send
		# maybe they just drop response packet for delaying
		with self.lock:
			queue, self.queue = self.queue [:], []
				
		count = len (queue)
		while queue:
			name, args = queue.pop (0)
			self.handler.handle_request (name, **args)
	
		if (not count and not self.has_job ()):
			return
		
		map = {}
		with self.lock:
			for client in self.udps:
				map [client._fileno] = client
		fds = list (map.keys ())
		
		# maybe 2 is enough
		safeguard = count * 2
		while self.has_job () and safeguard:
			safeguard -= 1
			asyncore.loop (0.1, map, count = 1)
			if safeguard % 5 == 0:
				self.maintern (time.time ())		
		self.maintern (time.time ())
							
		for fd in fds:
			if fd not in map:
				# resync 
				try: del asyncore.socket_map [fd]
				except KeyError: pass	
		
	def maintern (self, now):
		for client in self.udps:
			for id, (args, starttime) in list (client.requests.items ()):
				if now - starttime > self.query_timeout:
					client.collect_incoming_data (b'', id)
			
	def tcp (self, exclude = None):
		while 1:
			addr = random.choice (self.servers)
			if addr != exclude:
				return TCPClient (addr, self.logger)
		
	def udp (self, exclude = None):
		while 1:
			conn = random.choice (self.udps)
			if conn.addr != exclude:
				return conn


def query (name, **args):
	global pool
	
	if not lifetime.EXHAUST_DNS:
		return pool.handler.handle_request (name, **args)
	pool.add ((name, args))

	
def pop_all ():	
	global pool
	pool.pop_all ()
	
		
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
		self.handler.handle_request (item, protocol = "udp", callback = test_callback, qtype = "a")

def _print (ans):
	if ans:
		print (ans[0]['name'], ans[-1]['data'])
	else:
		print ("FAILED")
		
		
if __name__	== "__main__":
	from aquests.lib import logger
	import pprint
	
	create_pool (PUBLIC_DNS_SERVERS, logger.screen_logger ())
	for i in range (4):
		#query ("www.microsoft.com", protocol = "udp", callback = _print, qtype="a")
		#query ("www.cnn.com", protocol = "udp", callback = _print, qtype="a")
		#query ("www.gitlab.com", protocol = "udp", callback = _print, qtype="a")
		#query ("www.alexa.com", protocol = "udp", callback = _print, qtype="a")
		#query ("www.yahoo.com", protocol = "udp", callback = _print, qtype="a")
		#query ("www.github.com", protocol = "udp", callback = _print, qtype="a")
		#query ("www.google.com", protocol = "udp", callback = _print, qtype="a")
		#query ("www.amazon.com", protocol = "udp", callback = _print, qtype="a")
		#query ("www.almec.com", protocol = "udp", callback = _print, qtype="a")
		#query ("www.alamobeauty.com", protocol = "udp", callback = _print, qtype="a")
		#query ("www.alphaworld.com", protocol = "udp", callback = _print, qtype="a")
		#query ("www.allrightsales.com", protocol = "udp", callback = _print, qtype="a")
		query ("www.glasteel.com", protocol = "udp", callback = _print, qtype="a")
	
	pop_all ()
	print ('------------------------')	
	while 1:
		pop_all ()
		asyncore.loop (timeout = 1, count = 1)
		print ('UNFINISHED', pool.jobs ())
		
	
	