import requests
import json

def tostr (p):
	if p:
		return dict ([(k, str (v)) for k, v in p.items ()])	
			
class API:
	API_SERVER = "http://127.0.0.1:5000"
	REQ_TIMEOUT = 30.0
	
	def __init__ (self, server, timeout = 30.0):
		self.API_SERVER = server
		self.REQ_TIMEOUT = timeout
			
	def post (self, uri, d):
		return requests.post ("%s/%s" % (self.API_SERVER, uri), json.dumps (d), timeout = self.REQ_TIMEOUT).json ()
	
	def put (self, uri, d):
		return requests.put ("%s/%s" % (self.API_SERVER, uri), json.dumps (d), timeout = self.REQ_TIMEOUT).json ()
	
	def get (self, uri, p = {}):	
		return requests.get ("%s/%s" % (self.API_SERVER, uri), tostr (p), timeout = self.REQ_TIMEOUT).json ()
	
	def delete (self, uri):
		return requests.delete ("%s/%s" % (self.API_SERVER, uri), timeout = self.REQ_TIMEOUT).json ()

