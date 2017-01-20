import aquests

def finish_request (response):
	print (response.version, response.status_code, response.reason, len (response.content))
	print (response.content [:180])
	print (response.content)
	
aquests.configure (1, callback = finish_request, force_http1 = 0)		
for i in range (5):
	aquests.postform ("http://127.0.0.1:5000/lb/lib/login.htm", {'fid': 'i' * 105535})
	#aquests.postform ("http://127.0.0.1:5000/lb/lib/login.htm", {'fid': 'i' * 1055})
aquests.fetchall ()

