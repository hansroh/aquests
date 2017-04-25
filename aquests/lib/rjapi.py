import requests
import json
from urllib.parse import quote

def tostr (p):
	if p:
		return "?" + "&".join (["%s=%s" % (k, quote (str (v))) for k, v in p.items ()])	
	return ""
			
class API:
	API_SERVER = "http://127.0.0.1:5000"
	REQ_TIMEOUT = 30.0
	
	def __init__ (self, server, timeout = 30.0):
		self.API_SERVER = server
		self.REQ_TIMEOUT = timeout
		self.session = requests.Session ()
			
	def post (self, uri, d):
		return self.session.post ("%s/%s" % (self.API_SERVER, uri), json.dumps (d), timeout = self.REQ_TIMEOUT).json ()
	
	def put (self, uri, d):
		return self.session.put ("%s/%s" % (self.API_SERVER, uri), json.dumps (d), timeout = self.REQ_TIMEOUT).json ()
	
	def patch (self, uri, d):
		return self.session.patch ("%s/%s" % (self.API_SERVER, uri), json.dumps (d), timeout = self.REQ_TIMEOUT).json ()
	
	def get (self, uri, p = {}):	
		return self.session.get ("%s/%s%s" % (self.API_SERVER, uri, tostr (p)), timeout = self.REQ_TIMEOUT).json ()
	
	def delete (self, uri, p = {}):
		return self.session.delete ("%s/%s%s" % (self.API_SERVER, uri, tostr (p)), timeout = self.REQ_TIMEOUT).json ()
	
	def options (self, uri):
		return self.session.options ("%s/%s%s" % (self.API_SERVER, uri), timeout = self.REQ_TIMEOUT).json ()
	
	