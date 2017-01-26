from aquests.protocols.http import request
from aquests.lib import strutil
from .producer import ws_producer
import struct
import os

class Request (request.HTTPRequest):
	def __init__ (self, uri, message, headers = None, auth = None, logger = None, meta = {}):
		self.message = message
		if uri.startswith ("ws://"):
			uri = "http://" + uri [5:]
		elif uri.startswith ("wss://"):
			uri = "https://" + uri [6:]
		request.HTTPRequest.__init__ (self, uri, "websocket", {}, headers, auth, logger, meta)		
		
	def get_cache_key (self):
		return None
			
	def serialize (self):
		return ws_producer (self.message)
	
	