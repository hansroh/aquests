#! /usr/bin/python3

import aquests
import os, sys

def request_finished_and_req (r):
	global TOTAL, DONE
	DONE += 1
	if (DONE + len (aquests._currents)) < TOTAL:
		aquests.get (r.url)
	args = (r.status_code, r.reason, len (r.content))
	print ("%s %s %d bytes received" % args, r.version)

def request_finished (r):
	args = (r.status_code, r.reason, len (r.content))
	print ("%s %s %d bytes received" % args, r.version)


def make_example_testset ():
	#jpg = open (os.path.join (r"D:\apps\skitai\tests\examples", "statics", "reindeer.jpg"), "rb")	
	#aquests.upload ("http://127.0.0.1:5000/upload", {"username": "pytest", "file1": jpg})		
	#aquests.get ("http://127.0.0.1:5000/")	
	#aquests.get ("http://127.0.0.1:5000/members/", auth = ('admin', '1111'))
	#aquests.get ("http://127.0.0.1:5000/redirect1")	
	#aquests.rpc ("http://127.0.0.1:5000/rpc2/").add_number (1, 2)	
	aquests.ws ("ws://127.0.0.1:5000/websocket/echo-single", "Hello Skitai")
	
def test_load (h1, client, streams, urls):
	if urls == 1:
		aquests.configure (client, callback = request_finished, force_http1 = h1, http2_constreams = streams)
		for i in range (TOTAL):
			make_example_testset ()				
	else:
		aquests.configure (client, callback = request_finished_and_req, force_http1 = h1, http2_constreams = streams)			
		for i in range (client * streams):
			for url in urls:
				aquests.get (url)

	aquests.fetchall ()


if __name__ == "__main__":
	import getopt, time
	argopt = getopt.getopt(sys.argv[1:], "en:c:m:", ["h1"])
	
	h1 = 0
	num = 1
	client = 1
	streams = 1
	test_example = 0
	TOTAL = 0
	DONE = 0
	for k, v in argopt [0]:
		if k == "--h1":
			h1 = 1
		elif k == "-n":
			TOTAL = int (v)
		elif k == "-c":
			client = int (v)
		elif k == "-m":
			streams = int (v)
		elif k == "-e":	
			test_example = 1
			
	test_load (h1, min (client, TOTAL), streams, test_example or argopt [1])
	