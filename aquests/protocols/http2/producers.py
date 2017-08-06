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
		self._ready = None
		self._frame = b''
		
		if hasattr (producer, "ready"):
			self._ready = producer.ready
			producer.ready = None
	
	def ready (self):		
		if self.is_done ():
			return True
			
		if self._frame:
			# data or reset
			return True
		
		lfcw = self.encoder.local_flow_control_window (self.stream_id)
		#print ("---MULTIPLEXING", self.stream_id, lfcw)
		
		if lfcw == 0:
			# flow control error, graceful close
			if time.time () - self._last_sent > 10:
				 self.encoder.reset_stream (stream_id, error_code = errcode)
				 self._frame = self.encoder.data_to_send ()
				 self._buf = b''
				 self._end_stream = True
				 return True
			return False
		
		avail_data_length = min (self.SIZE_BUFFER, lfcw)
		if not self._buf:
			if self._ready and not self._ready ():
				return False				
			self._buf = self.producer.more ()
			self._end_stream = self.is_end_stream (self._buf)			
		data, self._buf = self._buf [:avail_data_length], self._buf [avail_data_length:]
		
		# try build frame
		with self._lock:		
			self.encoder.send_data (
				stream_id = self.stream_id,
				data = data,
				end_stream = self._end_stream and not self._buf
			)
			self._frame = self.encoder.data_to_send ()
			
		return True
		
	def get_size (self):			
		return self._ready and -1 or self.producer.get_size ()
		
	def __repr__ (self):
		return "<h2frame_producer stream_id:%d, weight:%d, depends_on:%d>" % (self.stream_id, self.weight, self.depends_on)
	
	def is_done (self):
		return self._end_stream and not self._buf and not self._frame
	
	def is_end_stream (self, data):
		return self._ready and len (data) == 0 or len (data) < self.producer.buffer_size
				 	
	def more (self):
		#print ('++++++++++++++more', len (self._frame), self.is_done ())
		self._last_sent = time.time ()
		if self.is_done ():
			return b''
		frame, self._frame = self._frame, b''		
		return frame
	