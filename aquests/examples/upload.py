import aquests

formdata = {
	'submit-name': 'Hans Roh', 
	"file1": open (r"D:\download\Jack.Reacher.2012.1080p.BluRay.H264.AAC-RARBG.smi", "rb")
}
	
aquests.configure (10)
for i in range (100):
	aquests.upload ("http://127.0.0.1:5000/test/up", formdata)
aquests.fetchall ()

