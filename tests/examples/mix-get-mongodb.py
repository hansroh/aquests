import aquests

dbo = aquests.mongodb ("127.0.0.1:27017", "test_database")
aquests.configure (20)
for i in range (1000): 
	aquests.get ("http://127.0.0.1:5000/")
	dbo.findone ("posts", {"author": "Hans Roh"})
aquests.fetchall ()
