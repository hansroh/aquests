r"""
D:\apps\skitai\skitai\protocol\smtp>D:\apps\xlmail\lib\sendlufex.py
send: 'ehlo [127.0.0.1]\r\n'
reply: '250-smtp.gmail.com at your service, [xx.xx.xx.xx]\r\n'
reply: '250-SIZE 35882577\r\n'
reply: '250-8BITMIME\r\n'
reply: '250-AUTH LOGIN PLAIN XOAUTH2 PLAIN-CLIENTTOKEN OAUTHBEARER XOAUTH\r\n'
reply: '250-ENHANCEDSTATUSCODES\r\n'
reply: '250-PIPELINING\r\n'
reply: '250-CHUNKING\r\n'
reply: '250 SMTPUTF8\r\n'
reply: retcode (250); Msg: smtp.gmail.com at your service, [14.33.246.211]
send: 'AUTH PLAIN RGDSsdRRO=\r\n'
reply: '235 2.7.0 Accepted\r\n'
reply: retcode (235); Msg: 2.7.0 Accepted
send: 'mail FROM:<test@abc.com> size=370\r\n'
reply: '250 2.1.0 OK lg14sm30993621pab.45 - gsmtp\r\n'
reply: retcode (250); Msg: 2.1.0 OK lg14sm30993621pab.45 - gsmtp
send: 'rcpt TO:<hhh@gmail.com>\r\n'
reply: '250 2.1.5 OK lg14sm30993621pab.45 - gsmtp\r\n'
reply: retcode (250); Msg: 2.1.5 OK lg14sm30993621pab.45 - gsmtp
send: 'data\r\n'
reply: '354  Go ahead lg14sm30993621pab.45 - gsmtp\r\n'
reply: retcode (354); Msg: Go ahead lg14sm30993621pab.45 - gsmtp
data: (354, 'Go ahead lg14sm30993621pab.45 - gsmtp')
send: 'Date: Fri, 27 Nov 2015 12:47:42 +0900\r\nTo: Hans Roh <hhh@gmail.com>
\r\nSubject: e-Mail Test\r\nFrom: Tester <test@abc.com>\r\nMIME-Version:
1.0\r\nContent-type: text/html; \r\n\tcharset="UTF-8"\r\nContent-Transfer-Encodi
ng: quoted-printable\r\n\r\n<h1>Hi</h1>,=20\r\nI recieved your message today.\r\
nI promise your request is processed with very high priority.\r\n<p>\r\nThanks.\
r\n</p>\r\n=09\r\n.\r\n'
reply: '250 2.0.0 OK 1448596061 lg14sm30993621pab.45 - gsmtp\r\n'
reply: retcode (250); Msg: 2.0.0 OK 1448596061 lg14sm30993621pab.45 - gsmtp
data: (250, '2.0.0 OK 1448596061 lg14sm30993621pab.45 - gsmtp')
send: 'quit\r\n'
reply: '221 2.0.0 closing connection lg14sm30993621pab.45 - gsmtp\r\n'
reply: retcode (221); Msg: 2.0.0 closing connection lg14sm30993621pab.45 - gsmtp
"""

from rs4 import asynchat, asyncore
import re, sys, time
import base64, hmac
import socket, ssl

try:
	from rfc822 import parseaddr
except ImportError:
	from email.utils import parseaddr
from email.base64mime import body_encode as encode_base64
from . import composer
from rs4 import producers

OLDSTYLE_AUTH = re.compile(r"auth=(.*)", re.I)
FEATURE = re.compile (r'(?P<feature>[A-Za-z0-9][A-Za-z0-9\-]*)')
CRLF = b"\r\n"

def quoteaddr(addr):
	m = (None, None)
	try:
		m=parseaddr(addr)[1]
	except AttributeError:
		pass
	if m == (None, None):
		return "<%s>" % addr
	else:
		return "<%s>" % m

def quotedata(data):
	return re.sub (r'(?m)^\.', '..',
		re.sub(r'(?:\r\n|\n|\r(?!\n))', "\r\n", data))
				

