from rs4 import asyncore, asynchat
import re, socket, sys
from ..client.asynlib import asyncon
import collections

# get port number from pasv response
pasv_pattern = re.compile("[-\d]+,[-\d]+,[-\d]+,[-\d]+,([-\d]+),([-\d]+)")

class asyncftp(asyncon.asyncon):
	def __init__(self, handler):
		asyncon.asyncon.__init__(self, handler)
		
		self.set_terminator(b"\n")
		self.data = ""
		self.response = []
		
		self.commands = [
			"PASV", self.ftp_handle_pasv_response,
			"RETR %s" % self.handler.get_remote_path (),
			"QUIT",
		]
		
		self.conhdr = self.ftp_handle_connect
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)		

	def handle_connect(self):
		pass

	def handle_expt(self):
		self.close()

	def collect_incoming_data(self, data):
		self.data = self.data + data

	def found_terminator(self):
		data = self.data
		if data.endswith("\r"):
			data = data[:-1]
		self.data = ""
		self.response.append(data)
		if not re.match("\d\d\d ", data):
			return

		response = self.response
		self.response = []

		#for line in response:
		#	print "S:", line

		# process response
		if self.conhdr:
			# call the response handler
			handler = self.conhdr
			self.conhdr = None

			handler(response)

			if self.conhdr:
				return # follow-up command in progress

		# send next command from queue
		try:
			command = self.commands.pop(0)
			if self.commands and isinstance(self.commands[0], collections.Callable):
				self.conhdr = self.commands.pop(0)
			#print "C:", command
			self.push(command + "\r\n")
		except IndexError:
			pass

	def ftp_handle_connect(self, response):
		code = response[-1][:3] # get response code
		if code == "220":
			self.push("USER " + self.handler.get_user () + "\r\n")
			self.conhdr = self.ftp_handle_user_response
		else:
			raise Exception("ftp login failed")

	def ftp_handle_user_response(self, response):
		code = response[-1][:3]
		if code == "230":
			return # user accepted
		elif code == "331" or code == "332":
			self.push("PASS " + self.handler.get_password () + "\r\n")
			self.conhdr = self.ftp_handle_pass_response
		else:
			raise Exception("ftp login failed: user name not accepted")

	def ftp_handle_pass_response(self, response):
		code = response[-1][:3]
		if code == "230":
			return # user and password accepted
		else:
			raise Exception("ftp login failed: user/password not accepted")

	def ftp_handle_pasv_response(self, response):
		code = response[-1][:3]
		if code != "227":
			return # pasv failed
		match = pasv_pattern.search(response[-1])
		if not match:
			return # bad port
		p1, p2 = match.groups()
		try:
			port = (int(p1) & 255) * 256 + (int(p2) & 255)
		except ValueError:
			return # bad port
		
		# establish data connection
		self.handler.handle_establish_connection (self.host, port)
		

class asyncftp_download(asyncore.dispatcher):
	def __init__(self, host, port):
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.connect((host, port))

	def writable(self):
		return 0

	def handle_connect(self):
		pass

	def handle_expt(self):
		self.close()

	def handle_read(self):
		sys.stdout.write(self.recv(8192))

	def handle_close(self):
		self.close()
		

