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
                self.cur.execute (sql, *request.params [1:])
                self.has_result = True
        except:
            self.handle_error ()
        else:            
            self.close_case ()


class Redis (Postgres):
    def connect (self):
        host, port = self.address
        self.conn = redis.Redis (host = host, port = port, db = self.dbname)

    def close (self, deactive = 1):    
        if self.conn:    
            self.conn.close ()            
            self.conn = None    
        self.connected = False    
        DBConnect.close (self, deactive)

    def _fetchall (self, command):
        try:
            resp = getattr (self.conn, command) (*self.request.params)
        except:
            self.handle_error ()
        else:            
            self.close_case ()
        self.has_result = False    
        return resp

    def fetchall (self):
        return self._fetchall (self.request.method)

    def execute (self, request):
        DBConnect.begin_tran (self, request)            
        if not self.connected:
            self.has_result = True
            self.connect ()


class MongoDB (Redis):
    def fetchall (self):
        return self._fetchall (self.request.method.lower ())        

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
