from aquests.lib import siesta

def test_sieta ():
	api = siesta.API ('http://127.0.0.1:5000/v1')
	resp = api.delune ("rfp-content").guess.get (q = "construction")
	print (resp.status_code, resp.reason, resp.data)
	
if __name__ == "__main__":
	test_sieta ()
