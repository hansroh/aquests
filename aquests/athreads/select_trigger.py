# -*- Mode: Python; tab-width: 4 -*-

VERSION_STRING = "$Id: select_trigger.py,v 1.11 1999/07/27 00:05:21 rushing Exp $"

import asyncore
import asynchat

import os
import socket
import string
try:
	import _thread
except ImportError:
	import thread as _thread
	
if os.name == 'posix':

	class trigger (asyncore.file_dispatcher):
		"Wake up a call to select() running in the main thread"

		# This is useful in a context where you are using Medusa's I/O
		# subsystem to deliver data, but the data is generated by another
		# thread.  Normally, if Medusa is in the middle of a call to
		# select(), new output data generated by another thread will have
		# to sit until the call to select() either times out or returns.
		# If the trigger is 'pulled' by another thread, it should immediately
		# generate a READ event on the trigger object, which will force the
		# select() invocation to return.

		# A common use for this facility: letting Medusa manage I/O for a
		# large number of connections; but routing each request through a
		# thread chosen from a fixed-size thread pool.  When a thread is
		# acquired, a transaction is performed, but output data is
		# accumulated into buffers that will be emptied more efficiently
		# by Medusa. [picture a server that can process database queries
		# rapidly, but doesn't want to tie up threads waiting to send data
		# to low-bandwidth connections]

		# The other major feature provided by this class is the ability to
		# move work back into the main thread: if you call pull_trigger()
		# with a thunk argument, when select() wakes up and receives the
		# event it will call your thunk from within that thread.  The main
		# purpose of this is to remove the need to wrap thread locks around
		# Medusa's data structures, which normally do not need them.  [To see
		# why this is true, imagine this scenario: A thread tries to push some
		# new data onto a channel's outgoing data queue at the same time that
		# the main thread is trying to remove some]

		def __init__ (self, logger = None):
			r, w = os.pipe()
			self.trigger = w
			self.logger = logger
			asyncore.file_dispatcher.__init__ (self, r)
			self.lock = _thread.allocate_lock()
			self.thunks = []

		def __repr__ (self):
			return '<select-trigger (pipe) at %x>' % id(self)

		def readable (self):
			return 1

		def writable (self):
			return 0

		def handle_connect (self):
			pass

		def pull_trigger (self, thunk=None):
			# print 'PULL_TRIGGER: ', len(self.thunks)
			if thunk:
				try:
					self.lock.acquire()
					self.thunks.append (thunk)
				finally:
					self.lock.release()
			os.write (self.trigger, b'x')			
			
		def handle_read (self):			
			self.recv (8192)
			try:
				self.lock.acquire()				
				for thunk in self.thunks:
					try:						
						thunk()
					except:
						if self.logger:
							self.logger.trace ('the_trigger')
				self.thunks = []
								
			finally:
				self.lock.release()

else:

	# win32-safe version

	class trigger (asyncore.dispatcher):
		address = ('127.9.9.9', 19999)
		def __init__ (self, logger = None):
			self.logger = logger
			sock_class = socket.socket
			a = sock_class (socket.AF_INET, socket.SOCK_STREAM)
			w = sock_class (socket.AF_INET, socket.SOCK_STREAM)
			
			try:
				a.setsockopt(
					socket.SOL_SOCKET, socket.SO_REUSEADDR,
					a.getsockopt(socket.SOL_SOCKET,
										   socket.SO_REUSEADDR) | 1
					)
			except socket.error:
				pass
				
			# tricky: get a pair of connected sockets
			a.bind (self.address)
			a.listen (1)
			w.setblocking (0)
			try:
				w.connect (self.address)
			except:
				pass
				
			r, addr = a.accept()
			a.close()
			w.setblocking (1)
			self.trigger = w

			asyncore.dispatcher.__init__ (self, r)
			self.lock = _thread.allocate_lock()
			self.thunks = []
			self._trigger_connected = 0

		def __repr__ (self):
			return '<select-trigger (loopback) at %x>' % id(self)

		def readable (self):
			return 1

		def writable (self):
			return 0

		def handle_connect (self):
			pass

		def pull_trigger (self, thunk=None):
			if thunk:
				try:
					self.lock.acquire()
					self.thunks.append (thunk)
				finally:
					self.lock.release()
			self.trigger.send (b'x')

		def handle_read (self):
			self.recv (8192)			
			try:
				self.lock.acquire()				
				for thunk in self.thunks:
					try:
						thunk ()
					except:
						if self.logger:
							self.logger.trace ('the_trigger')
				self.thunks = []
				
			finally:
				self.lock.release()

if __name__ == '__main__':
	
	import time

	def thread_function (output_file, i, n):
		print('entering thread_function')
		while n:
			time.sleep (5)
			output_file.write ('%2d.%2d %s\r\n' % (i, n, output_file))
			output_file.flush()
			n = n - 1
		output_file.close()
		print('exiting thread_function')

	class thread_parent (asynchat.async_chat):
		
		def __init__ (self, conn, addr):
			self.addr = addr
			asynchat.async_chat.__init__ (self, conn)
			self.set_terminator (b'\r\n')
			self.buffer = ''
			self.count = 0

		def collect_incoming_data (self, data):
			self.buffer = self.buffer + data

		def found_terminator (self):
			data, self.buffer = self.buffer, ''
			if not data:
				asyncore.close_all()
				print("done")
				return
			n = string.atoi (string.split (data)[0])
			tf = trigger_file (self)
			self.count = self.count + 1
			_thread.start_new_thread (thread_function, (tf, self.count, n))

	class thread_server (asyncore.dispatcher):
		
		def __init__ (self, family=socket.AF_INET, address=('', 9003)):
			asyncore.dispatcher.__init__ (self)
			self.create_socket (family, socket.SOCK_STREAM)
			self.set_reuse_addr()
			self.bind (address)
			self.listen (5)

		def handle_accept (self):
			conn, addr = self.accept()
			tp = thread_parent (conn, addr)

	thread_server()
	#asyncore.loop(1.0, use_poll=1)
	try:
		asyncore.loop ()
	except:
		asyncore.close_all()