import aquests

aquests.configure (10)
for i in range (100):
	aquests.postform ("http://127.0.0.1:5000/test/signin", {'username': 'A' * 1000000})
aquests.fetchall ()

