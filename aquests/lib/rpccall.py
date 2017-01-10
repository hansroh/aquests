import xmlrpc.client
from . import timeoutsocket

timeoutsocket.setDefaultSocketTimeout(3)

servers = []

class ServerNotDefined (Exception): pass

def set (serverlist):
	global servers
	servers = serverlist

def call (method, args):
	global servers
	if not servers:
		raise ServerNotDefined

	for server in servers:
		try:
			s = xmlrpc.client.Server ("http://" + server)
			resp = getattr (s, method) (*args)
			return resp
		except:
			pass
	raise			
