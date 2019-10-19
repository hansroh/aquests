from . import asynconnect
from rs4 import webtest
import threading
import time

class SynConnect (asynconnect.AsynConnect):
    ssl = False
    proxy = False

    def __init__ (self, address, lock = None, logger = None):
        self.address = address
        self.lock = lock
        self.logger = logger
        self._cv = threading.Condition ()
        self.auth = None
        self.set_event_time ()
        self.initialize_connection ()

        self.endpoint = "{}://{}".format (self.ssl and 'https' or 'http', self.address [0])
        port = self.address [1]
        if not ((self.ssl and port == 443) or (not self.ssl and port == 80)):
            self.endpoint += ":{}".format (port)
        self.connected = False

    def set_auth (self, auth):
        self.auth = auth

    def close (self):
        self.connected = False

    def disconnect (self):
        self.close ()

    def isconnected (self):
        return self.connected

    def connect (self):
        if not self.connected:
            self.webtest = webtest.Target (self.endpoint)
            self.connected = True


class SynSSLConnect (SynConnect):
    ssl = True
