import aquests

def request_finished (r):
	args = (r.status_code, r.reason, len (r.content))
	print ("%s %s %d bytes received" % args, r.version)

def test_get_all_static ():
	aquests.configure (2, callback = None, force_http_11 = False)
	for i in range (200): 
		aquests.get ("http://127.0.0.1:5000/images/gif1.gif")
		#aquests.get ("http://127.0.0.1:5000/images/concept.png")	
	aquests.fetchall ()
