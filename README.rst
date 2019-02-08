====================================
Asynchronous Multiplexing Requests
====================================

Aquests is generating asynchronous requests and fetching data from HTTP2, REST API, Websocket, RPCs and several Database engines. This project was originally started for testing `Skitai App Engine`_ and seperated for efficient developing eaches on Jan 2017.

Supported requests are:

- HTTP/1.1
- HTTP/2.0 if target server provides
- Websocket
- XML-RPC
- gRPC
- PostgreSQL
- MongoDB
- Redis

Aquests is a kind of sub module which is mainly used by `Skitai App Engine`_, you can consider Python3 asyncio alternatively. 

.. _`Skitai App Engine`: https://pypi.python.org/pypi/skitai

.. contents:: Table of Contents


Quickstart
=============

For fetching single web page:

.. code-block:: python

  import aquests
  
  aquests.get ("http://127.0.0.1:5000/")
  aquests.fetchall ()

Its result is:

.. code-block:: bash

  user$ REQID 0. HTTP/2.0 200 OK 4210 bytes received
  
Let's add more pages:

.. code-block:: python
  
  for i in range (3):
    aquests.get ("http://127.0.0.1:5000/")     
  aquests.fetchall ()
  
Its result is:

.. code-block:: bash

  REQID 0. HTTP/2.0 200 OK 4210 bytes received
  REQID 1. HTTP/2.0 200 OK 4210 bytes received
  REQID 2. HTTP/2.0 200 OK 4210 bytes received

Now increase fetching workers,

.. code-block:: python

  aquests.configure (3)  # 3 workers
  for i in range (3):
    aquests.get ("http://127.0.0.1:5000/")     
  aquests.fetchall ()

Result is same as above but somewhat faster and REQID is not ordered.

Now increase workers and pages for making load,

.. code-block:: python
  
  aquests.configure (100) # 100 workers
  for i in range (10000):
    aquests.get ("http://127.0.0.1:5000/")      
  aquests.fetchall ()
  
Now result is,

.. code-block:: bash

  REQID 3635. HTTP/2.0 200 OK 4210 bytes received
  REQID 3627. HTTP/2.0 200 OK 4210 bytes received
  REQID 3594. HTTP/2.0 200 OK 4210 bytes received
  REQID 3702. HTTP/2.0 200 OK 4210 bytes received
  REQID 3685. HTTP/2.0 200 OK 4210 bytes received
  REQID 3637. HTTP/2.0 200 OK 4210 bytes received
  REQID 3591. HTTP/2.0 200 OK 4210 bytes received
  REQID 3586. HTTP/2.0 200 OK 4210 bytes received
  (and scrolled fast...)

Installation
===============

.. code-block:: bash

  pip install aquests

Testing Installation
=========================

At command line,

.. code-block:: bash

  python3 -m aquests.load -n 100 -c 2 http://myserver.com
  # for viewing help
  python3 -m aquests.load --help

Note that is is similar to h2load HTTP2 bench marking tool, but aquests is not optimized for benchmarking.


Usage
======

Binding Callback
-------------------

.. code-block:: python
  
  def finish_request (response):
    print (response.status_code)
    print (response.content)
    
  aquests.configure (workers = 10, callback = finish_request)
  for i in range (10):
    aquests.get ("http://127.0.0.1:5000/")    
  aquests.fetchall ()


Making Traffic Load With Generator Style
------------------------------------------

.. code-block:: python
  
  numreq = 0
  limit = 1000000
  workers = 100
  
  def finish_request (response):
    global numreq, limit     
    if numreq < limit:
      aquests.get ("http://127.0.0.1:5000/")
      numreq += 1
    
  aquests.configure (workers, callback = finish_request)
  for i in range (workers):
    aquests.get ("http://127.0.0.1:5000/")  
    numreq += 1
  aquests.fetchall ()  


Set/Get Request Meta Information
------------------------------------

.. code-block:: python
  
  def finish_request (response):
    print (response.meta ['req_id'])
    print (response.meta ['req_method'])
    print (response.meta ['job_name'])
    
  aquests.configure (workers = 10, callback = finish_request)
  aquests.get ("http://127.0.0.1:5000/", meta = {'job_name': 'test1'})  
  aquests.get ("http://127.0.0.1:5000/", meta = {'job_name': 'test2'})

