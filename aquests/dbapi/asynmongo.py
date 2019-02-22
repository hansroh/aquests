from . import asynredis    
import struct
import socket
import bson
from pymongo import auth, message
from bson.codec_options import CodecOptions
from bson.son import SON

DEBUG = True
MAXINT = 2 ** (struct.Struct('i').size * 8 - 1) - 1
_UNICODE_REPLACE_CODEC_OPTIONS = CodecOptions (unicode_decode_error_handler='replace')

class MongoDBError (Exception):
    pass

def _unpack_response(data, op_code, request_id = None):
    # this function had been removed from pymong 3.4
    if op_code == 1:
        response_flag, cursor_id, starting_from, number_returned = struct.Struct("<iqii").unpack_from (data)
        if response_flag & 1:        
            if request_id is None:
                raise MongoDBError ("No cursor id for getMore operation")                              
            raise MongoDBError ("Cursor not found, cursor id: %d" % (request_id,))
           
        elif response_flag & 2:
            error_object = bson.BSON(data[20:]).decode()
            error_object.setdefault("ok", 0)
            
        result = {"cursor_id": cursor_id,
              "starting_from": starting_from,
              "number_returned": number_returned,
              "data": bson.decode_all(data[20:], _UNICODE_REPLACE_CODEC_OPTIONS)}
        assert len(result["data"]) == result["number_returned"]
        
    elif op_code == 2013:
        first_payload_type, first_payload_size = struct.Struct("<Bi").unpack_from (data)
        assert len (data) == first_payload_size + 5
        result = {"first_payload_type": first_payload_type,
              "first_payload_size": first_payload_size,              
              "data": bson.decode_all(bytes (data[5:]), _UNICODE_REPLACE_CODEC_OPTIONS)}
    else:
        raise MongoDBError ("Got opcode %r but expected opcode %r" % (op_code))
    
    return result
    
class MongoMessageHandler:
    def __init__ (self, asyncon):
        self.asyncon = asyncon
        self.dbname = asyncon.dbname                
        self.length = -1
        self.request_id = 0
        self.op_code = 0
    
    def close (self):    
        self.asyncon = None

    def send_message (self, message):
        try:
            self.request_id, data, max_bson_size = message
        except ValueError:            
            self.request_id, data = message        
        self.asyncon.push (data)
        self.asyncon.set_terminator (16)
        
    def _parse_header (self, header):
        """
        This method and below _parse_response() is based on 
        asyncmongo: An asynchronous library for accessing mongo with tornado.ioloop
        Author: Bitly
        URL: https://github.com/bitly/asyncmongo
        """
        length = int(struct.unpack("<i", header[:4])[0])
        request_id = struct.unpack("<i", header[8:12])[0]
        assert request_id == self.request_id, \
            "ids don't match %r %r" % (self.request_id, request_id)
        self.op_code = struct.unpack("<i", header[12:])[0]
        self.length = length - 16        
        self.asyncon.set_terminator (self.length)
        
    def _parse_response (self, response):
        self.length = -1
        self.asyncon.set_terminator (16)
        request_id, op_code = self.request_id, self.op_code
        self.request_id, self.op_code = 0, 0
        try:
            response = _unpack_response(response, op_code, request_id)
        except:            
            self.asyncon.handle_error ()
                        
        if response and response['data'] and response['data'][0].get('err') and response['data'][0].get('code'):
            raise MongoDBError ("[%s] %s" % (response['data'][0]['code'], response['data'][0]['err']))
        else:
            self.asyncon.handle_response (response)        
        
    
