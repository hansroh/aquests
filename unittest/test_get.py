import unittest
import aquests

SERVER = "http://127.0.0.1:5000"

class MyTest (unittest.TestCase):
	def setUp (self):
		self.__fetchcount = 0
		
	def equal200 (self, response):
		self.assertEqual (response.status_code, 200)
	
	def equal404 (self, response):
		self.assertEqual (response.status_code, 404)
		
	def nequal200 (self, response):
		self.assertNotEqual (response.status_code, 200)
		
	def ver11 (self, response):
		self.assertEqual (response.version, "1.1")	
	
	def ver20 (self, response):
		self.assertEqual (response.version, "2.0")	
	
	def increase (self, response):
		self.__fetchcount += 1
	
	def checkout (self):
		r = self.__fetchcount
		self.__fetchcount = 0
		return r
				
	def test_1 (self):			
		aquests.configure (1, callback = self.equal200)
		aquests.get (SERVER)
		aquests.fetchall ()
	
	def test_2 (self):			
		aquests.configure (1, callback = self.ver20)
		aquests.get (SERVER)
		aquests.fetchall ()
			
	def test_3 (self):			
		aquests.configure (1, callback = self.ver11, force_http1 = True)
		aquests.get (SERVER)
		aquests.fetchall ()
		
	def test_4 (self):	
		munreq = 1000
		aquests.configure (1, callback = self.increase, force_http1 = True)
		for i in range (munreq):
			aquests.get (SERVER)
		aquests.fetchall ()
		self.assertEqual (self.checkout (), munreq)			
	
	def test_5 (self):	
		munreq = 1000				
		aquests.configure (1, callback = self.increase, http2_constreams = 10)
		for i in range (munreq):
			aquests.get (SERVER)
		aquests.fetchall ()
		self.assertEqual (self.checkout (), munreq)
	
	def test_6 (self):			
		aquests.configure (1, callback = self.equal404)
		aquests.get (SERVER + "/no-page")
		aquests.fetchall ()
	
	def test_7 (self):			
		aquests.configure (1, callback = self.equal404, force_http1 = True)
		aquests.get (SERVER + "/no-page")
		aquests.fetchall ()
	
	def test_8 (self):	
		munreq = 3000
		aquests.configure (10, callback = self.increase, force_http1 = True)
		for i in range (munreq):
			aquests.get (SERVER)
		aquests.fetchall ()
		self.assertEqual (self.checkout (), munreq)			
	
	def test_9 (self):	
		munreq = 3000				
		aquests.configure (2, callback = self.increase, http2_constreams = 5)
		for i in range (munreq):
			aquests.get (SERVER)
		aquests.fetchall ()
		self.assertEqual (self.checkout (), munreq)
	
	def test_10 (self):			
		aquests.configure (1, callback = self.equal404)
		for i in range (10):
			aquests.get (SERVER + "/no-page")
		aquests.fetchall ()
	
	def test_11 (self):			
		aquests.configure (1, callback = self.equal404, force_http1 = True)
		for i in range (10):	
			aquests.get (SERVER + "/no-page")
		aquests.fetchall ()
		

if __name__ == "__main__":
	TS = unittest.makeSuite(MyTest, "test")
	runner = unittest.TextTestRunner()
	runner.run(TS)
	