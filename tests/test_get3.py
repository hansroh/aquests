import unittest
import aquests

SERVER = "http://127.0.0.1:5000"

def setUp ():
    __fetchcount = 0
    
def equal200 (response):
    assertEqual (response.status_code, 200)

def equal404 (response):
    assertEqual (response.status_code, 404)
    
def nequal200 (response):
    assertNotEqual (response.status_code, 200)
    
def ver11 (response):
    assertEqual (response.version, "1.1")    

def ver20 (response):
    assertEqual (response.version, "2.0")    

def increase (response):
    __fetchcount += 1

def checkout ():
    r = __fetchcount
    __fetchcount = 0
    return r
            
def test_1 ():            
    aquests.configure (1, callback = equal200)
    aquests.get (SERVER)
    aquests.fetchall ()

def test_2 ():            
    aquests.configure (1, callback = ver20)
    aquests.get (SERVER)
    aquests.fetchall ()
        
def test_3 ():            
    aquests.configure (1, callback = ver11, force_http1 = True)
    aquests.get (SERVER)
    aquests.fetchall ()
    
def test_4 ():    
    munreq = 1000
    aquests.configure (1, callback = increase, force_http1 = True)
    for i in range (munreq):
        aquests.get (SERVER)
    aquests.fetchall ()
    assertEqual (checkout (), munreq)            

def test_5 ():    
    munreq = 1000                
    aquests.configure (1, callback = increase, http2_constreams = 10)
    for i in range (munreq):
        aquests.get (SERVER)
    aquests.fetchall ()
    assertEqual (checkout (), munreq)

def test_6 ():            
    aquests.configure (1, callback = equal404)
    aquests.get (SERVER + "/no-page")
    aquests.fetchall ()

def test_7 ():            
    aquests.configure (1, callback = equal404, force_http1 = True)
    aquests.get (SERVER + "/no-page")
    aquests.fetchall ()

def test_8 ():    
    munreq = 3000
    aquests.configure (10, callback = increase, force_http1 = True)
    for i in range (munreq):
        aquests.get (SERVER)
    aquests.fetchall ()
    assertEqual (checkout (), munreq)            

def test_9 ():    
    munreq = 3000                
    aquests.configure (2, callback = increase, http2_constreams = 5)
    for i in range (munreq):
        aquests.get (SERVER)
    aquests.fetchall ()
    assertEqual (checkout (), munreq)

def test_10 ():            
    aquests.configure (1, callback = equal404)
    for i in range (10):
        aquests.get (SERVER + "/no-page")
    aquests.fetchall ()

def test_11 ():            
    aquests.configure (1, callback = equal404, force_http1 = True)
    for i in range (10):    
        aquests.get (SERVER + "/no-page")
    aquests.fetchall ()
