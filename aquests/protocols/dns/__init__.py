
"""
2008 added for asynchronous DNS query by Hans Roh
"""

import asyncore
import time
import random
from .pydns import Base, Type, Class, Lib, Opcode
import threading
from ... import lifetime
from .clients import UDPClient, TCPClient

defaults = Base.defaults
        
class RequestHandler:
    def __init__(self, lock, logger, client_getter):
        self.lock = lock 
        self.logger = logger
        self.client_getter = client_getter
        self.id = 0
        
    def get_id (self):
        with self.lock:
            self.id += 1
            if self.id == 32768:
                self.id = 1    
            return self.id
        
    def argparse (self, name, args):
        args['name'] = name
        if 'errors' not in args:
            args ['errors'] = []
            
        for i in list(defaults.keys()):
            if i not in args:
                args[i]=defaults[i]
        return args
        
    def handle_request (self, name, **args):
        if isinstance (name, str):
            name = name.encode ("utf8")
        args = self.argparse (name, args)

        protocol = args ['protocol']
        opcode = args ['opcode']
        rd = args ['rd']
        
        if type(args['qtype']) in (bytes, str):
            try:
                qtype = getattr (Type, args ['qtype'].upper ())
            except AttributeError:
                raise Base.DNSError('%s unknown query type' % name)
                
        else:
            qtype = args ['qtype']
            
        qname = args ['name']        
        m = Lib.Mpacker()        
        m.addHeader(self.get_id (),
              0, opcode, 0, 0, rd, 0, 0, 0,
              1, 0, 0, 0)
        
        m.addQuestion (qname, qtype, Class.IN)
        request = m.getbuf ()
        
        conn = self.client_getter (args.get ('addr'), args ['protocol'])
        conn.query (request, args, self.process_reply)
        
    def process_reply (self, args, data, timeouted):        
        err = None
        answers = []
        qname = args ['name'].decode ('utf8')
        
        if timeouted:
            err = 'timeout'            
        else:    
            try:
                if not data:
                    err = "no-reply"                    
                else:    
                    if args ["protocol"] == "tcp":
                        header = data [:2]
                        if len (header) < 2:
                            err = 'EOF-invalid-header' % qname
                        count = Lib.unpack16bit(header)
                        reply = data [2: 2 + count]
                        if len (reply) != count:
                            err = "incomplete-reply"                    
                    else:
                        reply = data
                    
            except:
                self.logger.trace ()
                err = 'exception'    
            
            if not err:
                try:    
                    u = Lib.Munpacker(reply)
                    r = Lib.DnsResult(u, args)
                    r.args = args
                    if r.header ['tc']:
                        err = 'truncate'
                        args ['protocol'] = 'tcp'
                        self.logger ('%s, trucated switch to TCP' % qname, 'warn')
                        
                    else:
                        if r.header ['status'] != 'NOERROR':
                            self.logger ('%s, status %s' % (qname, r.header ['status']), 'warn')
                            answers = [{"name": qname, "data": None, "status":  r.header ['status']}]
                        else:    
                            answers = r.answers
                            
                except:
                    self.logger.trace ()
        
        if err:
            if len (args ['errors']) < 2:
                args ['errors'].append (err)
                # switch protocol
                args ['protocol'] = args ['protocol'] == "tcp" and "udp" or "tcp"
                query (**args)
                return
            
            self.logger ('%s, DNS %s errors' % (qname, args ['errors']), 'warn')        
            answers = [{"name": qname, "data": None, "error": err}] 
        
        callback = args.get ("callback", None)
        if callback:
            if type (callback) != type ([]):
                callback = [callback]
            for cb in callback:                
                cb (answers)
        
        
