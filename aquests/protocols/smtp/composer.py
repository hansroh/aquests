from email.base64mime import body_encode as encode_base64
try:
	from rfc822 import parseaddr
except ImportError:
	from email.utils import parseaddr
import pickle
import time, os
import mimetypes
from hashlib import md5
import shutil

class DefaultSMTPServer:
	server = None
	user = None
	password = None
	ssl = False

class Composer:
	SAVE_PATH = None
	def __init__ (self, subject, snd, rcpt):
		self.H = {}
		self.contents = []
		self.H ['MIME-Version'] = '1.0'
		self.H ['Date'] = self.rfc_date ()
		self.H ['X-Priority'] = '3'
		self.H ['X-Mailer'] = 'Skitai SMTP Delivery Agent'
		self.H ['Subject'] = subject.strip ()
		self.H ['From'] = self.snd = snd.strip ()
		self.H ['To'] = self.rcpt = rcpt.strip ()
		self.attachments = []
		self.content_map = {}
		self.smtp_server = None
		self.ssl = False
		self.login = None
		self.saved_name = None
		self.created_time = time.time ()
		self.retrys = 1

	def inc_retry (self):
		self.retrys += 1

	def set_smtp (self, server, user = None, password = None, ssl = False):
		try:
			s, p = server.split (":")
			p = int (p)
		except ValueError:
			s, p = server, 25
		self.smtp_server = (s, p)
		self.ssl = ssl
		if user and password:
			self.login = (user, password)

	def set_header (self, name, value):
		self.H [name] = value

	def rfc_date (self):
		return time.strftime ('%a, %d %b %Y %H:%M:%S -0000', time.gmtime (time.time ()))

	def parse_address (self, addr):
		try:
			return parseaddr(addr)
		except AttributeError:
			return ("", addr)

	def encode (self, data):
		return encode_base64 (data)

	def add_text (self, data, mimetype, charset = 'utf8'):
		self.add_content (data, mimetype, charset)

	def add_content (self, data, mimetype, charset = 'utf8'):
		msg = (
			"Content-type: %s; \r\n\tcharset=\"%s\"\r\n"
			"Content-Transfer-Encoding: base64\r\n"
			"\r\n" % (mimetype, charset)
			)
		msg += self.encode (data.encode ("utf8"))
		self.contents.append (msg)

	def add_attachment (self, filename, name = None, cid = None):
		if not name:
			name = os.path.split (filename) [-1]
		if cid:
			self.content_map [name] = cid
		self.attachments.append ((cid, name, filename, mimetypes.guess_type (filename) [0]))

	def encode_attachment (self, cid, name, data, mimetype):
		if cid:
			msg = (
			"Content-ID: <%s>\r\n"
			"Content-Disposition: inline; filename=\"%s\"\r\n"
			"X-Attachment-Id: %s\r\n"
			% (cid, name, cid)
		)

		else:
			msg = (
				"Content-Disposition: attachment; filename=\"%s\"\r\n" % name
			)

		msg += (
			"MIME-Version: 1.0\r\n"
			"Content-Type: %s; name=\"%s\"\r\n"
			"Content-transfer-encoding: base64\r\n"
			"\r\n" % (mimetype, name)
			)
		msg += self.encode (data)
		return msg

	def remove (self, fn = None):
		if fn is None:
			fn = self.get_FILENAME ()
		try: os.remove (fn)
		except FileNotFoundError: pass

	def moveto (self, path):
		old_path = self.get_FILENAME ()
		self.save (path)
		self.remove (old_path)

	def set_default_smtp (self):
		self.set_smtp (
			DefaultSMTPServer.server,
			DefaultSMTPServer.user,
			DefaultSMTPServer.password,
			DefaultSMTPServer.ssl
		)

	def save (self, path):
		if self.smtp_server is None:
			assert DefaultSMTPServer.server, "SMTP server is not specified"
			self.set_default_smtp ()

		while 1:
			d = md5 ((self.get_FROM () + self.get_TO () + str (time.time ())).encode ("utf8"))
			fn = os.path.join (path, "%d.%s" % (self.get_RETRYS (), d.hexdigest ().upper()))
			if not os.path.isfile (fn):
				self.saved_name = fn
				with open (fn, "wb") as f:
					pickle.dump (self, f)
				break

	def send (self):
		self.save (self.SAVE_PATH)

	def is_SSL (self):
		return self.ssl

	def get_CREATED_TIME (self):
		return self.created_time

	def get_TO (self):
		return self.parse_address (self.rcpt) [1]

	def get_FROM (self):
		return self.parse_address (self.snd) [1]

	def get_SMTP (self):
		return self.smtp_server

	def get_LOGIN (self):
		return self.login

	def get_RETRYS (self):
		return self.retrys - 1

	def get_FILENAME (self):
		return self.saved_name

	def get_DATA (self):
		body = "\r\n".join (["%s: %s" % (k, v) for k, v in self.H.items ()]) + "\r\n"

		if len (self.contents) == 0:
			raise AttributeError

		elif len (self.contents) == 1 and not self.attachments:
			body += self.contents [0]

		else:
			sndemail = self.get_FROM ()
			boundary = '__________' + sndemail.replace ('@', '_') + "_" + str (time.time ())
			body += "Content-type: multipart/mixed; \r\n\tboundary=\"%s\"\r\n\r\n" % boundary
			body += "This is a multi-part message in MIME format.\r\n\r\n"

			for cid, name, filename, mimetype in self.attachments:
				f = open (filename, "rb")
				data = f.read ()
				f.close ()
				self.contents.append (self.encode_attachment (cid, name, data, mimetype))

			for content in self.contents:
				body += "--%s\r\n%s\r\n\r\n" % (boundary, content)
			body += "--%s--\r\n" % boundary
		return body


def load (fn):
	with open (fn, "rb") as f:
		m = pickle.load (f)
	m.inc_retry ()
	return m

def set_default_smtp (server, user = None, password = None, ssl = False):
	DefaultSMTPServer.server = server
	DefaultSMTPServer.user = user
	DefaultSMTPServer.password = password
	DefaultSMTPServer.ssl = ssl


if __name__ == "__main__":
	data="""Hi,
I recieved your message today.

I promise your request is processed with very high priority.

Thanks.
	"""
	m = Composer ("e-Mail Test", '"Tester"<hansroh@xxx.com>', '"Hans Roh"<hansroh2@xxx.com>')
	m.set_smtp ("smtp.gmail.com:465", "ehmax@xxx.com", "password", True)
	m.add_content (data, "text/html", "utf8")
	m.add_attachment (r"d:/download/setup.py", cid="AAA")
	m.save (r"d:/download")

	load (m.get_FILENAME ())
	print (m.get_DATA ())
	print (m.get_FILENAME ())
	m.remove ()
