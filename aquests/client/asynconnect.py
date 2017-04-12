import asynchat, asyncore
import re, os, sys
import ssl
import socket
import time
import zlib
from warnings import warn
from errno import ECONNRESET, ENOTCONN, ESHUTDOWN, ECONNABORTED, EWOULDBLOCK
if os.name == "nt":
	from errno import WSAENOTCONN
import select
import threading
from . import adns
from ..protocols.http2 import H2_PROTOCOLS
from ..lib.athreads.fifo import await_fifo
from ..lib.ssl_ import resolve_cert_reqs, resolve_ssl_version, create_urllib3_context
from collections import deque
from ..protocols.http import respcodes

DEBUG = 1
	
class SocketPanic (Exception): pass
class TimeOut (Exception): pass

class AsynConnect (asynchat.async_chat):
	ac_in_buffer_size = 65535
	ac_out_buffer_size = 65535
	zombie_timeout = 10
	request_count = 0
	active = 0
	proxy = False
	fifo_class = deque
	
	def __init__ (self, address, lock = None, logger = None):
		self.address = address
		self.lock = lock
		self.logger = logger
		self._cv = threading.Condition ()		
		self.__sendlock = None
		self.__no_more_request = False
		self.set_event_time ()
		self.proxy = False
		self.proxy_client = False
		self.handler = None
		self.initialize_connection ()
		#asynchat.async_chat.__init__ (self)
		self.ac_in_buffer = b''
		self.incoming = []
		self.producer_fifo = self.fifo_class ()
		asyncore.dispatcher.__init__(self)
	
	def __repr__ (self):
		return "<AsynConnect %s:%d>" % self.address
		
	def close (self):
		if self._closed:
			return
		
		if self.socket:
			# self.socket is still None, when DNS not found
			asynchat.async_chat.close (self)
			self._fileno = None
			
		# re-init asychat
		self.ac_in_buffer = b''
		self.incoming = []
		self.producer_fifo.clear()		
		self._proto = None
		self._closed = True
			
		if not self.handler:			
			# return to the pool
			return self.set_active (False)		
		if not self.errcode:
			# disconnect intentionally
			return

		handler, self.handller = self.handler, None
		keep_active = False			
		try: 
			keep_active = handler.connection_closed (self.errcode, self.errmsg)
		except: 
			self.trace ()
			
		if not keep_active:
			self.set_active (False)
			#if not self.proxy_client:
			self.logger (
				".....socket %s has been closed (reason: %d)" % ("%s:%d" % self.address, self.errcode),
				"info"
			)		
		# DO NOT Change any props, because may be request has been restarted	
		
	def end_tran (self):
		if DEBUG:
			self.logger ('end_tran {rid:%s} %s' % (self.handler.request.meta ['req_id'], self.handler.request.uri), 'debug')
		self.del_channel ()
		self.handler = None
		self.set_active (False)
				
	def use_sendlock (self):
		self.__sendlock = threading.Lock ()
		self.initiate_send = self._initiate_send_ts
		
	def _initiate_send_ts (self):
		with self.__sendlock:
			return asynchat.async_chat.initiate_send (self)
				
	def get_proto (self):
		with self.lock:
			p = self._proto
		return p
	
	def set_proto (self, proto):
		with self.lock:
			self._proto = proto		
				
	def get_history (self):
		return self.__history
				
	def initialize_connection (self):		
		self._closed = False
		self._raised_ENOTCONN = 0 # for win32
		self.__history = []
		self._proto = None
		self._handshaking = False
		self._handshaked = False		
		
		self.established = False		
		self.upgraded = False		
		
	def set_event_time (self):
		self.event_time = time.time ()
	
	def is_proxy (self):
		return self.proxy
			
	def log (self, msg, logtype):
		if self.handler is not None and hasattr (self.handler, "log"):
			self.handler.log (msg, logtype)
		elif self.logger:
			self.logger (msg, logtype)
		else:
			warn ("No logger")
			
	def trace (self):
		if self.handler is not None and hasattr (self.handler, "trace"):
			self.handler.trace ()
		elif self.logger:
			self.logger.trace ()
		else:
			warn ("No logger for traceback")
				
	def duplicate (self):
		return self.__class__ (self.address, self.lock, self.logger)
		
	def clean_shutdown_control (self, phase, time_in_this_phase):	
		self.__no_more_request = True
		if self.isactive () or (self.handler and self.handler.working ()):
			return 1
		else:				
			self.handle_close (712, "Controlled Shutdown")
			self.__no_more_request = False
			return 0
	
	def is_channel_in_map (self, map = None):
		if map is None:
			map = self._map		
		return self._fileno in map
		
	def set_active (self, flag, nolock = False):
		if flag:
			flag = time.time ()
		else:
			flag = 0
			
		if nolock or self.lock is None:
			self.active = flag
			return
			
		self.lock.acquire ()
		self.active = flag
		self.request_count += 1
		self.lock.release ()
	
	def get_active (self, nolock = False):
		if nolock or self.lock is None:
			return self.active
		self.lock.acquire ()
		active = self.active
		self.lock.release ()	
		return active
	
	def isactive (self):	
		return self.get_active () > 0
	
	def isconnected (self):
		with self.lock:
			r = self.connected
		return r	
		
	def get_request_count (self):	
		return self.request_count
		
	def del_channel (self, map = None):
		fd = self._fileno
		if map is None:
			map = self._map
		if fd in map:
			del map[fd]
            			
	def create_socket (self, family, type):		
		self.family_and_type = family, type
		sock = socket.socket (family, type)
		sock.setblocking (0)
		self.set_socket (sock)
			
	def connect (self):
		if adns.query:
			adns.query (self.address [0], "A", callback = self.continue_connect)
		else:
			# no adns query
			self.continue_connect (True)
		
	def continue_connect (self, answer = None):		
		self.initialize_connection ()
		
		ipaddr = None
		res = adns.get (self.address [0], "A")
		if res:
			ipaddr = res [-1]["data"]
		
		if not ipaddr:
			return self.handle_close (704)
		
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)		
		try:
			if not adns.query:				
				asynchat.async_chat.connect (self, self.address)				
			else:	
				asynchat.async_chat.connect (self, (ipaddr, self.address [1]))
									
		except:	
			self.handle_error (714)
	
	def recv (self, buffer_size):
		self.set_event_time ()
		try:
			data = self.socket.recv (buffer_size)			
			if not data:
				self.handle_close (700, "Connection closed unexpectedly in recv")
				return b''
			else:
				return data		
		except socket.error as why:
			if why.errno in asyncore._DISCONNECTED:
				self.handle_close (700, "Connection closed unexpectedly in recv")
				return b''				
			else:
				raise
	
	def send (self, data):
		self.set_event_time ()
		#print ("====SEND", data)
		try:
			return self.socket.send (data)
		except socket.error as why:
			if why.errno == EWOULDBLOCK:
				return 0				
			elif why.errno in asyncore._DISCONNECTED:
				#print (">>>>>>>>>> why.errno == asyncore.ENOTCONN", why.errno == asyncore.ENOTCONN)
				if os.name == "nt" and why.errno == asyncore.ENOTCONN:
					# winsock sometimes raise ENOTCONN and sometimes recovered.
					# Found this error at http://file.hungryboarder.com:8080/HBAdManager/pa.html?siteId=hboarder&zoneId=S-2
					if self._raised_ENOTCONN <= 3:
						self._raised_ENOTCONN += 1
						return 0
					else:
						self._raised_ENOTCONN = 0
				self.handle_close (700, "Connection closed unexpectedly in send")
				return 0
			else:
				raise
	
	def close_if_over_keep_live (self):
		if time.time () - self.event_time > self.zombie_timeout:
			self.disconnect ()
		
	def set_timeout (self, timeout = 10):
		self.zombie_timeout = timeout
		
	def handle_connect (self):
		if hasattr (self.handler, "has_been_connected"):		
			self.handler.has_been_connected ()
			
	def handle_expt (self):
		#self.logger ("socket panic", "fail")
		self.handle_close (703)
	
	def handle_error (self, code = 701):
		self.trace ()
		self.handle_close(code)
	
	def handle_timeout (self):
		#self.log ("socket timeout", "fail")
		self.handle_close (702)
		
	def handle_expt_event(self):
		err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
		if err != 0:
			#self.log ("Socket Error %d Occurred" % err, "warn")
			self.handle_close (703, "Socket %d Error" % err)
		else:
			self.handle_expt ()
	
	def maintern (self, object_timeout):
		if time.time () - self.event_time > object_timeout:
			if self.handler and hasattr (self.handler, "enter_shutdown_process"):
				self.handler.enter_shutdown ()
				return True
			else:	
				self.disconnect ()
				return True		
		return False
		
	# proxy POST need no init_send
	def push (self, thing, init_send = True):
		if type (thing) is bytes:
			asynchat.async_chat.push (self, thing)
		else:
			self.push_with_producer (thing, init_send)	
		
	def push_with_producer (self, producer, init_send = True):
		self.producer_fifo.append (producer)
		if init_send:
			self.initiate_send ()
	
	def handle_abort (self):
		self.handler = None
		self.close ()
		
	def handle_close (self, code = 700, msg = ""):
		if code == 0: msg = ""
		self.errcode = code
		if msg:
			self.errmsg = msg
		else:
			self.errmsg = respcodes.get (code, "Undefined Error")			
		self.close ()
							
	def collect_incoming_data (self, data):
		if not self.handler:
			self.logger ("recv data but no hander, droping data %d" % len (data), "warn")
			self.disconnect ()
			return
		self.handler.collect_incoming_data (data)
	
	def found_terminator (self):
		if not self.handler:
			self.logger ("found terminator but no handler", "warn")
			self.disconnect ()
			return # already closed
		self.handler.found_terminator ()
	
	def disconnect (self):
		# no error
		self.handle_close (0)
	
	def reconnect (self):
		self.disconnect ()		
		self.connect ()
	
	def set_proxy (self, flag = True):
		self.proxy = flag
		
	def set_proxy_client (self, flag = True):
		self.proxy_client = flag
						
	def begin_tran (self, handler):
		if self.__no_more_request:
			return self.handle_close (705)
		self.errcode = 0
		self.errmsg = ""
		
		self.handler = handler
		if DEBUG:
			self.logger ('begin_tran {rid:%s} %s' % (self.handler.request.meta ['req_id'], self.handler.request.uri), 'debug')
		self.set_event_time ()
		self.proxy_client = False
		
		if self.connected:
			self.close_if_over_keep_live () # check keep-alive
		
		# IMP: call add_channel () AFTER push()	otherwise threading issue will be raised
		try:
			if self.connected:
				#should keep order but it seems meaningless? LOOK LATER with initiate_send
				#self.initiate_send ()
				self.add_channel ()
			else:
				self.connect ()
		except:
			self.handle_error ()


