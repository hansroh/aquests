import aquests

aquests.configure (10)
for i in range (100):
	aquests.postjson ("http://127.0.0.1:5000/post", {'username': 'A' * 1000000})
aquests.fetchall ()

