======================
Asynchronous Requests
======================

Aquests is generating asynchronous requests and fetching data from HTTP2, REST API, XMLRPC, gRPC and sevral Database engines. It was seperated from Skitai_ on Jan 2017.

Supported requests are:

- HTTP/1.1
- HTTP/2.0 if target server provides
- Websocket
- XML-RPC
- gRPC
- PostgreSQL
- MongoDB
- Redis

.. _Skitai: https://pypi.python.org/pypi/skitai

.. contents:: Table of Contents


Quick Start
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

  REQID 635. HTTP/2.0 200 OK 4210 bytes received
  REQID 627. HTTP/2.0 200 OK 4210 bytes received
  REQID 594. HTTP/2.0 200 OK 4210 bytes received
  REQID 702. HTTP/2.0 200 OK 4210 bytes received
  REQID 685. HTTP/2.0 200 OK 4210 bytes received
  REQID 637. HTTP/2.0 200 OK 4210 bytes received
  REQID 591. HTTP/2.0 200 OK 4210 bytes received
  REQID 586. HTTP/2.0 200 OK 4210 bytes received
  (and scrolled fast...)

Installation
===============

**Requirements**

- `hyper-h2`_: HTTP/2 State-Machine based protocol implementation
- pymongo_: Python driver for MongoDB
- redis_: Python client for Redis key-value store

But these will be automatically installed, when aquests installed.

.. code-block:: bash

  pip install aquests


.. _`hyper-h2`: https://pypi.python.org/pypi/h2
.. _pymongo: https://pypi.python.org/pypi/pymongo
.. _redis: https://pypi.python.org/pypi/redis/2.10.5


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


Change Logger
--------------

.. code-block:: python
  
  from aquests.lib import logger
  
  aquests.configure (
    workers = 10, 
    logger = logger.file_logger ('/tmp/logs', 'aquests')
  )


Making Traffic Load
---------------------

.. code-block:: python
  
  numreq = 0
  limit = 100000
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

Set Meta Information
----------------------

.. code-block:: python
  
  def finish_request (response):
    print (response.meta ['req_id'])
    print (response.meta ['req_method'])
    print (response.meta ['job_name'])
  	
  aquests.configure (workers = 10, callback = finish_request)
  aquests.get ("http://127.0.0.1:5000/", meta = {'job_name': 'test1'})  
  aquests.get ("http://127.0.0.1:5000/", meta = {'job_name': 'test2'})

Note: meta ['req_id'] and meta ['req_method'] are automatically added by aquests.

Response
---------

Response has these attributes and method:

- meta: user added meta data including 'req_id'
- url: requested URL
- status_code: HTTP status code
- reason: status text like OK, Not Found...
- version: HTTP protocol version
- headers: Response headers
- content: bytes content
- text: encoded string
- data: usally same as content but on RPC, DB query situation, it returns result object.
- encoding: extracted from content-type header
- json (): load JSON data


List of Methods
==================

HTTP GET, DELETE
-----------------

.. code-block:: python

  aquests.get ("http://127.0.0.1:5000/")
  aquests.delete ("http://127.0.0.1:5000/models/ak-40")
  aquests.get ("https://www.google.co.kr/search?q=aquests")

Also aquests.delete () is available.


  
HTTP POST, PUT
---------------

.. code-block:: python

  aquests.post (
    "http://127.0.0.1:5000/", 
    {'author': 'James Milton'}, 
    {'Content-Type': 'application/x-www-form-urlencoded'}
   )
   
  # is equal to:
   
  aquests.postform (
    "http://127.0.0.1:5000/", 
    {'author': 'James Milton'}    
  )

Put example,

.. code-block:: python
  
  aquest.put (
    "http://127.0.0.1:5000/", 
    {'user': 'JamesMilton'},
    {'Content-Type': 'application/json'}
    )
  )
  
  # is equal to:
   
  aquests.putjson (
    "http://127.0.0.1:5000/", 
    {'user': 'JamesMilton'}
  )
  
There're some shorter ways ratehr than specifing content type:

- postform: application/x-www-form-urlencoded, data value should be dictionary
- postjson: application/json, data value should be json dumpable
- postxml: text/xml, data value should be xml string or utf-8 encoded bytes
- postnvp: text/namevalue, data value should be dictionary 

And putform (), putjson ()... is also available.

  
HTTP File Upload
------------------

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
  aquests.fetchall ()


XML-RPC
----------

.. code-block:: python

  stub = aquests.rpc ("https://pypi.python.org/pypi")
  stub.package_releases('roundup')
  stub.prelease_urls('roundup', '1.4.10')
  aquests.fetchall ()



gRPC
----------

.. code-block:: python
  
  import route_guide_pb2
  
  stub = aquests.grpc ("http://127.0.0.1:5000/routeguide.RouteGuide")
  point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
  for i in range (3):
    stub.GetFeature (point)
  aquests.fetchall ()

For more about gRPC and route_guide_pb2, go to here_.

.. _here: http://www.grpc.io/docs/tutorials/basic/go.html


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


Resis
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


History
=========

- 0.2.13: change default display callback
- 0.2.10: fix xmlrpc

