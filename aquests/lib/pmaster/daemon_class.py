from .. import pathtool, logger
import os, signal
import time, sys

EXIT_CODE = None

class DaemonClass:
    NAME = "base"
    def __init__ (self, logpath, varpath, consol):        
        self.logpath = logpath
        self.varpath = varpath
        self.consol = consol
        self.last_maintern = 0
        self.flock = None
        self.shutdown_in_progress = False
        
        logpath and pathtool.mkdir (logpath)
        varpath and pathtool.mkdir (varpath)
            
        if not self.consol: # service mode
            sys.stderr = open (os.path.join (varpath, "stderr.log"), "a")
        self.make_logger ()
        self.setup ()
    
    def log (self, msg, type = "info"):
        self.logger (msg, type)
    
    def trace (self):
        self.logger.trace (self.NAME)    
                
    def make_logger (self):        
        self.logger = logger.multi_logger ()
        if self.consol:
            self.logger.add_logger (logger.screen_logger ())
        if self.logpath:
            self.logger.add_logger (logger.rotate_logger (self.logpath, self.NAME, "weekly"))
            self.log ("{} log path: {}".format (self.NAME, self.logpath), "info")        
        self.log ("{} tmp path: {}".format (self.NAME, self.varpath), "info")
            
    def bind_signal (self, term, kill, hup):
        if os.name == "nt":
            signal.signal(signal.SIGBREAK, term)
        else:    
            def hUSR1 (signum, frame):    
                self.logger.rotate ()                
            signal.signal(signal.SIGUSR1, hUSR1)
            signal.signal(signal.SIGTERM, term)            
            signal.signal(signal.SIGHUP, hup)
    
    def start (self):
        self.log ("service %s started" % self.NAME)    
        try:
            self.run ()
        except KeyboardInterrupt:
            pass    
        except:
            self.trace ()
    
    def close (self):
        self.log ("service %s stopped" % self.NAME)
            
    def setup (self):
        pass
    
    def run (self):
        raise NotImplementedError
    
def make_service (service_class, logpath, varpath, consol, *args, **kargs):
    pathtool.mkdir (varpath)
    if logpath:
        pathtool.mkdir (logpath)
    return service_class (logpath, varpath, consol, *args, **kargs)
