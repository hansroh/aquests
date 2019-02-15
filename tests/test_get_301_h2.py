import aquests

def finish_request (response):
	aquests.cb_gateway_demo (response)
	print (response.history)

def test_get_301_h2 ():	
	aquests.configure (callback = finish_request, allow_redirects = 1)
	for i in range (1):
		aquests.get ("https://www.google.com/")
	aquests.fetchall ()
