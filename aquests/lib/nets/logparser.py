import time

class OneLog:
	pass
	
class LogIIS:
	def parse (self, line):
		l = OneLog ()
		
		l.date, l.time, l.destip, l.cmd, info = line.split (" ", 4)
		l.script, l.querystring, l.port, l.something, info = info.split (" ", 4)
		info = info.split (" ")
		l.srcip = info [0]
		l.ver = info [1]
		l.code = info [-3]
		l.host = info [-4].split (":")[0]
		l.ua = " ".join (info [2:-4])		
		tpack = [int (x) for x in l.date.split ("-") + l.time.split (":")]
		tpack [3] += 9
		l.timeint = int (time.mktime (tuple (tpack) + (0,0,0)))
		return l


class LogSquidAccess:
	def parse (self, line):
		l = OneLog ()
		
		l.timeint = int (float (line [:14]))
		line = line [14:].strip ()
		o = line.split (" ")
		l.inputbytes = o [0]
		l.srcip = o [1]
		l.cachehit = o [2]
		l.outputbytes = o [3]
		l.cmd = o [4]
		l.uri = " ".join (o [5:-3])
		l.querystring = o [-3]
		l.destserver = o [-2]
		l.mimetype = o [-1]
				
		return l
	

if __name__ == "__main__":		
	f = LogSquidAccess ()
	l = f.parse ("1245538111.854   3094 211.172.253.204 TCP_MISS/200 46887 GET http://fedvendor.com/vendor_directory/index.htm? - FIRST_UP_PARENT/server_188 text/html")
	f = LogIIS ()
	l = f.parse ("2009-06-20 14:59:16 192.168.1.188 GET /governmentbid-education-higher-statistics-E01032.htm - 80 - 192.168.1.185 HTTP/1.0 Mozilla/5.0+(compatible;+DotBot/1.1;+http://www.dotnetdotcom.org/,+crawler@dotnetdotcom.org) www.govcb.com 200 0 2")
	for k in dir (l):
		print(k, eval ("l." + k))

