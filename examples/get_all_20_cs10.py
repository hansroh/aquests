import aquests

def request_finished (r):
	args = (r.status_code, r.reason, len (r.content))
	print ("%s %s %d bytes received" % args, r.version)

aquests.configure (10, callback = request_finished, force_http1 = 0, http2_constreams = 10)
for i in range (1000): 
	aquests.get ("http://127.0.0.1:5000/")	
aquests.fetchall ()
