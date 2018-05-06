import time
from datetime import datetime

class Timer:
	def __init__ (self):		
		self.jobs = {}
		self.lastest = ''
		self.created = time.time ()
		self._begun = False
		
	def begin (self, name = 'job'):
		assert not self._begun
		self._begun = True
		self.s = time.time ()
		self.jobs [name] = time.time ()
		self.lastest = name
		print ('* Started {}'.format (name))
		
	def finish (self, tail = '', name = ''):
		assert self._begun
		self._begun = False
		jobname = name or self.lastest
		due = time.time () - self.jobs [jobname]
		print ('* Finished {} for {:2.4f} seconds{}'.format (jobname, due, tail and ', ' + tail or ''))
		self.s = time.time ()
		self.lastest = ''
		
	
	def close (self):
		due = time.time () - self.created
		print ('-------------------')
		print ('* Finished script for {:2.4f} seconds'.format (due))


class Timer2:
	def __init__ (self):
		self.stime = 0
		
	def begin (self):
		self.stime = datetime.now ()
	
	def finish (self, n = 0):
		diff = datetime.now () - self.stime
		print ('Duration: {}'.format (diff))
		if n:
			sec = diff.seconds + (diff.microseconds / 1000000)
			print ('Speed: {:.3f} IPS'.format (n / sec))
		    
if __name__ == "__main__":
    detect ('face560x840.jpg', 100)
    detect ('face250x250.jpg', 100)
    

		