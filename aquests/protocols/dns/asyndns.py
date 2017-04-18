"""
2008 added for asynchronous DNS query by Hans Roh
"""

import asyncore
import socket
import time
import types
import random
import types
from .pydns import Base, Type, Class, Lib, Opcode
import random

defaults = Base.defaults
Base.DiscoverNameServers ()

class async_dns (asyncore.dispatcher_with_send):
	zombie_timeout = 10
	
	def __init__ (self, servers, request, args, callback, logger, debug_level):
		self.servers = servers
		if not self.servers:
			raise OSError ("DNS Server Required")
		random.shuffle (self.servers)
		#self.servers = [("156.154.71.3", 513), ("156.154.71.9", 543)]
		self.addr = self.servers.pop (0)
		self.request = request
		self.callback = callback		
		self.args = args		
		self.logger = logger
		self.debug_level = debug_level
		self.qname = self.args ["name"].decode ("utf8")
		
		self.creation_time = time.time ()
		self.event_time = time.time ()
		self.ac_in_buffer = b""
		self.closed = False
		
		asyncore.dispatcher_with_send.__init__ (self)		
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)				
				
		try:
			self.connect (self.addr)
		except:
			self.handle_error ()
	
	def __repr__ (self):
		return "<async_dns: %s>" % self.qname
				
	def trace (self):
		self.logger.trace (self.qname)
	
	def log_info (self, line, level = 'info'):
		self.log ("[%s:%s] %s" % (level, self.qname, line))
	
	def log (self, line):
		self.logger (line)
	
	def create_socket (self, family, type):
		sock_class = socket.socket			
		self.family_and_type = family, type
		self.socket = sock_class (family, type)
		self.socket.setblocking (0)
		self._fileno = self.socket.fileno ()
		self._timeouted = 0
		self.add_channel()
		
	def handle_error (self):
		if self.debug_level: 
			self.trace ()
		self.close ()
	
	def handle_timeout (self):
		if self.debug_level: 
			self.log_info ('DNS query timeout %s' % self.callback, 'error')
			self._timeouted = 1
		self.handle_close ()
					
	def handle_connect (self):	
		self.send (self.request)
		
	def handle_write (self):
		if not self.closed:
			self.socket.shutdown (1)
		
	def handle_read (self):
		data = self.recv (4096)
		self.ac_in_buffer += data		
		
	def handle_expt (self):
		self.handle_close ()
	
	def close (self):
		if self.closed:
			return
		self.closed = True	
		asyncore.dispatcher_with_send.close (self)		
		self.callback (self.servers, self.request, self.args, self.ac_in_buffer, self._timeouted)
			
	def handle_close (self):
		self.close ()
	
	
class Request:
	def __init__(self, logger, server = [], debug_level = 1):
		if type (server) is bytes:
			server = [server]
		
		defaults ["server"] += server		
		self.logger = logger
		self.debug_level = debug_level		
		
	def argparse (self, name, args):
		args['name']=name
		for i in list(defaults.keys()):
			if i not in args:
				if i == "server": 
					args[i]=defaults[i][:]
				else:	
					args[i]=defaults[i]
				
		if type (args['server']) == bytes:
			args ['server'] = [args['server']]
			
		return args
		
	def req (self, name, **args):
		name = name.encode ("utf8")
		args = self.argparse (name, args)
		
		protocol = args ['protocol']
		port = args ['port']
		opcode = args ['opcode']
		rd = args ['rd']
		server = args ['server'][:]
		#server = ['127.0.0.1:6000']
		
		if type(args['qtype']) in (bytes, str):
			try:
				qtype = getattr (Type, args ['qtype'].upper ())
			except AttributeError:
				raise Base.DNSError('%s unknown query type' % name)
				
		else:
			qtype = args ['qtype']
			
		qname = args ['name']
		
		#print 'QTYPE %d(%s)' % (qtype, Type.typestr(qtype))
		m = Lib.Mpacker()
		# jesus. keywords and default args would be good. TODO.
		m.addHeader(0,
			  0, opcode, 0, 0, rd, 0, 0, 0,
			  1, 0, 0, 0)
		
		m.addQuestion (qname, qtype, Class.IN)
		request = m.getbuf ()
		request = Lib.pack16bit (len(request)) + request
		
		server = [(x, args ["port"]) for x in server]
		async_dns (server, request, args, self.processReply, self.logger, self.debug_level)
			
	def processReply (self, server, request, args, data, timeouted):
		if timeouted:
			# for retrying
			answers = []
			
		else:	
			# do not query for 5 minutes
			not_found = [{'err': True, "name": args ['name'].decode ('utf8'), "data": None, "typename": args ["qtype"], 'ttl': 60}]
				
			try:
				if not data:
					raise Base.DNSError('%s, no working nameservers found' % args ['name'])
			
				if args ["protocol"] == "tcp":
					header = data [:2]
					if len (header) < 2:
						raise Base.DNSError('%s, EOF' % args ['name'])
					count = Lib.unpack16bit(header)		
					reply = data [2: 2 + count]
					if len (reply) != count:
						raise Base.DNSError('%s, incomplete reply' % args ['name'])
				
				else:
					reply = data
				
			except:					
				if server:
					async_dns (server, request, args, self.processReply, self.logger, self.debug_level)
					return
					
				else:
					reply = None
			
			if reply is None:
				answers = not_found
				
			else:
				try:	
					u = Lib.Munpacker(reply)
					r = Lib.DnsResult(u, args)
					r.args = args
					answers = r.answers
				except:
					self.logger.trace ()
					answers = not_found
			
		callback = args.get ("callback", None)
		#self.logger ('DNS callback %s' % callback)
		if callback:
			if type (callback) != type ([]):
				callback = [callback]
			for cb in callback:
				cb (answers)
			

if __name__	== "__main__":
	from aquests.lib import logger
	import pprint
	f = Request (logger.screen_logger ())
	f.req ("www.yahoo.com", protocol = "tcp", callback = pprint.pprint, qtype="a")
	f.req ("www.hungryboarder.com", protocol = "tcp", callback = pprint.pprint, qtype="a")
	f.req ("www.alexa.com", protocol = "tcp", callback = pprint.pprint, qtype="a")
	f.req ("www.google.com", protocol = "tcp", callback = pprint.pprint, qtype="mx")
	asyncore.loop (timeout = 1)
	
	
