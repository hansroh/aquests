import aquests

def request_finished (r):
	args = (r.status_code, r.reason, len (r.content))
	print ("%s %s %d bytes received" % args, r.version)

def test_get_all_20_cs10 ():
	aquests.configure (10, callback = request_finished, force_http1 = 0, http2_constreams = 3)
	for i in range (1000): 
		aquests.get ("https://127.0.0.1:5002/v1/console/needtofix")	
	aquests.fetchall ()
