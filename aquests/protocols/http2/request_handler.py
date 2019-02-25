from ...protocols.http import base_request_handler
from h2.connection import H2Connection, GoAwayFrame
from h2.exceptions import ProtocolError, NoSuchStreamError, StreamClosedError, FlowControlError
from h2.events import TrailersReceived, DataReceived, ResponseReceived, StreamEnded, ConnectionTerminated, StreamReset, WindowUpdated, RemoteSettingsChanged
from h2.errors import ErrorCodes
from h2.settings import SettingCodes
from rs4 import producers
from .producers import h2frame_producer, h2header_producer
from ..http import respcodes
from ..http import response as http_response

from ...client import asynconnect
import threading
try:
	from cStringIO import StringIO as BytesIO
except ImportError:
	from io import BytesIO


			
class FakeAsynConnect:
	collector = None
	def __init__ (self, asyncon, logger):
		self.asyncon = asyncon
		self.logger = logger
	
	def get_proto (self):
		return "h2"
		
	def is_proxy (self):
		return False
		
	def handle_close (self, *args, **karg):
		pass
		
	def handle_error (self):
		self.logger.trace ()
	
	def isconnected (self):
		return True
		
	def push (self, *args, **karg):	
		pass
	
	def set_terminator (self, *args, **karg):
		pass		
			
	def get_terminator (self):
		pass
	
	def begin_tran (self, *args, **karg):	
		pass
	
	def end_tran (self, *args, **karg):	
		pass	
	
	def collect_incoming_data (self):
		if self.collector:
			self.collector.collect_incoming_data ()
	
	def disconnect (self):
		pass
			

class FlowControlWindow:
	MIN_RFCW = 4096
	MIN_IBFCW = 65535
	INRCEMENT_DELTA = 1048576
	
	def reset_stream (self, stream_id, error_code = 3):
		self.conn.reset_stream (stream_id, error_code = 3)				 
		
	def adjust_flow_control_window (self, stream_id):
		if self.conn.inbound_flow_control_window < self.MIN_IBFCW:			
			with self._clock:
				self.conn.increment_flow_control_window (self.INRCEMENT_DELTA)
				
		rfcw = self.conn.remote_flow_control_window (stream_id)
		if rfcw < self.MIN_RFCW:
			try:
				with self._clock:
					self.conn.increment_flow_control_window (self.INRCEMENT_DELTA, stream_id)
			except StreamClosedError:
				pass
			except:
				self.reset_stream (stream_id, 3)
	
		
