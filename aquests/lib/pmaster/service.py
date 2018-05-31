import os
from setproctitle import setproctitle
import time

if os.name == "nt":
    import win32serviceutil
    
class Service:
    def __init__ (self, name, working_dir, lockpath):
        self.name = name
        self.working_dir = working_dir
        self.lockpath = lockpath        
        setproctitle (name)
        os.chdir (working_dir)
        
    def start (self):
        if os.name == "nt":
            set_service_config (['start'])
        else:    
            from aquests.lib.pmaster import Daemonizer
            if not Daemonizer (self.working_dir, self.name, lockpath = self.lockpath).runAsDaemon ():
                print ("already running")
                sys.exit ()
            
    def stop (self):
        if os.name == "nt":            
            set_service_config (['stop'])
        else:    
            from aquests.lib.pmaster import daemon
            daemon.kill (self.lockpath, self.name, True)
    
    def status (self, verbose = True):
        from aquests.lib.pmaster import daemon
        pid = daemon.status (self.lockpath, self.name)
        if verbose:
            if pid:
                print ("running [%d]" % pid)
            else:
                print ("stopped")
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
            global Win32Service            
            #sys.stdout = sys.stderr = open (r"D:\apps\skitai\examples\err.log", "a")
            argv.insert (0, "")            
            script = os.path.join (os.getcwd (), sys.argv [0])
            win32serviceutil.HandleCommandLine(Win32Service, "%s.%s" % (script [:-3], Win32Service.__name__), argv)
                
        def install (self):
            self.set_service_config (['--startup', 'auto', 'install'])
    
        def remove (self):
            self.set_service_config (['remove'])
        
        def update (self):
            self.set_service_config (['update'])


            