class Pool:
    query_timeout = 1
    
    def __init__ (self, servers, logger):
        self.logger = logger
        self.lock = threading.Lock ()
        self.handler = RequestHandler (self.lock, self.logger, self.get_client)
        self.servers = [(x, 53) for x in servers]
        self.udps = [UDPClient (x, self.logger) for x in self.servers]                        
        self.queue = []
        
    def add (self, item):
        with self.lock:
            self.queue.append (item)
    
    def has_job (self):
        with self.lock:
            for client in self.udps:
                if len (client.requests):
                    return 1
        return 0
    
    def jobs (self):
        t = []        
        with self.lock:
            for client in self.udps:
                t.extend (list (client.requests.keys ()))
        return t    
    
    def qsize (self):
        with self.lock:
            return len (self.queue)
                
    def pop_all (self):
        # DNS query maybe not allowed delay between request and send
        # maybe they just drop response packet for delaying
        with self.lock:
            queue, self.queue = self.queue [:], []
                
        count = len (queue)
        while queue:
            name, args = queue.pop (0)
            self.handler.handle_request (name, **args)
    
        if (not count and not self.has_job ()):
            return
        
        map = {}
        with self.lock:
            for client in self.udps:
                map [client._fileno] = client
        fds = list (map.keys ())
        
        # maybe 2 is enough
        safeguard = count * 2
        while self.has_job () and safeguard:
            safeguard -= 1
            asyncore.loop (0.1, map, count = 1)
            if safeguard % 5 == 0:
                self.maintern (time.time ())        
        self.maintern (time.time ())
                            
        for fd in fds:
            if fd not in map:
                # resync 
                try: del asyncore.socket_map [fd]
                except KeyError: pass    
        
    def maintern (self, now):
        for client in self.udps:
            for id, (args, starttime) in list (client.requests.items ()):
                if now - starttime > self.query_timeout:
                    client.collect_incoming_data (b'', id)
            
    def get_client (self, exclude = None, protocol = "tcp"):
        if protocol == "tcp":
            random.shuffle (self.servers)
            addr = self.servers [0]
            return TCPClient (addr, self.logger)
        else:
            random.shuffle (self.udps)
            return self.udps [0]

def query (name, **args):
    global pool
    if not lifetime.EXHAUST_DNS:
        return pool.handler.handle_request (name, **args)
    pool.add ((name, args))
    
def pop_all ():    
    global pool
    pool.pop_all ()
    
def qsize ():
    global pool
    return pool.qsize ()

    
PUBLIC_DNS_SERVERS = [
    '8.8.8.8', 
    '8.8.4.4'
]

Base.DiscoverNameServers ()
PRIVATE_DNS_SERVERS = Base.defaults['server']

pool = None            
def create_pool (dns_servers, logger):
    global pool, PUBLIC_DNS_SERVERS, PRIVATE_DNS_SERVERS
    if not dns_servers:
        dns_servers = PRIVATE_DNS_SERVERS or PUBLIC_DNS_SERVERS
    pool = Pool (dns_servers, logger)

testset = [
    "www.alexa.com",
    "www.yahoo.com",
    "www.microsoft.com",
    "www.amazon.com",
    "www.cnn.com",
    "www.gitlab.com",
    "www.github.com",
    "hub.docker.com",
]

def test_callback (ans):
    global testset, pool
    
    pprint.pprint (ans)    
    if testset:
        item = testset.pop ()        
        self.handler.handle_request (item, protocol = "udp", callback = test_callback, qtype = "a")

def _print (ans):
    if ans:
        print (ans[0]['name'], ans[-1]['data'])
    else:
        print ("FAILED")
        
        
if __name__    == "__main__":
    from rs4 import logger
    import pprint
    
    create_pool (PUBLIC_DNS_SERVERS, logger.screen_logger ())
    for i in range (4):
        #query ("www.microsoft.com", protocol = "udp", callback = _print, qtype="a")
        #query ("www.cnn.com", protocol = "udp", callback = _print, qtype="a")
        #query ("www.gitlab.com", protocol = "udp", callback = _print, qtype="a")
        #query ("www.alexa.com", protocol = "udp", callback = _print, qtype="a")
        #query ("www.yahoo.com", protocol = "udp", callback = _print, qtype="a")
        #query ("www.github.com", protocol = "udp", callback = _print, qtype="a")
        #query ("www.google.com", protocol = "udp", callback = _print, qtype="a")
        #query ("www.amazon.com", protocol = "udp", callback = _print, qtype="a")
        #query ("www.almec.com", protocol = "udp", callback = _print, qtype="a")
        #query ("www.alamobeauty.com", protocol = "udp", callback = _print, qtype="a")
        #query ("www.alphaworld.com", protocol = "udp", callback = _print, qtype="a")
        #query ("www.allrightsales.com", protocol = "udp", callback = _print, qtype="a")
        query ("www.glasteel.com", protocol = "udp", callback = _print, qtype="a")
    
    pop_all ()
    print ('------------------------')    
    while 1:
        pop_all ()
        asyncore.loop (timeout = 1, count = 1)
        print ('UNFINISHED', pool.jobs ())
        
    
    