class AsynSSLConnect (AsynConnect):	
	ac_negotiate_http2 = True
	
	def negotiate_http2 (self, flag):
		self.ac_negotiate_http2 = flag
		
	def handshake (self):
		if not self._handshaking:
			err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
			if err != 0:
				raise socket.error(err, _strerror(err))
				
			ssl_context = create_urllib3_context(ssl_version=resolve_ssl_version(None), cert_reqs=resolve_cert_reqs(None))
			if self.ac_negotiate_http2:
				try: ssl_context.set_alpn_protocols (H2_PROTOCOLS)
				except AttributeError: ssl_context.set_npn_protocols (H2_PROTOCOLS)								
			self.socket = ssl_context.wrap_socket (self.socket, do_handshake_on_connect = False, server_hostname = self.address [0])			
			self._handshaking = True
			
		try:
			self.socket.do_handshake ()
		except ssl.SSLError as why:
			if why.args [0] in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):
				return False
			raise ssl.SSLError(why)
			
		try: self._proto = self.socket.selected_alpn_protocol()
		except (AttributeError, NotImplementedError): 
			try: self._proto = self.socket.selected_npn_protocol()
			except (AttributeError, NotImplementedError): pass

		self._handshaked = True
		return True
							
	def handle_connect_event (self):
		try:
			if not self._handshaked and not self.handshake ():
				return
		except:
			self.handle_error (713)
			return
					
		# handshaking done
		self.handle_connect()
		self.connected = True
		
	def recv (self, buffer_size):
		self.set_event_time ()
		try:
			data = self.socket.recv (buffer_size)			
			if not data:				
				self.handle_close (700, "Connection closed unexpectedly")
				return b''
			else:				
				return data
			
		except ssl.SSLError as why:
			if why.errno == ssl.SSL_ERROR_WANT_READ:
				try: 
					raise BlockingIOError				
				except NameError:
					raise socket.error (EWOULDBLOCK)
													
			# closed connection
			elif why.errno in (ssl.SSL_ERROR_ZERO_RETURN, ssl.SSL_ERROR_EOF):
				self.handle_close (700, "Connection closed by SSL_ERROR_ZERO_RETURN or SSL_ERROR_EOF")
				return b''
				
			else:
				raise

	def send (self, data):
		self.set_event_time ()
		try:
			return self.socket.send (data)			

		except ssl.SSLError as why:
			if why.errno == ssl.SSL_ERROR_WANT_WRITE:
				return 0
			elif why.errno == ssl.SSL_ERROR_ZERO_RETURN:				
				self.handle_close (700, "Connection closed by SSL_ERROR_ZERO_RETURN")
				return 0
			else:
				raise


class AsynSSLProxyConnect (AsynSSLConnect, AsynConnect):
	def handle_connect_event (self):
		if self.established:
			AsynSSLConnect.handle_connect_event (self)
		else:	
			AsynConnect.handle_connect_event (self)
	
	def recv (self, buffer_size):	
		if self._handshaked or self._handshaking:
			return AsynSSLConnect.recv (self, buffer_size)				
		else:
			return AsynConnect.recv (self, buffer_size)
			
	def send (self, data):		
		if self._handshaked or self._handshaking:
			return AsynSSLConnect.send (self, data)
		else:
			return AsynConnect.send (self, data)

	