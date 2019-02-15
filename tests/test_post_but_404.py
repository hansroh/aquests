import aquests

def test_post_but_404 ():
	stub = aquests.rpc ("http://127.0.0.1:5000/rpc2356465")
	stub2 = aquests.rpc ("http://192.168.1.120:5000/rpc2")
	
	for i in range (300):
		stub.add_number (5, 'A' * 2048)
		#stub2.add_number (5, 7)
	
	aquests.fetchall ()