class RequestHandler (base_request_handler.RequestHandler, FlowControlWindow):
	# HTTP2 Adaptor Class	
	# this class rely: asyncon - this class - http_reqyest_handler
	def __init__ (self, handler):
		self.asyncon = handler.asyncon
		self.request = handler.request
		base_request_handler.RequestHandler.__init__ (self, handler.request.logger)
		#self.asyncon.set_timeout (60, 60)
		self.lock = handler.asyncon.lock # pool lock
		self._ssl = handler._ssl
		
		self._clock = threading.RLock () # conn lock
		self._llock = threading.RLock () # local lock
		self.fakecon = FakeAsynConnect (self.asyncon, self.logger)		
		
		self.initiate ()		
		is_upgrade = not (self._ssl or self.request.initial_http_version == "2.0")			
		if is_upgrade:
			self.conn.initiate_upgrade_connection()
			self.conn.update_settings({SettingCodes.ENABLE_PUSH: 0})
			# assume 1st request's stream_id = 1
			self.add_request (1, handler)
			self._send_stream_id = 1 # nexet request stream_id will be 3
		else:		    
			self.conn.initiate_connection()				
			
		self.send_data ()
		self.asyncon.set_terminator (9)
		
		if not is_upgrade:			
			self.handle_request (handler)
		else:
			self.asyncon.set_active (False)
	
	def initiate (self):	
		self.asyncon.handler = self
		self.asyncon.use_sendlock ()
		self._send_stream_id = -1
		self.requests = {}
		self.conn = H2Connection ()		
		self.conn.local_settings.initial_window_size = 65535
		
		self.buf = b""
		self.rfile = BytesIO ()		
		self.frame_buf = self.conn.incoming_buffer		
		self.frame_buf.max_frame_size = self.conn.max_inbound_frame_size
		self.data_length = 0
		self.current_frame = None
	
	def working (self):
		return self.jobs () and True or False
	
	def jobs (self):
		with self._llock:
			return len (self.requests)
		
	def go_away (self, errcode = 0, msg = None):
		with self._clock:
			self.conn.close_connection (errcode, msg)
		self.send_data ()
		self.channel.close_when_done ()	
		
	def control_shutdown (self, err = 0):
		self.go_away (ErrorCodes.NO_ERROR)		
				
	def add_request (self, stream_id, handler):		
		handler.asyncon = self.fakecon
		with self._llock:
			self.requests [stream_id] = handler
				
	def get_new_stream_id (self):
		with self._llock:
			self._send_stream_id += 2
			stream_id = self._send_stream_id
		return stream_id
	
	def send_data (self):
		with self._clock:
			data_to_send = self.conn.data_to_send ()						
		if data_to_send:			
			self.asyncon.push (data_to_send)
							
	def handle_request (self, handler):
		self.request = handler.request
		stream_id = self.get_new_stream_id ()		
		self.add_request (stream_id, handler)		
		self.asyncon.set_active (False)		
		
		headers, content_encoded = handler.get_request_header ("2.0", False)
		payload = handler.get_request_payload ()
		producer = None
		if payload:
			if type (payload) is bytes:
				producer = producers.globbing_producer (
					producers.simple_producer (payload)
				)
			else:
				# multipart, grpc_producer 
				producer = producers.globbing_producer (payload)
		
		header = h2header_producer (stream_id, headers, producer, self.conn, self._clock)		
		self.asyncon.push (header)		
		if producer:
			payload = h2frame_producer (stream_id, 0, 1, producer, self.conn, self._clock)
			# is it proper?
			#payload = producers.ready_globbing_producer (payload)
			self.asyncon.push (payload)
					
	def collect_incoming_data (self, data):		
		if not data:  return
		if self.data_length:
			self.rfile.write (data)
		else:
			self.buf += data
	
	def connection_closed (self, why, msg):
		with self._llock:
			requests = list (self.requests.items ())
		for stream_id, h in requests:
			h.response = http_response.FailedResponse (720, respcodes.get (720), h.request)			
			h.handle_callback ()
		with self._llock:
			self.requests = {}

	def found_terminator (self):
		buf, self.buf = self.buf, b""		
		events = None
		if self.data_length:			
			events = self.set_frame_data (self.rfile.getvalue ())				
			self.data_length = 0
			self.current_frame = None
			self.rfile.seek (0)
			self.rfile.truncate ()
			self.asyncon.set_terminator (9) # for frame header
						
		elif buf:
			self.current_frame, self.data_length = self.frame_buf._parse_frame_header (buf)
			self.frame_buf.max_frame_size = self.data_length
			if self.data_length == 0:
				events = self.set_frame_data (b'')
			self.asyncon.set_terminator (self.data_length == 0 and 9 or self.data_length)	# next frame header
			
		else:
			raise ProtocolError ("Frame decode error")
		
		if events:
			self.handle_events (events)	
	
	def set_frame_data (self, data):
		if not self.current_frame:
			return []
		self.current_frame.parse_body (memoryview (data))				
		self.current_frame = self.frame_buf._update_header_buffer (self.current_frame)
		with self._clock:
			events = self.conn._receive_frame (self.current_frame)
		return events
	
	def get_handler (self, stream_id):
		h = None
		with self._llock:
			try: h =	self.requests [stream_id]
			except KeyError: pass
		return h		
	
	def remove_handler (self, stream_id):
		with self._llock:
			try: del	self.requests [stream_id]
			except KeyError: pass
		
	def handle_response (self, stream_id, headers):
		# to HTTP/1.1 header
		jheaders = []
		for k, v in headers:
			k = k.decode ("utf8")
			v = v.decode ("utf8")
			if k == ":status":
				jheaders.insert (0, "HTTP/2.0 " + v + " " + respcodes.get (int (v), "Undefined Error"))
			else:
				jheaders.append (k + ": " + v)
		
		h = self.get_handler (stream_id)
		if h:
			h.collect_incoming_data ("\r\n".join (jheaders).encode ("utf8"))
			h.found_terminator ()
		# finally, make inactive on post, put request 
		self.asyncon.set_active (False)
	
	def handle_trailers (self, stream_id, headers):
		respheader = self.get_handler (stream_id).response.header
		for k, v in headers:			
			respheader.append ("{}: {}".format (k.decode ("utf8"), v.decode ("utf8")))
					
	def handle_events (self, events):
		for event in events:			
			if isinstance(event, ResponseReceived):				
				self.handle_response (event.stream_id, event.headers)
			
			elif isinstance(event, TrailersReceived):
				self.handle_trailers (event.stream_id, event.headers)
				
			elif isinstance(event, StreamReset):
				if event.remote_reset:				
					h = self.get_handler (event.stream_id)
					if h:
						h.response = http_response.FailedResponse (721, respcodes.get (721), h.request)
						h.handle_callback ()
						self.remove_handler (event.stream_id)
					
			elif isinstance(event, ConnectionTerminated):
				self.asyncon.handle_close (721, "HTTP2 Connection Terminated")
				
			elif isinstance (event, DataReceived):
				h = self.get_handler (event.stream_id)
				if h:
					h.collect_incoming_data (event.data)
					self.adjust_flow_control_window (event.stream_id)
													
			elif isinstance(event, StreamEnded):
				h = self.get_handler (event.stream_id)
				if h:
					self.remove_handler (event.stream_id)
					h.found_terminator ()
					
		self.send_data ()
		