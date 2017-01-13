import aquests

stub = aquests.rpc ("http://127.0.0.1:5000/")
stub.add_number (5, 7)
stub.add_number (5, 'a')
stub.add_number (5, 8, 9)

aquests.fetchall ()