Note: meta ['req_id'], meta ['req_method'] and meta ['req_callback'] are reserved keys and automatically added by aquests. You SHOULDN'T use theses keys and actually it is better do not use key starts with 'req\_'.


Timeout Setting
----------------

.. code-block:: python
  
  aquests.configure (20, timeout = 10) # 10 seconds
  aquests.get ("https://www.google.co.kr/?gfe_rd=cr&ei=3y14WPCTG4XR8gfSjoK4DQ")  
  aquests.fetchall ()

If timeout occured, response status_code will be 702. Also note above 700 codes mostly indicates network related error.


**Caution**

1. You can't specify timout for each task
2. Cause of aquests' single thread coroutine feature, timeout will not work with exactly timeout seconds.


Set Response Validators For Content-Type and Content-Length
--------------------------------------------------------------

You can set response validators using headers.

.. code-block:: python
  
  aquests.configure (20, timeout = 10) # 10 seconds
  aquests.get (
    "https://www.google.co.kr/?gfe_rd=cr&ei=3y14WPCTG4XR8gfSjoK4DQ",
    headers = {
      "Accept": 'text/html',
      "Accept-Content-Length": 100000, # max 100Kb
    }
  )
  aquests.fetchall ()

Accept-Content-Length is not standard HTTP header but used by aquests. aquests returns status code 718 for unaccpetable content and code 719 for too large content.

Mixed Requests
----------------

.. code-block:: python

  dbo = aquests.mongodb ("127.0.0.1:27017", "test_database")
  aquests.configure (20)
  for i in range (1000): 
    aquests.get ("http://127.0.0.1:5000/")
    dbo.findone ("posts", {"author": "James Milton"})
  aquests.fetchall ()


Authorization
-----------------

For requesting with basic/digest authorization:

.. code:: python

  stub = aquests.rpc (url, auth = (username, password))
  stub.get_prime_number_gt (10000)
  aquests.fetchall ()
  
If you provide both (username, password), aquests try basic/digest authorization. But if just (username,) aquests handle username as bearer token like API Key.


Redirection
------------

For automatically redireting by http status 301, 302, 307, 308:

.. code:: python
  
  def finish_request (response):
    print (response.history)
    
  aquests.configure (callback = finish_request)
  aquests.get ('http://pypi.python.org')
  aquests.fetchall ()
  
response.history is like,

.. code:: python

  [<Response [301]>, <Response [302]>]

Also for disabling redirect,

.. code:: python

  aquests.configure (callback = finish_request, allow_redirects = False)
  

Enabling Cookie
------------------

.. code-block:: python
  
  def finish_request (response):
    print (response.cookies)
    
  aquests.configure (20, callback = finish_request, cookie = True)
  aquests.get ("https://www.google.co.kr/?gfe_rd=cr&ei=3y14WPCTG4XR8gfSjoK4DQ")  
  aquests.fetchall ()

**Caution**

This cookie feature shouldn't handle as different sessions per worker. All workers (connections) of aquests share same cookie values per domain. It means a worker sign in a website, so are the others. Imagine lots of FireFox windows on a desktop computer. If you really need session control, use requests_.


Change Logger
--------------

.. code-block:: python
  
  from aquests.lib import logger
  
  aquests.configure (
    workers = 10, 
    logger = logger.file_logger ('/tmp/logs', 'aquests')
  )


Response
---------

I make similar naming with requests_' attribute and method names as possible.

Response has these attributes and method:

- meta: user added meta data including 'req_id' and 'req_method'
- status_code: HTTP status code or DBO query success (200) or failure (500) code
- reason: status text like OK, Not Found...
- content: bytes content or original db result
- data: usally same as content but on RPC, DB query or json response situation, it returns result object.
- logger: logger.log (msg, type ='info'), logger.trace ()
- method: POST, GET, PUT etc for HTTP/RPC and execute, get, set or lrange etc for DBO
- raise_for_status (): raise exception when HTTP status code >= 300 or DBO command excution failure
- reraise (): shortcut for raise_for_status ()

Below thing is available only on Websocket response.

- opcode: websocket opcode of received message

Below things are available only on DBO responses.

- server: database server address
- dbname: database object name
- params: database command parameters

Below things aren't available on DBO and Websocket responses.