class SMTP (asynchat.async_chat):
	zombie_timeout = 120
	debug = False
	
	def __init__(self, composer, logger = None, callback = None):
		self.composer = composer						
		self.callback = callback
		self.logger = logger
		
		self.__line = []
		self.__mline = []
		self.__code = 900
		self.__resp = "Connection Failed"
		self.__stat = 0		
		self.__sent = 0
		self.__panic = 0
		self.does_esmtp = 1
		self.esmtp_features = {}
		self.is_esmtp = True
		self.event_time = time.time ()
		
		asynchat.async_chat.__init__(self)		
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
		self.set_terminator (CRLF)		
		self.sendmail ()
	
	def connect (self, adrr):
		self.event_time = time.time ()
		asynchat.async_chat.connect (self, adrr)
			
	def get_time (self):
		return self.event_time
		
	def push (self, msg):
		if self.debug: print ("SEND:", msg)	
		asynchat.async_chat.push(self, (msg + '\r\n').encode ("utf8"))
	
	def trace (self):	
		return self.logger.trace ("%s -> %s" % (self.composer.snd, self.composer.rcpt))
	
	def log (self, msg, lt = "info"):
		self.logger ("[%s] %s %s -> %s (%1.1f Kb)" % (lt, msg, self.composer.snd, self.composer.rcpt, self.__sent / 1024))
		
	def sendmail (self):
		try:
			host, port = self.composer.get_SMTP ()
			self.connect ((host, port))
			self.address = host			
		except:
			self.handle_error ()		
	
	def collect_incoming_data (self, data):
		if self.debug: print ("RECV:", data.decode ("utf8"))
		self.__line.append(data.decode ("utf8"))
	
	def get_reply (self, line):
		code = line [:3]		
		try:
			code = int (code)
			resp = line [4:]
		except:	
			code = -1
			resp = ""		
		return code, resp
	
	def has_extn(self, opt):
		return opt.lower() in self.esmtp_features
	
	def send_from (self):
		if self.is_esmtp and self.does_esmtp and self.has_extn('size'):
			option = "size=" + repr(len(self.composer.get_DATA ()))
			self.push ("mail FROM:%s %s" % (quoteaddr (self.composer.get_FROM ()), option))
		else:
			self.push ("mail FROM:%s" % (quoteaddr (self.composer.get_FROM ())))
	
	def login (self, phase = 1, resp = None):		
		def encode_cram_md5(challenge, user, password):
			challenge = base64.decodebytes(challenge)
			response = user + " " + hmac.HMAC(password.encode('ascii'),
											challenge, 'md5').hexdigest()
			return encode_base64(response.encode('ascii'), eol='')
	
		def encode_plain(user, password):
			s = "\0%s\0%s" % (user, password)
			return encode_base64(s.encode('ascii'), eol='')
		
		try:
			advertised_authlist = self.esmtp_features["auth"].split()		
		except KeyError:
			advertised_authlist = []	
		user, password = self.composer.get_LOGIN ()
		
		AUTH_PLAIN = "PLAIN"
		AUTH_CRAM_MD5 = "CRAM-MD5"
		AUTH_LOGIN = "LOGIN"

		preferred_auths = [AUTH_CRAM_MD5, AUTH_PLAIN, AUTH_LOGIN]		
		authlist = [auth for auth in preferred_auths if auth in advertised_authlist]
		if not authlist:
			self.__code, self.__resp = 900, "No Suitable Authentication Method"			
			self.__stat = 9
			self.push ("rset")
			return
		
		if AUTH_PLAIN in authlist:
			self.push ("AUTH %s %s" % (AUTH_PLAIN, encode_plain (user, password)))
			self.__stat = 3
			
		elif AUTH_LOGIN in authlist:
			if phase == 1:
				self.push ("AUTH %s %s" % (AUTH_LOGIN, encode_base64(user.encode('ascii'), eol='')))
				self.__stat = 2.5
			else:
				self.push (encode_base64(password.encode('ascii'), eol=''))	
				self.__stat = 3
			
		else:
			if phase == 1:
				self.push ("AUTH %s" % (AUTH_CRAM_MD5,))
				self.__stat = 2.5
			else:	
				self.push (encode_cram_md5 (resp, user, password))
				self.__stat = 3
						
	def found_terminator(self):
		line = "".join(self.__line)
		self.__line = []				
		
		code, _resp = self.get_reply (line)
		
		if code == -1:
			self.__code, self.__resp = 801, "SMTP Server Response Error"
			self.close ()
			return
			
		self.__mline.append (_resp)
		
		if line [3:4] == "-":
			return
			
		else:
			for each in self.__mline [1:]:
				auth_match = OLDSTYLE_AUTH.match(each)
				if auth_match:
					self.esmtp_features["auth"] = self.esmtp_features.get("auth", "") \
							+ " " + auth_match.groups(0)[0]
					if self.debug: print (self.esmtp_features)
					continue
	
				m=FEATURE.match(each)
				if m:
					feature=m.group("feature").lower()
					params=m.string[m.end("feature"):].strip()
					if feature == "auth":
						self.esmtp_features[feature] = self.esmtp_features.get(feature, "") \
								+ " " + params
					else:
						self.esmtp_features[feature]=params
			
			resp = " ".join (self.__mline)
			self.__mline = []
		
		if self.__stat == 0:
			if code != 220:
				self.__code, self.__resp = code, resp
				self.__stat = 9
				self.push ("quit")
				return
			self.__stat = 1
			self.push ("ehlo %s" % socket.getfqdn())
		
		elif self.__stat == 1:
			if not (200 <= code <= 299):
				self.__code, self.__resp = code, resp
				self.__stat = 2
				self.is_esmtp = False
				self.push ("helo %s" % socket.getfqdn())
				return
			
			if self.composer.get_LOGIN ():
				self.login ()
							
			else:
				self.__stat = 4
				self.send_from ()

		elif self.__stat == 2:	
			if not (200 <= code <= 299):
				self.__code, self.__resp = code, resp
				self.__stat = 10 # not SMTP, close immediatly
				return
			self.__stat = 4
			self.send_from ()
		
		elif self.__stat == 2.5:
			if code != 334:
				self.__code, self.__resp = code, resp
				self.__stat = 9
				self.push ("rset")
				return
			self.login (2, resp)
			
		elif self.__stat == 3:
			if code not in (235, 503):
				self.__code, self.__resp = code, resp
				self.__stat = 9
				self.push ("rset")
				return
			self.__stat = 4
			self.send_from ()
				
		elif self.__stat == 4:
			if not (200 <= code <= 299):
				self.__code, self.__resp = code, resp
				self.__stat = 9
				self.push ("rset")
				return				
			self.__stat = 5
			self.push ("rcpt TO:%s" % quoteaddr (self.composer.get_TO ()))
			
		elif self.__stat == 5:
			if not (250 <= code <= 251):				
				self.__code, self.__resp = code, resp
				self.__stat = 9
				self.push ("rset")
				return
			self.__stat = 6
			self.push ("data")
		
		elif self.__stat == 6:
			if code != 354:
				self.__code, self.__resp = code, resp
				self.__stat = 9
				self.push ("rset")
				return
			self.__stat = 9
			
			q = quotedata (self.composer.get_DATA ()) + ".\r\n"
			self.push_with_producer (producers.simple_producer (q.encode ("utf8")))
			#self.push (q.encode ("utf8"))
			self.__sent = len (q)
				
		elif self.__stat == 9:
			if self.__sent and code == 250:
				self.__code, self.__resp = -250, "OK"
			elif self.__sent:
				self.__code, self.__resp = code, resp								
			self.__stat = 10
			self.push ("quit")
			
		else:			
			self.handle_close ()	
	
	def clean_shutdown_control (self, phase, time_in_this_phase):
		if phase == 3:
			if self._stat < 99 or self.writable ():
				return 1
			return 0
	
	def handle_connect (self):
		self.event_time = time.time ()
	
	def close (self):
		self.log ("%s %s" % (self.__code, self.__resp), self.__code == -250 and "info" or "fail")
		if self.callback:
			self.callback (self.composer, self.__code, self.__resp)		
		asynchat.async_chat.close (self)
		self.__stat = 99
		
	def handle_error (self):
		self.trace ()
		self.__code = 900
		self.__resp = asyncore.compact_traceback() [1].__name__
		self.close()
	
	def handle_close (self):
		self.close()
			
	def handle_expt (self):
		self.__panic += 1
		if self.__panic > 3:		
			self.__code = 802
			self.__resp = "Socket panic"
			self.close ()
	
	def handle_read (self):
		self.event_time = time.time ()
		return asynchat.async_chat.handle_read (self)

	def handle_write(self):
		self.event_time = time.time ()
		return asynchat.async_chat.handle_write (self)
    
	def handle_timeout (self):
		self.__code, self.__resp = 800, "Timeout"
		self.close ()
		

