import aquests
	
aquests.configure (force_http1 = 1, timeout = 20)
for i in range (1):
	aquests.get ("http://ibizcast.skitai.com:5000/lb/board/lists/?id=classic&page=1", auth = ("12345678-1234-123456",))
aquests.fetchall ()
