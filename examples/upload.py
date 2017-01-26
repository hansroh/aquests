import aquests

formdata = {
	'submit-name': 'Hans Roh', 
	"file1": open (r"D:\IDCs\serversoftwares\Coldfusion5\ClusterCATS-5.1-w32.exe", "rb")
}
	
aquests.configure (10)
for i in range (100):
	aquests.upload ("http://127.0.0.1:5000/upload", formdata)
aquests.fetchall ()

