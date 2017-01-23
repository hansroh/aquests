import aquests

def finish_request (response):
	aquests.cb_gateway_demo (response)
	
aquests.configure (callback = finish_request)
for i in range (1):
	aquests.get ("http://127.0.0.1:5000/r1")	
aquests.fetchall ()
