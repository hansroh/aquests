from redis import connection as redisconn
import asynchat
from . import dbconnect	
import socket

DEBUG = True
LINE_FEED = b"\r\n"

import redis.connection


class RedisError (Exception):
	pass
	
	
class AsynConnect (dbconnect.AsynDBConnect, asynchat.async_chat):	
	def __init__ (self, address, params = None, lock = None, logger = None):
		dbconnect.AsynDBConnect.__init__ (self, address, params, lock, logger)
		self.redis = redisconn.Connection ()
		asynchat.async_chat.__init__ (self)
	
	def close (self, deactive = 1):
		asynchat.async_chat.close (self)				
		# re-init asychat
		self.ac_in_buffer = b''
		self.incoming = []
		self.producer_fifo.clear()
				
		dbconnect.AsynDBConnect.close (self, deactive)
		self.logger ("[info] ..dbo %s:%d has been closed" % self.address)
		
	def handle_connect (self):
		self.set_event_time ()		
		if self.user:			
			self.push_command ('AUTH', self.password)		
	
	def push_command (self, *args):
		self.set_event_time ()
		self.last_command = args [0].upper ()
		command = self.redis.pack_command (self.last_command, *args [1:])		

		if isinstance(command, list):
			command = b"".join (command)		
		self.push (command)
			    						
	def connect (self):
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)		
		try:
			asynchat.async_chat.connect (self, self.address)
		except:	
			self.handle_error ()
	
	def collect_incoming_data (self, data):
		self.set_event_time ()
		self.data.append (data)
	
	def fetchall (self):
		try:
			res = self.response [0][0]
		except IndexError:
			res = None
		self.response = []		
		return res
	
	def add_element (self, e):
		if type (e) is bytes:
			e = e.decode ("utf8")
		self.response [-1].append (e)
		self.num_elements [-1] -= 1
		while self.num_elements and self.num_elements [-1] <= 0:		
			self.num_elements.pop (-1)
			if len (self.response) > 1:
				item = self.response.pop (-1)
				self.response [-1].append (item)		
		
	def raise_error (self, e):
		raise RedisError (e.decode ("utf8"))
		
	def found_terminator (self):
		if self.last_command == "AUTH":
			if self.data [-1] != b"+OK":
				self.raise_error (self.data [-1][1:])
			if self.dbname:
				return self.push_command ('SELECT', self.dbname)
										
		if self.last_command == "SELECT" and self.data [-1] != b"+OK":
			self.raise_error (self.data [-1][1:])
		
		header = self.data [-1][:1]
		if self.length != -1:
			self.add_element (self.data [-1][:-2])
			self.data = []
			self.length = -1
			self.set_terminator (LINE_FEED)
		
		elif header in b"-":
			self.raise_error (self.data [-1][1:])

		elif header in b"+":
			self.add_element (self.data [-1][1:])
			self.has_result = True	
			self.set_terminator (LINE_FEED)
				
		elif header in b":":
			self.add_element ((int (self.data [-1][1:]),))			
			self.set_terminator (LINE_FEED)
			
		elif header == b"$":
			self.length = int (self.data [-1][1:]) + 2
			if self.length == 1:
				self.add_element (None)				
				self.data = []				
				self.set_terminator (LINE_FEED)	
				self.length = -1
			else:	
				self.set_terminator (self.length)
		
		elif header == b"*":
			num_elements = int (self.data [-1][1:])
			if self.num_elements [-1] == -1:
				self.add_element (None)
			else:
				self.response.append ([])
				self.num_elements.append (num_elements)
			self.data = []
			self.set_terminator (LINE_FEED)
			
		else:
			raise ValueError ("Protocol Error")	
		
		if not self.num_elements:
			self.has_result = True
			self.close_case_with_end_tran ()

	def close_case (self):
		if self.request:
			self.request.handle_result (None, self.expt, self.fetchall ())
			self.request = None
		self.set_active (False)
	
	def end_tran (self):
		if not self.backend:
			self.del_channel ()
		
	def begin_tran (self, request):
		dbconnect.AsynDBConnect.begin_tran (self, request)			
		self.response = [[]]
		self.data = []
		self.length = -1
		self.num_elements = [0]
		self.last_command = None		
						
	def execute (self, request):
		self.begin_tran (request)		
		# SHOULD push before adding to map, otherwise raised threading collision
		self.push_command (request.method, *request.params)
		self.set_terminator (LINE_FEED)
		if not self.connected:
			self.connect ()
		elif not self.backend:
			self.add_channel ()
		