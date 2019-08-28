This is a another release of the pydns code, as originally written by 
Guido van Rossum, and nicer API bolted over the top of it by Anthony 
Baxter <anthony@interlink.com.au> and added asynchronous query feature
and a little modification for Python 3 competetable in 2015 by Hans Roh 
<hansroh@gmail.com>.


To use:

from skitai.lib import logger
from skitai.protocol.dns import asyndns
from rs4 import asyncore

import pprint
f = asyndns.Request (logger.screen_logger ())
f.req ("google.com", protocol = "tcp", callback = pprint.pprint, qtype="mx")
f.req ("www.google.com", protocol = "tcp", callback = pprint.pprint, qtype="a")
f.req ("www.google.com", protocol = "tcp", callback = pprint.pprint, qtype="ns")
asyncore.loop (timeout = 1)

