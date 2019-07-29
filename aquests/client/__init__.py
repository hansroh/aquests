from . import asynconnect

def set_timeout (timeout):
	for each in (asynconnect.AsynConnect, asynconnect.AsynSSLConnect, asynconnect.AsynSSLProxyConnect):
		each.keep_alive = timeout
		each.zombie_timeout = timeout
		