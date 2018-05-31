from .. import pathtool, logger
import os, signal
import time, sys

EXIT_CODE = None

class DaemonClass:
    NAME = "base"
    def __init__ (self, config, logpath, varpath, consol):
        self.config = config
        self.logpath = logpath
        self.varpath = varpath
        self.consol = consol
        self.last_maintern = 0
        self.flock = None
        self.shutdown_in_progress = False
        if self.consol not in ("1", "yes"): # service mode
            sys.stderr = open (os.path.join (varpath, "stderr.log"), "a")            
        self.setup ()
    
    def close (self):
        pass
            
    def make_logger (self):        
        self.logger = logger.multi_logger ()
        if self.consol:
            self.logger.add_logger (logger.screen_logger ())
        if self.logpath:
            self.logger.add_logger (logger.rotate_logger (self.logpath, self.NAME, "weekly"))
            self.logger ("{} log path: {}".format (self.NAME, self.logpath), "info")        
        self.logger ("{} tmp path: {}".format (self.NAME, self.varpath), "info")
            
    def bind_signal (self, term, kill, hup):
        if os.name == "nt":
            signal.signal(signal.SIGBREAK, term)
        else:    
            def hUSR1 (signum, frame):    
                self.logger.rotate ()                
            signal.signal(signal.SIGUSR1, hUSR1)
            signal.signal(signal.SIGTERM, term)            
            signal.signal(signal.SIGHUP, hup)
            
    def setup (self):
        raise NotImplementedError

def make_service (service_class, config, logpath, varpath, consol):
    pathtool.mkdir (varpath)
    if logpath:
        pathtool.mkdir (logpath)
    return service_class (config, logpath, varpath, consol)
