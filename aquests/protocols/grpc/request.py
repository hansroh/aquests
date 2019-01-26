import struct
from rs4 import attrdict
from .producers import grpc_producer
from ..http.request import XMLRPCRequest

class GRPCRequest (XMLRPCRequest):
	initial_http_version = "2.0"
	use_compress = False
	def __init__ (self, uri, method, params = (), headers = None, auth = None, logger = None, meta = {}, http_version = "2.0"):
		self.uri = uri
		self.method = method
		self.params = params
		self.auth = (auth and type (auth) is not tuple and tuple (auth.split (":", 1)) or auth)
		self.logger = logger
		self.meta = meta
		self.http_version = http_version
		self.address, self.path = self.split (uri)
	
		self.headers = attrdict.CaseInsensitiveDict ({
			"grpc-timeout": "10S",			
			"grpc-accept-encoding": "identity,gzip",
			"user-agent": self.user_agent,
			"message-type": self.params [0].__class__.__name__,
			"te": 'trailers',
		})
		if self.use_compress:
			self.headers ["grpc-encoding"] = "gzip",
			
		self.payload = self.serialize ()
		if not self.payload:
			self.method = "GET"
		else:
			self.headers ["Content-Type"] = "application/grpc+proto"
		
	def get_cache_key (self):
		return None
		
	def xmlrpc_serialized (self):
		return False
			
	def split (self, uri):
		address, path = XMLRPCRequest.split (self, uri)
		if path [-1] != "/":
			path += "/"
			self.uri += "/"
		path += self.method
		self.uri += self.method
		return address, path
	
	def serialize (self):		
		return grpc_producer (self.params [0], self.use_compress)
	