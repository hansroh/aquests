import aquests

def request_finished (r):
    print (r.cookie)

def test_cookie ():
    aquests.configure (1, cookie = True, callback = request_finished)	
    aquests.get ("https://www.google.co.kr/?gfe_rd=cr&ei=3y14WPCTG4XR8gfSjoK4DQ")
    aquests.get ("https://aws.amazon.com/")
    aquests.fetchall ()
