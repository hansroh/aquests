import aquests


def get_all_20_cs10 ():
	aquests.configure (2000, http2_constreams = 1, force_http1 = 1)
	for i in range (3000): 
		aquests.get ("http://127.0.0.1:5000/")	
	aquests.fetchall ()

