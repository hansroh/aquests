import time

class Timer:
	def __init__ (self):		
		self.jobs = {}
		self.lastest = ''
		self.created = time.time ()
		self.begin ()
	
	def begin (self, name = 'job'):
		self.s = time.time ()
		self.jobs [name] = time.time ()
		self.lastest = name
		
	def finish (self, tail = '', name = ''):
		jobname = name or self.lastest
		due = time.time () - self.jobs [jobname]
		print ('* Finished {} for {:2.4f} seconds{}'.format (jobname, due, tail and ', ' + tail or ''))
		self.s = time.time ()
	
	def close (self):
		due = time.time () - self.created
		print ('-------------------')
		print ('* Finished script for {:2.4f} seconds'.format (due))
		