from .synsqlite3 import SynConnect
from .dbconnect import DBConnect
import psycopg2
import redis

class Postgres (SynConnect):
    def connect (self):
        try:
            host, port = self.address        
            self.conn = psycopg2.connect (
                dbname = self.dbname,
                user = self.user,
                password = self.password,
                host = host,
                port = port
            )
        except:
            self.handle_error ()
        else:    
            self.connected = True

    def close_if_over_keep_live (self):
        DBConnect.close_if_over_keep_live (self)

    def execute (self, request):
        DBConnect.begin_tran (self, request)            
        sql = self._compile (request)
        
        if not self.connected:
            self.connect ()
            self.conn.isolation_level = None
                
        try:
            if self.cur is None:
                self.cur = self.conn.cursor ()
            sql = self._compile (request)
            self.cur.execute (sql, *request.params [1:])      
            self.has_result = True        
        except:
            self.handle_error ()
        else:            
            self.close_case ()


class Redis (Postgres):
    def close (self, deactive = 1):    
        if self.conn:    
            self.conn.close ()            
            self.conn = None    
        self.connected = False    
        DBConnect.close (self, deactive)

    def close_case (self):
        if self.request:
            self.request.handle_result (None, self.expt, self.fetchall ())
            self.request = None
        self.set_active (False)

    def connect (self):
        host, port = self.address
        self.conn = redis.Redis (host = host, port = port, db = self.dbname)

    def fetchall (self):
        result, self.response = self.response, None
        return result

    def prefetch (self):
        self.response = [[]]
        self.response = getattr (self.conn, self.request.method) (*self.request.params)
        self.has_result = True

    def execute (self, request):
        DBConnect.begin_tran (self, request)
        try:
            if not self.connected:
                self.connect ()
            self.prefetch ()            
        except:
            self.handle_error ()
        else:            
            self.close_case ()


class MongoDB (Redis):
    def prefetch (self):
        self.response = None
        self.response = getattr (self.conn [self.request.dbname], self.request.method.lower ()) (*self.request.params)                 
        self.has_result = True

    def connect (self):
        user, password = "", ""
        auth = self.request.auth
        if auth:
            if len (auth) == 2:
                user, password = auth
            else:
                user = auth [0]    
        host, port = self.address

        kargs = {}
        if user: kargs ["username"] = user
        if password: kargs ["password"] = password        
        if port: kargs ["port"] = port        
        self.conn = pymongo.MongoClient (host = host, **kargs)        
