import aquests

def request_finished (r):
	print (r.lxml)

aquests.configure (1, callback = request_finished)	
aquests.get ("https://gitlab.com/hansroh")
aquests.fetchall ()
