#! /usr/bin/python3

import aquests
import os, sys
import time

TOTAL = 0
DONE = 0
def request_finished_and_req (r):
	global TOTAL, DONE
	
	DONE += 1
	if TOTAL >= 10 and DONE % int (TOTAL / 10) == 0:
		aquests.log ("progress: {:.0f}%".format (DONE / TOTAL * 100))
		
	args = (r.status_code, r.reason, len (r.content))
	#print ("%s %s %d bytes received" % args, r.version)
	if (DONE + len(aquests._currents) + aquests.qsize ()) < TOTAL:
		aquests.get (r.url)

def request_finished (r):
	args = (r.status_code, r.reason, len (r.content))
	print ("%s %s %d bytes received" % args, r.version)

def make_example_testset ():
	if os.path.isfile (r"D:\apps\skitai\tests\examples"):
		jpg = open (os.path.join (r"D:\apps\skitai\tests\examples", "statics", "reindeer.jpg"), "rb")	
		aquests.upload ("http://127.0.0.1:5000/upload", {"username": "pytest", "file1": jpg})		
	aquests.get ("http://127.0.0.1:5000/")	
	aquests.get ("http://127.0.0.1:5000/members/", auth = ('admin', '1111'))
	aquests.get ("http://127.0.0.1:5000/redirect1")	
	aquests.rpc ("http://127.0.0.1:5000/rpc2/").add_number (1, 2)	
	aquests.ws ("ws://127.0.0.1:5000/websocket/echo-single", "Hello Skitai")
	
def test_load (h1, client, streams, urls):
	if urls == 1:
		aquests.configure (client, callback = request_finished, force_http1 = h1, http2_constreams = streams)
		for i in range (TOTAL):
			make_example_testset ()				
	else:
		aquests.configure (client, callback = request_finished_and_req, force_http1 = h1, http2_constreams = streams, backend = True)			
		for i in range (client * streams):
			for url in urls:
				aquests.get (url)
	aquests.fetchall ()

def usage ():
	print ("""
python -m aquests.load [options] urls
ex) python -m aquests.load -n 100 -c2 -m2 http://yourserver.com

options:
  
  -n: number of requests
  -c: number of clients
  -m: numner of HTTP2 concurent streams
  --h1: use force HTTP/1.1 request, -m option will be ignored  
	""")
	sys.exit ()

def main ():
	global TOTAL
	
	import getopt, time
	argopt = getopt.getopt(sys.argv[1:], "en:c:m:", ["h1", "help"])
	
	h1 = 0
	num = 1
	client = 1
	streams = 1
	test_example = 0
	for k, v in argopt [0]:
		if k == "--h1":
			h1 = 1
		elif k == "--help":
			usage ()
		elif k == "-n":
			TOTAL = int (v)
		elif k == "-c":
			client = int (v)
		elif k == "-m":
			streams = int (v)
		elif k == "-e":	
			test_example = 1
			
	test_load (h1, min (client, TOTAL), streams, test_example or argopt [1])
	print ("---")
	aquests.result.report ()
	
	
if __name__ == "__main__":
	main ()
	