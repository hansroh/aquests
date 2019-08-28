from rs4 import asynchat
import socket
import time
from .pydns import Base, Type, Class, Lib, Opcode

class UDPClient (asynchat.async_chat):
    protocol = "udp"
    zombie_timeout = 1200
    ac_in_buffer_size = 512
    
    def __init__ (self, addr, logger):
        self.addr = addr
        self.logger = logger                
        self.event_time = time.time ()
        self.creation_time = time.time ()        
        self.closed = False
        self._timeouted = False
        self.requests = {}
        self.callback = None
        asynchat.async_chat.__init__ (self)
                            
    def query (self, request, args, callback):    
        if self.callback is None:
            self.callback = callback
        self.event_time = time.time ()        
        self.header = None
        
        self.requests [request [:2]] = [args, time.time ()]
        qname = args ["name"].decode ("utf8")
        args ['addr'] = self.addr
        self.push (request)
            
        if not self.connected:
            self.set_terminator (None)
            self.create_socket (socket.AF_INET, socket.SOCK_DGRAM)
            self._connect ()
                
    def _connect (self):        
        try:
            self.connect (self.addr)
        except:
            self.handle_error ()
                    
    def trace (self):
        self.logger.trace ()
    
    def log_info (self, line, level = 'info'):
        self.log ("[%s] %s" % (level, line))
              
    def log (self, line):
        self.logger (line)
            
    def handle_error (self):
        self.trace ()
        self.close ()
    
    def handle_timeout (self):
        self._timeouted = True
        self.handle_close ()
                    
    def handle_connect (self):    
        self.event_time = time.time ()        
        
    def handle_expt (self):
        self.handle_close ()
        
    def collect_incoming_data (self, data, id = None):
        try:
            args, starttime = self.requests.pop (id or data [:2])                
        except KeyError:
            # alerady timeouted
            pass
        else:    
            self.callback (args, data, id is not None)
            
    def handle_close (self):    
        for args, starttime in self.requests.values ():
            self.callback (args, b'', True)
        self.close ()

        
class TCPClient (UDPClient):
    protocol = "tcp"
    zombie_timeout = 10
    ac_in_buffer_size = 65536
    
    def __init__ (self, addr, logger):        
        UDPClient.__init__ (self, addr, logger)
        self.callback = None
        self.args = None
        self.request = None
        self.header = None
        self.reply = b''
                            
    def query (self, request, args, callback):    
        self.event_time = time.time ()
        self.reply = b""
        self.header = None
        self.request = request
        self.args = args
        self.callback = callback
        
        args ['addr'] = self.addr        
        self.push (Lib.pack16bit(len(request)) + request)
        if not self.connected:
            self.set_terminator (2)
            self.create_socket (socket.AF_INET, socket.SOCK_STREAM)                
            self._connect ()
        
    def collect_incoming_data (self, data):        
        self.reply += data
            
    def found_terminator (self):    
        if self.header:
            self.callback (self.args, self.header + self.reply, self._timeouted)
            self.close ()
            
        else:
            self.header, self.reply = self.reply, b""
            count = Lib.unpack16bit(self.header)
            self.set_terminator (count)            
        
    def handle_close (self):    
        self.callback (self.args, b'', self._timeouted)                
        self.close ()
