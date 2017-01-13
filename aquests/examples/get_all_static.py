import aquests

def request_finished (r):
	args = (r.status_code, r.reason, len (r.content))
	print ("%s %s %d bytes received" % args, r.version)

aquests.configure (10, callback = request_finished)
for i in range (200): 
	aquests.get ("http://127.0.0.1:5000/images/gif1.gif")
aquests.fetchall ()
