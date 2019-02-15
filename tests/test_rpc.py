import aquests

def test_rpc ():	
	aquests.configure (10)
	stub = aquests.rpc ("http://127.0.0.1:5000/rpc2")
	for i in range (30):
		stub.add_number (5, 7)
	aquests.fetchall ()
	
