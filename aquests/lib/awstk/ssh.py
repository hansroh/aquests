import time
import boto.ec2
from boto.manage.cmdshell import sshclient_from_instance
from . import iquery

class SSH:
	def __init__ (self, instance_id, key_path, user_name = "ubuntu"):
		self.instance_id = instance_id
		self.instance = iquery.get_instance_by_id (instance_id)
		self.ssh_client = sshclient_from_instance(self.instance, key_path, user_name = user_name)
		self.lines = []
	
	def __execute (self, cmd):	
		status, stdout, stderr = self.ssh_client.run (cmd)
		output = stderr.decode ('utf8') + stdout.decode ('utf8')
		if status != 0:
			raise SystemError (output)
		return output	
		
	def run (self):
		self.lines.insert (0, 'cat > .boto.sh << EOF\n#!/bin/bash')
		self.lines.append ('EOF')
		self.__execute ("\n".join (self.lines))
		self.lines = []
		return self.__execute ('chmod 755 .boto.sh && ./.boto.sh')
			
	def add (self, cmd):
		self.lines.append (cmd)

def get_shell_client (instance_id, key_path):
	return SSH (instance_id, key_path)
	