import base64
from hashlib import md5
import os
from . import http_util

class Authorizer:
	def __init__ (self):
		self.db = {}
	
	def get (self, netloc, auth, method, uri, data):
		if netloc not in self.db:
			return ""
			
		infod = self.db [netloc]
		if infod ["meth"] == "basic":
			return "Basic " + base64.encodestring ("%s:%s" % auth) [:-1]
		elif infod ["meth"] == "bearer":
			return "Bearer " + auth [0]
		else:
			infod ["nc"] += 1
			hexnc = hex (infod ["nc"])[2:].zfill (8)
			infod ["cnonce"] = http_util.md5uniqid ()
			
			A1 = md5 (("%s:%s:%s" % (auth [0], infod ["realm"], auth [1])).encode ("utf8")).hexdigest ()
			if infod ["qop"] == "auth":
				A2 = md5 (("%s:%s" % (method, uri)).encode ("utf8")).hexdigest ()
			elif infod ["qop"] == "auth-int" and type (data) is bytes:
				entity = md5 (data).hexdigest ()
				A2 = md5 (("%s:%s:%s" % (method, uri, entity)).encode ("utf8")).hexdigest ()
			else:
				return # sorry data is not bytes or unknown qop
						
			Hash = md5 (("%s:%s:%s:%s:%s:%s" % (
				A1,
				infod ["nonce"],
				hexnc,
				infod ["cnonce"],
				infod ["qop"],
				A2
				)).encode ("utf8")
			).hexdigest ()
			
			return (
				'Digest username="%s", realm="%s", nonce="%s", '
				'uri="%s", response="%s", opaque="%s", qop=%s, nc=%s, cnonce="%s"' % (
					auth [0], infod ["realm"], infod ["nonce"], uri, Hash, 
					infod ["opaque"], infod ["qop"], hexnc, infod ["cnonce"]
				)
			)
			
	def set (self, netloc, authreq, auth):
		if auth is None:
			return
		
		amethod, authinfo = authreq.split (" ", 1)		
		infod = {"meth": amethod.lower ()}
		infod ["nc"] = 0
		for info in authinfo.split (","):
			k, v = info.strip ().split ("=", 1)
			if not v: return self.get_www_authenticate ()
			if v[0] == '"': v = v [1:-1]
			infod [k]	 = v
		
		if "qop" in infod:
			qop = list (map (lambda x: x.strip (), infod ["qop"].split (",")))
			if "auth" in qop:
				infod ["qop"] = "auth"
			else:
				infod ["qop"] = "auth-int"
				
		self.db [netloc] = infod
		
	def make_http_auth_header (self, request, is_proxy = False):
		auth = request.get_auth ()		
		if auth:
			uri = is_proxy and request.uri or request.path
			auth_header = self.get (request.get_address (), auth, request.get_method (), uri, request.get_payload ())
			if auth_header is None:
				raise AssertionError ("Unknown authedentification method")
			return auth_header			
	
	def save_http_auth_header (self, request, response):
		self.set (
			request.get_address (), 
			response.get_header ("WWW-Authenticate"), 
			request.get_auth ()
		)	

authorizer = Authorizer ()

