import aquests

def test_sqllite3 ():
	dbo = aquests.sqlite3 ("d:/var/sqlite3-test.db")
	for i in range (3):
		dbo.do ("select * from people;")
	
	aquests.fetchall ()
	
