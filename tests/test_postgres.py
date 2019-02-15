import aquests

def test_postgres ():
	dbo = aquests.postgresql ("127.0.0.1:5432", "mydb", ("test", "1111"))
	for i in range (100):
		dbo.do ("SELECT * FROM weather;")
	
	aquests.fetchall ()

