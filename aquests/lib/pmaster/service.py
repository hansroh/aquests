import os, sys
from setproctitle import setproctitle
from . import daemon
import time
from aquests.lib.termcolor import tc
if os.name == "nt":
    import win32serviceutil
    
class Service:
    def __init__ (self, name, working_dir, lockpath = None, win32service = None):
        self.name = name
        self.working_dir = working_dir
        self.lockpath = lockpath or working_dir
        self.win32service = win32service        
        setproctitle (name)
        os.chdir (working_dir)
        
    def start (self):
        if os.name == "nt":
            set_service_config (['start'])
        else:    
            from aquests.lib.pmaster import Daemonizer
            if not Daemonizer (self.working_dir, self.name, lockpath = self.lockpath).runAsDaemon ():
                pid = daemon.status (self.lockpath, self.name)
                print ("{} {}".format (tc.debug (self.name), tc.error ("[already running:{}]".format (pid))))
                sys.exit ()
            
    def stop (self):
        if os.name == "nt":            
            set_service_config (['stop'])
        else:    
            daemon.kill (self.lockpath, self.name, True)
    
    def status (self, verbose = True):
        pid = daemon.status (self.lockpath, self.name)
        if verbose:
            if pid:
                print ("{} {}".format (tc.debug (self.name), tc.warn ("[running:{}]".format (pid))))
            else:
                print ("{} {}".format (tc.debug (self.name), tc.secondary ("[stopped]")))
        return pid
    
    def execute (self, cmd):
        if cmd == "stop":
            self.stop ()
            return False
        elif cmd == "status":
            self.status ()
            return False
        elif cmd == "start":
            self.start ()
        elif cmd == "restart":
            self.stop ()        
            time.sleep (2)
            self.start ()
        elif cmd == "install":    
            self.install ()
        elif cmd == "update":    
            self.update ()
        elif cmd == "remove":    
            self.remove ()
        else:
            raise AssertionError ('unknown command: %s' % cmd)
                
        if os.name == "nt":
            return False
        return True
    
    if os.name == "nt":
        def set_service_config (self, argv = []):
            argv.insert (0, "")            
            script = os.path.join (os.getcwd (), sys.argv [0])
            win32serviceutil.HandleCommandLine(self.win32service, "%s.%s" % (script [:-3], self.win32service.__name__), argv)
                
        def install (self):
            self.set_service_config (['--startup', 'auto', 'install'])
    
        def remove (self):
            self.set_service_config (['remove'])
        
        def update (self):
            self.set_service_config (['update'])


            