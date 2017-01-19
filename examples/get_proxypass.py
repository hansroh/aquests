import aquests

def finish_request (response):
	print (response.version, response.status_code, len (response.content))
	print (response.content [:80])
	
aquests.configure (5, callback = finish_request)		
for i in range (10):
	#aquests.get ("http://127.0.0.1:5000/lb/pypi/aquests")
	aquests.get ("http://127.0.0.1:5000/lb/")
aquests.fetchall ()
