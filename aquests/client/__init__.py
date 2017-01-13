from . import asynconnect

def set_timeout (timeout):
	for each in (asynconnect.AsynConnect, asynconnect.AsynSSLConnect, asynconnect.AsynSSLProxyConnect):
		each.keep_alive_timeout = timeout
		each.network_delay_timeout = timeout
		