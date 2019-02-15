import aquests

def test_redisex ():
	dbo = aquests.redis ("127.0.0.1:6379")
	for i in range (3):
		dbo.get ("EFG")
	
	aquests.fetchall ()

