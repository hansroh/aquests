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
	
	def decode (self, resp):
		try:
			return resp.json ()
		except ValueError:
			if resp.status_code == 200:
				return resp.content or None
			else:
				raise	
	
	def _normurl (self, s):
		if not s:
			return s
		return s [0] != "/" and s or s [1:]
		
	def post (self, uri, d = {}):
		return self.decode (self.session.post ("%s/%s" % (self.API_SERVER, self._normurl (uri)), json.dumps (d), timeout = self.REQ_TIMEOUT))
	
	def put (self, uri, d = {}):
		return self.decode (self.session.put ("%s/%s" % (self.API_SERVER, self._normurl (uri)), json.dumps (d), timeout = self.REQ_TIMEOUT))
	
	def patch (self, uri, d = {}):
		return self.decode (self.session.patch ("%s/%s" % (self.API_SERVER, self._normurl (uri)), json.dumps (d), timeout = self.REQ_TIMEOUT))
	
	def get (self, uri, p = {}):	
		return self.decode (self.session.get ("%s/%s%s" % (self.API_SERVER, self._normurl (uri), tostr (p)), timeout = self.REQ_TIMEOUT))
	
	def delete (self, uri, p = {}):
		return self.decode (self.session.delete ("%s/%s%s" % (self.API_SERVER, self._normurl (uri), tostr (p)), timeout = self.REQ_TIMEOUT))
	
	def options (self, uri):
		return self.decode (self.session.options ("%s/%s%s" % (self.API_SERVER, self._normurl (uri)), timeout = self.REQ_TIMEOUT))
	
	