- url: requested url
- history: redirected history by http code 301, 302, 307 and 308 like *[<Response [302]>, <Response [302]>]*
- version: HTTP protocol version
- headers: Response headers
- text: charset encoded string (unicode)
- raw: file like object for bytes stream has raw.read (), raw.readline (),... methods
- cookies: if configure (cookie = True), returns dictionary
- encoding: extracted from content-type header
- request.headers
- request.payload: request body bytes, not available at upload and grpc
- json (): load JSON data, but if response content-type is application/json, automatically loaded into response.data then you can just use it.
- get_header (key, default = None): returns header value, if not exists return default
- get_header_with_attr (key, default = None): returns header value and attr dict like 'text/html', {'charset': 'utf-8'}
- set_cookie (key, val, domain = None, path = "/")
- get_cookie (key)

.. _requests: https://pypi.python.org/pypi/requests


Configuration Parameters
==========================

.. code-block:: python

  import aquests
  
  aquests.configure (
    workers = 1, 
    logger = None, 
    callback = None, 
    timeout = 10, 
    cookie = False,
    force_http1 = False, 
    http2_constreams = 1,
    allow_redirects = True,
    qrandom = False,    
    use_pool = True,
    dns = [], 
    tracking = False        
  )
  
- workers: number of fetching workers, it'not threads
- logger: logger shoukd have 2 method - log (msg, type = 'info') and trace () for exception logging. if not provided, aquests uses aquests.ib.logger.screen_logger
- callback: global default callback function has receiving response arg
- timeout: request timeout seconds
- cookie: enable/disable using cookie for request
- force_http1: enforce http 1.1 not 2.0
- http2_constreams: if you making requests to single http2 server, how many concurrent streams per channel. BE CAREFUL, it might be useful for generating traffic load for testing your http2 web servers. and if your server doesn't provide http2, your workers will be increased to number of http2_constreams times than you really want.
- allow_redirects: if set True, in case HTTP status code is in 301, 302, 307, 308 then redirect automatically
- qrandom: requests will be selected by random, this is useful for load distributing to request multiple hosts.
- use_pool: because aquests use socket pool, if you work with lots of sites concurrently, it may be raised error by too many open files and this can make disabling socket pooling
- dns: DNS server list
- tracking: False, show Python object memory allocation status


List of Methods
==================


GET, DELETE and etc.
---------------------

.. code-block:: python

  aquests.get ("http://127.0.0.1:5000/")
  aquests.delete ("http://127.0.0.1:5000/models/ak-40")
  aquests.get ("https://www.google.co.kr/search?q=aquests")

Also aquests.head (), options () and trace () are available.


POST, PUT
---------------

.. code-block:: python

  aquests.post (
    "http://127.0.0.1:5000/", 
    {'author': 'James Milton'}, 
    {'Content-Type': 'application/x-www-form-urlencoded'}
   )
  
Put example,

.. code-block:: python
  
  aquest.put (
    "http://127.0.0.1:5000/users/jamesmilton",
    {'fullnamer': 'James Milton'},
    {'Content-Type': 'application/json'}
    )
  )
  
  # is equal to:
   
  aquests.putjson (
    "http://127.0.0.1:5000/users/jamesmilton",
    {'fullnamer': 'James Milton'}
  )
  
There're some shorter ways ratehr than specifing content type:

- postjson: application/json, data value should be json dumpable
- postxml: text/xml, data value should be xml string or utf-8 encoded bytes

And putform (), putjson ()... is also available.

  
File Upload
------------

.. code-block:: python

  aquests.upload (
    "http://127.0.0.1:5000/", 
    {
      'author': 'James Milton',
      'file': open ('/tmp/mycar.jpg', 'rb')
    }
  )

You should open file with 'rb' mode.

Websocket
-----------

.. code-block:: python

  aquests.ws ("ws://127.0.0.1:5000/websocket/echo", "Hello World")
  # secure websocket channel, use wss
  aquests.ws ("wss://127.0.0.1:5000/websocket/echo", "Hello World")
  aquests.fetchall ()

Response is like this,
  
- response.status_code: 200
- response.reason: "OK"
- response.content: (1, "Hello World") # (opcode, message)
- response.opcode: 1 # OPCODE_TEXT
- response.data: "Hello World"

Note: Sometimes status_code is 200, opcode is -1. It is NOT official websocket spec. but means websocket is successfully connected but disconnected before receving a message by some reasons.

If you want to send specify message type.