class AsynConnect (asynredis.AsynConnect):    
    def __init__ (self, address, params = None, lock = None, logger = None):
        asynredis.AsynConnect.__init__ (self, address, params, lock, logger)
        self.mgh = MongoMessageHandler (self)
        self.codec_option = CodecOptions (SON)
        self._state = None
        
    def handle_connect (self):
        self.set_event_time ()        
        if self.user:
            self._state = "nonce"
            msg = message.query(0, "%s.$cmd" % self.dbname,    0, 1, SON({'getnonce': 1}),SON({}))
            self.mgh.send_message (msg)
            
    def push_command (self, msg):
        self.set_event_time ()
        self.mgh.send_message (msg)
    
    def get_full_colname (self, colname):    
        return "%s.%s" % (self.dbname, colname)

    def is_response_expected (self):        
        if self.last_command == "kill_cursors" and not self.producer_fifo:
            self.handle_response (None)
            
    def handle_write (self):
        asynredis.AsynConnect.handle_write (self)    
        self.is_response_expected ()
            
    def push (self, data):
        asynredis.AsynConnect.push (self, data)    
        self.is_response_expected ()
    
    def found_terminator (self):        
        if self.user and self._state is not None:
            if self._state == "nonce":
                self._state = "finish"
                response = self.fetchall ()
                try:
                    nonce = response['data'][0]['nonce']                
                    key = auth._auth_key(nonce, self.dbuser, self.dbpass)
                except:
                    raise AuthenticationError ("Authentication Error")
                msg = message.query (
                    0, "%s.$cmd" % self.pool._dbname, 0, 1,
                    SON([('authenticate', 1), ('user', self.user), ('nonce', nonce), ('key', password)]), SON({}, self.codec_option)
                )
                return self.send_message (msg)
                
            elif self._state == "finish":
                self._state = None
                response = self.fetchall ()                
                try:
                    assert response ['number_returned'] == 1
                    response = response ['data'][0]
                except:
                    raise AuthenticationError ("Authentication Error")
                if response.get("ok") != 1:                
                    raise AuthenticationError (response.get("errmsg"))
            return    
    
        if self.mgh.length == -1:
            self.mgh._parse_header (self.data [-1])
        else:            
            self.mgh._parse_response (self.data [-1])
        self.data = []
        
    def handle_response (self, response):
        if response is not None: # if None end of session
            if self.last_command [:6] in ("insert", "upsert", "delete"):
                data = response ["data"][0]
                if data ["ok"] != 1.0:
                    raise MongoDBError ("%(err)s (connectionId:%(connectionId)d syncMillis:%(syncMillis)d)" % data)
                    
            self.response = response
            if not self.preserve_cursor:
                cursor_id = response.get ('cursor_id')
                if cursor_id != 0:
                    self.response ['cursor_id'] = 0
                    return self.kill_cursors ([cursor_id])

        self.has_result = True
        self.close_case_with_end_tran ()
        
    def fetchall (self):
        r = self.response
        self.response = None
        self.has_result = False
        return r
    
    def __query (self, colname, spec, offset = 0, limit = 1):
        # options, collection_name, num_to_skip, num_to_return, query, field_selector, opts, check_keys
        if limit == -1: limit = MAXINT
        msg = message.query (0, self.get_full_colname (colname), offset, limit, spec, None, self.codec_option)
        self.push_command (msg)
    
    def find (self, colname, spec, offset = 0, limit = 1):
        self.preserve_cursor = False
        self.__query (colname, spec, offset, limit)
    
    def findone (self, colname, spec):
        self.preserve_cursor = False
        self.__query (colname, spec, 0, 1)    
    
    def findall (self, colname, spec):
        self.preserve_cursor = False
        self.__query (colname, spec, 0, -1)    
    
    def findkc (self, colname, spec, offset = 0, limit = 1):
        self.preserve_cursor = True
        self.__query (colname, spec, offset, limit)
        
    def get_more (self, colname, cursor_id, num_to_return):
        self.preserve_cursor = True
        msg = message.get_more (self.get_full_colname (colname), num_to_return, cursor_id)
        self.push_command (msg)
    
    def kill_cursors (self, cursor_ids):
        self.last_command = "kill_cursors"
        if type (cursor_ids) not in (list, tuple): cursor_ids = [cursor_ids]
        msg = message.kill_cursors (cursor_ids)
        self.push_command (msg)
    
    def insert (self, colname, docs, continue_on_error = 0):
        #collection_name, docs, check_keys, safe, last_error_args, continue_on_error, opts
        if type (docs) not in (list, tuple): docs = [docs]        
        msg = message.insert (self.get_full_colname (colname), docs, False, 1, (), continue_on_error, self.codec_option)    
        self.push_command (msg)
    
    def __update (self, colname, spec, doc, multi = 1, upsert = 0):
        #collection_name, upsert, multi, spec, doc, safe, last_error_args, check_keys, opts
        msg = message.update (self.get_full_colname (colname), upsert, multi, spec, doc, 1, (), False, self.codec_option)
        self.push_command (msg)
    
    def update (self, colname, spec, doc):
        self.__update (colname, spec, doc, 1, 0)
        
    def updateone (self, colname, spec, doc):
        self.__update (colname, spec, doc, 0, 0)
        
    def upsert (self, colname, spec, doc):
        self.__update (colname, spec, doc, 1, 1)
    
    def upsertone (self, colname, spec, doc):
        self.__update (colname, spec, doc, 0, 1)
        
    def delete (self, colname, spec, flag = 0):
        #collection_name, spec, safe, last_error_args, opts, flags=0
        msg = message.delete (col, args [0], 1, (), self.codec_option, flags)        
        self.push_command (msg)
    
    def begin_tran (self, request):
        if not asynredis.AsynConnect.begin_tran (self, request):
            return False
        self.response = None
        self.last_command = request.method.lower ()
        self.preserve_cursor = False
        self.data = []
        return True
    
    REQ_OPS_OF_WIRE_PROTOCOL = (
        "find", "findone", "findall", 
        "kfind", "get_more", "kill_cursors",
        "insert", "delete",
        "update", "upsert", "updateone", "upsertone"        
    )
    def execute (self, request):
        # SHOULD push before adding to map, otherwise raised threading collision
        command = request.method.lower ()
        if command not in self.REQ_OPS_OF_WIRE_PROTOCOL:
            raise NotImplementedError ("Command %s Not Impemented" % command)

        self.begin_tran (request)        
        getattr (self, command) (*request.params)
        self.set_terminator (16)
        if not self.connected:
            self.connect ()
        elif not self.backend:
            self.add_channel ()
        