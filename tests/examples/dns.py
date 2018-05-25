import aquests

def request_finished (r):
	print (r.lxml)

aquests.configure (1, callback = request_finished)	
aquests.get ("http://rdsapi.skitai.com:5000/")
aquests.fetchall ()

