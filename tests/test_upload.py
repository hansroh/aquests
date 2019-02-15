import aquests

def test_upload ():
	formdata = {
		'submit-name': 'Hans Roh', 
		"file1": open ("./README.txt", "rb")
	}
		
	aquests.configure (10)
	for i in range (100):
		aquests.upload ("http://127.0.0.1:5000/upload", formdata)
	aquests.fetchall ()
	
