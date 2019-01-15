from ..http import request
from rs4 import strutil
from .producer import ws_producer
import struct
import os

class Request (request.HTTPRequest):
	def __init__ (self, uri, message, headers = None, auth = None, logger = None, meta = {}, http_version = "1.1"):
		self.message = message
		if uri.startswith ("ws://"):
			uri = "http://" + uri [5:]
		elif uri.startswith ("wss://"):
			uri = "https://" + uri [6:]
		request.HTTPRequest.__init__ (self, uri, "websocket", {}, headers, auth, logger, meta, http_version)		
		
	def get_cache_key (self):
		return None
			
	def serialize (self):
		return ws_producer (self.message)
	
	