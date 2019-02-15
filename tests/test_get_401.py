import aquests

def finish_request (response):
	aquests.cb_gateway_demo (response)
	print (response.history)

def test_get_401 ():	
	aquests.configure (callback = finish_request, force_http1 = 0)
	for i in range (1):
		aquests.get ("http://127.0.0.1:5000/", auth = ('admin', '1111'))
	aquests.fetchall ()