.. code-block:: python
  
  from aquests.protocols.ws import OPCODE_TEXT, OPCODE_BINARY
    
  aquests.ws ("ws://127.0.0.1:5000/websocket/echo", (OPCODE_BINARY, b"Hello World"))
  aquests.fetchall ()

*Note*: This method can only single message per request.


XML-RPC
----------

.. code-block:: python

  stub = aquests.rpc ("https://pypi.python.org/pypi")
  stub.package_releases('roundup')
  stub.prelease_urls('roundup', '1.4.10')
  aquests.fetchall ()

Returns,

.. code-block:: bash

  ['1.5.1']
  <class 'xmlrpc.client.Fault'> <Fault 1:...>


gRPC
----------

.. code-block:: python
  
  import route_guide_pb2
  
  stub = aquests.grpc ("http://127.0.0.1:5000/routeguide.RouteGuide")
  point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
  for i in range (3):
    stub.GetFeature (point)
  aquests.fetchall ()


Returns,

.. code-block:: python

  name: "Berkshire Valley Management Area Trail, Jefferson, NJ, USA"
  location {
    latitude: 409146138
    longitude: -746188906
  }

For more about gRPC and route_guide_pb2, go to `gRPC Basics - Python`_.

.. _`gRPC Basics - Python`: http://www.grpc.io/docs/tutorials/basic/python.html


PostgreSQL
-------------

.. code-block:: python
  
  def finish_request (response):
    print (response.data)    
  
  aquests.configure (3, callback = finish_request)  
  dbo = aquests.postgresql ("127.0.0.1:5432", "mydb", ("test", "1111"))
  for i in range (10):
    dbo.execute ("SELECT city, prcp, temp_hi, temp_low FROM weather;")

Returns,

.. code-block:: bash

  [
    {'prcp': 0.25, 'temp_hi': 50, 'city': 'San  Francisco', 'temp_lo': 46}, 
    {'prcp': 0.0, 'temp_hi': 54, 'city': 'Hayward', 'temp_lo': 37}
  ]  

MongoDB
---------

.. code-block:: python

  dbo = aquests.mongodb ("127.0.0.1:27017", "test_database")
  for i in range (3):
    dbo.findone ("posts", {"author": "Steve Newman"})  
    dbo.findall ("posts", {"author": "Hans Roh"})
  aquests.fetchall ()

Returns,

.. code-block:: bash

  {
    'starting_from': 0, 
    'number_returned': 1, 
    'cursor_id': 0, 
    'data': [
      {
        '_id': ObjectId('586a11f80d23915c7ec76f01'), 
        'author': 'Steve Newman', 
        'title': 'How to swim'
      }
    ]
  }
  

**Available Functions**