class SMTP_SSL (SMTP):
	def connect (self, addr):
		self.handshaking = False
		SMTP.connect (self, addr)
					
	def handle_connect_event(self):
		if not self.handshaking:
			err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
			if err != 0:
				raise socket.error(err, _strerror(err))
				
			self.socket = ssl.wrap_socket (self.socket, do_handshake_on_connect = False)			
			self.handshaking = True
			
		try:
			self.socket.do_handshake ()
		except ssl.SSLError as why:
			if why.args[0] in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):
				return # retry handshake
			raise ssl.SSLError(why)
		
		# handshaking done
		self.handle_connect()
		self.connected = True
		
	def recv (self, buffer_size):
		self.event_time = time.time ()
		try:
			data = self.socket.recv (buffer_size)
			if not data:
				self.handle_close ()
				return b''
			else:
				return data

		except ssl.SSLError as why:
			if why.errno == ssl.SSL_ERROR_WANT_READ:
				return b'' # retry
			# closed connection
			elif why.errno == ssl.SSL_ERROR_EOF:
				self.log ("SSL_ERROR_EOF Error Occurred in recv ()", "warn")				
				self.handle_close ()
				return b''
			else:
				raise

	def send (self, data):
		self.event_time = time.time ()
		try:
			return self.socket.send(data)

		except ssl.SSLError as why:
			if why.errno == ssl.SSL_ERROR_WANT_WRITE:
				return 0			
			else:
				raise
	

if __name__ == "__main__":		
	from rs4 import logger
	from skitai import lifetime
	
	log = logger.screen_logger ()
	m = composer.Composer ("smtp.gmail.com:587", "", "")
	m.add_content ("Hello World<div><img src='cid:A'></div>", "text/html")
	#m.add_attachment (r"1.png", cid="A")
	
	for i in range (1):
		SMTP_SSL (m, log)
		
	asyncore.loop ()
	
	

