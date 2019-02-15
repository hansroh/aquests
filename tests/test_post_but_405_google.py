import aquests

def test_post_but_405_google ():
	for i in range (3):
		aquests.postform ("https://www.google.co.kr/search?q=pypi", {"aa.": "aaa"})
	
	aquests.fetchall ()
