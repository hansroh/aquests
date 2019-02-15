import aquests

def test_get_https ():
    aquests.configure (force_http1 = 1)
    aquests.get ("https://www.facebook.com/")
    aquests.fetchall ()
    
    aquests.configure (force_http1 = 0)
    aquests.get ("https://www.facebook.com/")
    aquests.fetchall ()
    
