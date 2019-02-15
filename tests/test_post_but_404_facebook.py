import aquests

def test_post_but_404_facebook ():
	for i in range (1):
		aquests.postform ("https://www.facebook.com/asdakjdhakjdhajkdhajkd", {"aa.": "a" * 10000000})
	
	aquests.fetchall ()
