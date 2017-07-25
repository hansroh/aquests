import time
try:
	from h2.exceptions import FlowControlError
except ImportError:
	pass	
from aquests.lib import producers
import asynchat

class h2header_producer:
	def __init__ (self, stream_id, headers, producer, encoder, lock):
		# DO NOT set self.stream_id
		# if set, http2_producer_fifo try to re-sort and will raise error
		self.__stream_id = stream_id
		with lock:
			encoder.send_headers (
				stream_id = self.__stream_id,
				headers = headers,
				end_stream = producer is None
			)
			self.data_to_send = encoder.data_to_send ()
	
	def get_size (self):
		return 0
		
	def __repr__ (self):
		return "<h2header_producer stream_id:%d>" % (self.__stream_id,)
	
	def more (self):		
		data_to_send, self.data_to_send = self.data_to_send, b''
		return data_to_send


class h2frame_producer:
	SIZE_BUFFER = 16384
	
	def __init__ (self, stream_id, depends_on, weight, producer, encoder, lock):
		self.stream_id = stream_id
		self.depends_on = depends_on
		self.weight = weight
		self.producer = producer # globbing_producer
		self.encoder = encoder
		
		self._lock = lock
		self._buf = b""
		self._end_stream = False		
		self._last_sent = time.time ()
		
		if hasattr (producer, "ready"):
			self.ready = producer.ready
			producer.ready = None
	
	def get_size (self):			
		return self.producer.get_size ()
		
	def __repr__ (self):
		return "<h2frame_producer stream_id:%d, weight:%d, depends_on:%d>" % (self.stream_id, self.weight, self.depends_on)
	
	def is_done (self):
		return self._end_stream and not self._buf
	
	def is_end_stream (self, data):
		return not data or len (data) < self.producer.buffer_size
				 	
	def more (self):
		if self.is_done ():
			return b''

		if self._buf:
			data, self._buf = self._buf [:self.SIZE_BUFFER], self._buf [self.SIZE_BUFFER:]
				
		else:
			data = self.producer.more ()
			self._end_stream = self.is_end_stream (data)
			if len (data) > self.SIZE_BUFFER:
				data, self._buf = data [:self.SIZE_BUFFER], data [self.SIZE_BUFFER:]
		
		# print ("MULTIPLEXING", self.stream_id, self.encoder.local_flow_control_window (self.stream_id))
		with self._lock:
			try:
				self.encoder.send_data (
					stream_id = self.stream_id,
					data = data,
					end_stream = self.is_done ()
				)
				self._last_sent = time.time ()	
				data_to_send = self.encoder.data_to_send ()
				
			except FlowControlError:
				# close forcely
				return b''
		
		return data_to_send
	
	
class h2stream_producer (h2frame_producer):
	def __repr__ (self):
		return "<h2stream_producer stream_id:%d>" % (self.stream_id,)
	
	def get_size (self):			
		return -1
		
	def is_end_stream (self, data):
		return len (data) == 0
		
	def more (self):
		if self.is_done ():
			return b''

		if self._buf:
			data, self._buf = self._buf [:self.SIZE_BUFFER], self._buf [self.SIZE_BUFFER:]
				
		else:
			data = self.producer.more ()
			self._end_stream = self.is_end_stream (data)
			if len (data) > self.SIZE_BUFFER:
				data, self._buf = data [:self.SIZE_BUFFER], data [self.SIZE_BUFFER:]
		
		with self._lock:
			try:
				self.encoder.send_data (
					stream_id = self.stream_id,
					data = data,
					end_stream = self.is_done ()
				)
				self._last_sent = time.time ()	
				data_to_send = self.encoder.data_to_send ()
				
			except FlowControlError:
				# close forcely
				return b''
		
		return data_to_send

class h2_globbing_producer (producers.globbing_producer):
	def __init__ (self, stream_id, depends_on, weight,  producer, buffer_size = producers.SIZE_BUFFER):
		self.stream_id = stream_id
		self.depends_on = depends_on
		self.weight = weight
		producers.globbing_producer.__init__ (self, producer, buffer_size)
		
