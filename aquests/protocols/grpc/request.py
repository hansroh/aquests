import struct
from .producers import grpc_producer
from aquests.protocols.http.request import XMLRPCRequest

class GRPCRequest (XMLRPCRequest):
	initial_http_version = "2.0"
	
	def __init__ (self, uri, method, params = (), headers = None, encoding = "utf8", auth = None, logger = None, meta = {}):
		self.uri = uri
		self.method = method
		self.params = params
		self.encoding = encoding
		self.auth = (auth and type (auth) is not tuple and tuple (auth.split (":", 1)) or auth)
		self.logger = logger
		self.meta = meta
		self.address, self.path = self.split (uri)
	
		self.headers = {
			"grpc-timeout": "10S", 
			"grpc-encoding": "gzip",
			"grpc-accept-encoding": "identity,gzip",
			"user-agent": self.user_agent,
			"message-type": self.params [0].__class__.__name__,
		}		
		self.payload = self.serialize ()
		if not self.payload:
			self.method = "GET"
		else:
			self.headers ["Content-Type"] = "application/grpc"		
	
	def get_cache_key (self):
		return None
		
	def xmlrpc_serialized (self):
		return False
			
	def split (self, uri):
		(host, port), path = XMLRPCRequest.split (self, uri)				
		if path [-1] != "/":
			path += "/"
			self.uri += "/"
		path += self.method
		self.uri += self.method
		return (host, port), path
	
	def serialize (self):
		return grpc_producer (self.params [0])
	
	def get_content_length (self):
		return self.payload.get_content_length ()
		
