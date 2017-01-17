import aquests

aquests.configure (1, http2_constreams = 10, force_http1 = 0)
for i in range (100): 
	aquests.get ("http://ibizcast.skitai.com:5000/")	
aquests.fetchall ()

aquests.configure (1, http2_constreams = 1, force_http1 = 1)
for i in range (100): 
	aquests.get ("http://ibizcast.skitai.com:5000/")	
aquests.fetchall ()

