import aquests

CONCURRENT = 50
MAX_REQ = 1000
_ID = 0

def makeload (response):
	global _ID
	print (response.meta ['_id'], response.code, response.msg, response.version)
	if aquests.countreq () < MAX_REQ:
		aquests.get ("http://127.0.0.1:5000/", meta = {'_id': _ID})	
		_ID += 1
	
aquests.configure (CONCURRENT, callback = makeload) # cioncurrent
for i in range (CONCURRENT): 
	aquests.get ("http://127.0.0.1:5000/", meta = {'_id': _ID})
	_ID += 1
	
aquests.fetchall ()