- find (colname, spec, offset = 0, limit = 1)
- findone (colname, spec): equivalent with find (colname, spec, 0, 1)
- findall (colname, spec): equivalent with find (colname, spec, 0, -1)
- insert (colname, docs, continue_on_error = 0)
- update (colname, spec, doc)
- updateone (colname, spec, doc)
- upsert (colname, spec, doc)
- upsertone (colname, spec, doc)
- delete (colname, spec, flag = 0)
- findkc (colname, spec, offset = 0, limit = 1): after finidhing search, it keeps cursor alive. then you can use 'get_more()'
- get_more (colname, cursor_id, num_to_return): cursor_id can be got from (findkc()'s result).data ["cursor_id"]
- kill_cursors (cursor_ids): if you use findkc() and stop fetching documents, you should mannually call this.

Note: User authorization is not supported yet.


Redis
---------

.. code-block:: python

  dbo = aquests.redis ("127.0.0.1:6379")
  dbo.get ("session-5ae675bc")
  dbo.lrange ("user-saved-docs", 0, 3)
  aquests.fetchall ()

Returns,

.. code-block:: bash
  
  response-of-session-5ae675bc
  
  [32534, 3453, 6786]

Possibly you can use all `Redis commands`_.

.. _`Redis commands`: https://redis.io/commands


Note: User authorization is not supported yet.


SQLite3 For Fast App Prototyping
---------------------------------

Usage is almost same with PostgreSQL. This service IS NOT asynchronous BUT just emulating.

.. code:: python
  
  dbo = aquests.sqlite3 ("sqlite3.db")
  dbo.execute ("""
    drop table if exists people;
    create table people (name_last, age);
    insert into people values ('Cho', 42);
  """)
  aquests.fetchall ()
  
  
Requests Parameters
========================

For get, post*, put*, upload, delete, options, trace parameters are the same.

.. code-block:: python

  aquests.get (url, params = None, headers = None, auth = None, meta = {})
  
- url: request url string
- params: None or dictionary, if it provide with get method, it will be attached on tail of url with '?'
- headers: None or dictionary
- auth: None or tuple (username, password)
- callback: substitude defaul callback
- meta: dictionary

For Websocket,

.. code-block:: python

  aquests.ws (url, params = None, headers = None, auth = None, meta = {})
  
- url: request url string, should start with 'ws://' or 'wss://'(SSL Websocket)
- params: string, bytes or tuple. if messages is not string you specify message type code using tuple like (ws.OPCODE_PING, b"hello"), you can find OPCODE list, 'from aquests.protocols import ws'. CAUTION. if your params type is bytes type, opcode will automatically be OPCODE_BINARY and string type, be OPCODE_TEXT. and opcode is inffluent to receiver. if you avoid auto opcode, specify opcode with tuple.
  
    * ws.OPCODE_TEXT
    * ws.OPCODE_BINARY
    * ws.OPCODE_CONTINUATION
    * ws.OPCODE_PING
    * ws.OPCODE_PONG
    * ws.OPCODE_CLOSE
    
- headers: None or dictionary
- auth: None or tuple (username, password)
- callback: substitude defaul callback
- meta: dictionary

For rpc, grpc stub creation:

.. code-block:: python

  stub = aquests.rpc (url, headers = None, auth = None, meta = {})
  stub = aquests.grpc (url, headers = None, auth = None, meta = {})
  
- url: request url string
- headers: None or dictionary
- auth: None or tuple (username, password)
- callback: substitude defaul callback
- meta: dictionary

Note: stub's methods and parameters are defined by RPC service providers

For postgresql, mongodb, redis dbo creation:

.. code-block:: python

  dbo = aquests.postgresql (server, dbname = None, auth = None, meta = {})
  dbo = aquests.mongodb (server, dbname = None, auth = None, meta = {})  
  dbo = aquests.redis (server, dbname = None, auth = None, meta = {})
  
- server: address:port formated string
- dbname: None or string
- auth: None or tuple (username, password)
- callback: substitude defaul callback
- meta: dictionary

Note: stub's methods and parameters are defined by database engines. Please read above related chapters But SQL based postgresql has only 1 method and parameters - execute(sql) or do(sql) just for your convinience.


History
=========

- 0.8
  
  - remove specific version dependancy with redis, pymongo 
  - support SQLAlchemy query statement object 
  - aquests.lib moved to new rs4 package, and aquests.lib has been removed

- 0.7.19

  - fix asyndns DNS server choicing

- 0.7.18

  - fix deleting item of await_fifo
  
- 0.7.16
  
  - add psutil to requirements.txt
  - fix killtree.kill
  - fix HTTP2 trailers
  - fix HTTP/2 remote flow control window
   
- 0.7.15

  - fix app/package reloading
  - fix HTTP/2 remote flow control window
  
- 0.7.13
    
  - add daemonizing command line handler
  - add JSON-RPC 2.0  

- 0.7.12
  
  - fix JWT token
  - remove grpc data compressing, it makes decrease overal performance 	
  - fix http2 connection limitation 
	
- 0.7.9
 
  - make sqlite3 to autocommit mode
  - switch DNS protocol on query failure
  - prevent same DNS server choice on query failure  
  - fix proxy DNS query
  - prevent same DNS server choice on DNS query failure
  - fix DNS query retry
  - add dns param to aquests.configure for user defined DSN server list
  - re-unify DNS sockets with main socket_map, it was bad idea
  - make keeping number of UDP DNS Client per DNS server
  - re-enginering DNS query and fix passing calllback args
  - DNS query ops has super priority to avoid network timeout, it makes reducing queury failures
  - change DNS query protocol from TCP to UDP pipelining
  - fix losting request handler
  - response content type and length validating using request headers
  
- 0.7.8
  
  - fix memory leaking cause by exception handling
  - set DNS minimum ttl value to 300
  - remove 1 second delay when DNS query failed
  - increase DNS query timeout
  - use select.select for asyncore.loop instead of select.poll for andling socket errors directly
  - add getjson, deletejson, this request automatically add header 'Accept: application/json'
  - change default request content-type from json to form data, if you post/put json data, you should change postjson/putjson    
  
- 0.7.7
  
  - fix sqlite3 execute ()
  - merge process related modele to aquests.lib.pmaster
  - add auto expiring on DNS cache
  - logger.trace () is now formatted to multi rows, if you analyze log files, should be reviewed
  - add parameter 'use_pool' to aquests.configure, you can set False when if you meet the OS error: too many open files
  - enter beta development status
  - fix error handling win32 select loop
  - add load.py for testing installation and your server

- 0.7.6
  
  - fix redicting
  - fix prefetch DNS
  - fix recursion error related to DNS query  
  - fix early termination when making http2 connection
  - fix http2 body posting
  - fix recursion error when massive DNS Error
  - retry after 1 seconds when DNS query failed
  - fix daemonizer.kill ()
  - adaptation to h2 3.0.1
  - fix delay when http concurrent stream = 1
  - fix handling psycopg2 poll () failure
  - reengineer select loop
  - fix DNS erro handling
  - fix HTTP/2 auto redirecting
  - fix HTTP/2 sockets over creation
  - add get_size () to all producers for estimating content length
  - increase socket out buffer from 4096 -> 65535
  
- 0.7.5
   
   - re-engineer await_fifo, http2_fifo
   - add lib.evbus
   - retry once if database is disconnected by keep-live timeout
   - change screen_logger for easy to read traceback information

- 0.7.4: 
  
  - fix incomplete sending when resuested with connection: close header
  
- 0.7.3: 
  
  - fix early termination when single worker
  - add PATCH method
  - use google public DNS for default
  - fix early termination in case of single worker

- 0.7.2: 
  
  - accept header validation with response content-type
  - change qrandom parameter's default value to False of aquests.configure ()

- 0.7.1: fix dns cache case sensitivity

- 0.7: 
  
  - fix redirecting and reauthorizing
  - dns query instacnt loop before being called fetchall ()
  - add callback arg for each request
  - fix redirect, improve asyndns, error codes related network error
  - redefine workers, workers mean nummber of connections
  - fix finish_request, and shutdown entering
  - fix FailedResponse's contents

- 0.6.14: add qrandom option for aquests.configure

- 0.6.13: fix response.json ()

- 0.6.11 

  - request & response.headers is NocaseDict
  - fix sqlite bugs, add response.uuid & rfc
  - fix sqlite.del_channel
  - add auqests.suspend

- 0.6.10: add response.lxml

- 0.6.8: add protocols.__init__.py

- 0.6.7: change socket closing log message

- 0.6.6: fix asyncon active

- 0.6.4.2: license changed from BSD to MIT

- 0.6.4.1: fix await_fifo bug

- 0.6.3: fix lifetime,  tmap

- 0.6.2: change queue list -> deque

- 0.6.1: fix websocket text data encoding

- 0.6: 
  
  * add configure option: allow_redirects
  * new response.history
  * fix 30x redirection
  * fix 401 unauthorized
  
- 0.5.2: remove ready_producer_fifo, this will be used only serverside
- 0.5.1: change from list to deque on producer_fifo
- 0.4.33: force_http1 applied to https
- 0.4.32: fix http.buffer.list_buffer class
- 0.4.30: add websocket message type detection
- 0.4.28: remove aquests.wss, use aquests.ws with url wss://...
- 0.4.25: fix select.select () divide and conquer
- 0.4.22: fix http2_constreams
- 0.4.21: fix http2 flow control window
- 0.4.20: add configure options: force_http1, http2_constreams
- 0.4.18: url / trailing
- 0.4.17: fix finding end of data on http2
- 0.4.16: fix http2 disconnecting behavior
- 0.4.10: fix xmlrpc stub url / trailing
- 0.4.9: changed response properties - request.method -> method, request.server -> server, request.dbname -> dbname and request.params -> params
- 0.4.4: add lib.athreads
- 0.4.2: fix http2 large content download
- 0.4.1: add a few examples
- 0.4: add timeout feature
- 0.3.10: fix http2 frame length validation, add cookie feature
- 0.3.8: fix dbo request shutdown behavior
- 0.3.1: add HEAD, OPTIONS, TRACE
- 0.3: fix installation error
- 0.2.13: change default display callback
- 0.2.10: fix xmlrpc

