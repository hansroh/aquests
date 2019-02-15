import aquests

def test_mongodbex ():
	dbo = aquests.mongodb ("127.0.0.1:27017", "test_database")
	for i in range (3):
		dbo.findone ("posts", {"author": "Hans Roh"})
	
	aquests.fetchall ()

