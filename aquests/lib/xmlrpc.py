import xmlrpc.client
from . import timeoutsocket

timeoutsocket.setDefaultSocketTimeout(3)

servers = []

class ServerNotDefined (Exception): pass

def setup (serverlist, timeout = 3):
	global servers
	servers = serverlist
	timeoutsocket.setDefaultSocketTimeout(timeout)

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
