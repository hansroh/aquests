# This is NOT for production BUT just for unit test

import argparse
import asyncio
import json
import logging
import pickle
import ssl
import sys
import time
from collections import deque
from typing import Callable, Deque, Dict, List, Optional, Union, cast
from urllib.parse import urlparse
import os

from aioquic.asyncio.client import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h0.connection import H0_ALPN, H0Connection
from aioquic.h3.connection import H3_ALPN
from .connection import H3Connection
from .events import DuplicatePushReceived
from aioquic.h3.events import DataReceived, H3Event, HeadersReceived, PushPromiseReceived
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent, ConnectionTerminated, StreamDataReceived
from aioquic.quic.logger import QuicLogger
from .client import URL, HttpResponse, HttpRequest

try:
    import uvloop
except ImportError:
    uvloop = None

logger = logging.getLogger("client")

HttpConnection = Union[H0Connection, H3Connection]

EVENT_HISTORY = []
class HttpClient(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._http: Optional[HttpConnection] = None
        self._request_events: Dict[int, Deque[H3Event]] = {}
        self._request_waiter: Dict[int, asyncio.Future[Deque[H3Event]]] = {}

        if self._quic.configuration.alpn_protocols[0].startswith("hq-"):
            self._http = H0Connection(self._quic)
        else:
            self._http = H3Connection(self._quic)
        self._push = {}
        self._recent_stream_id = 0

    def http_event_received(self, event):
        if hasattr (event, 'stream_id'):
            stream_id = event.stream_id
            if stream_id in self._request_events:
                self._recent_stream_id = stream_id
                self._request_events[event.stream_id].append(event)
                if hasattr (event, 'stream_ended') and event.stream_ended:
                    request_waiter = self._request_waiter.pop(stream_id)
                    request_waiter.set_result(self._request_events.pop(stream_id))

    def quic_event_received(self, event):
        #  pass event to the HTTP layer
        if not isinstance (event, StreamDataReceived):
            EVENT_HISTORY.append (event)

        if self._http is not None:
            for http_event in self._http.handle_event(event):
                #print ('-----------', http_event)
                if not isinstance (event, (HeadersReceived, PushPromiseReceived, DataReceived)):
                    # logging only control frames
                    EVENT_HISTORY.append (http_event)
                self.http_event_received(http_event)
        if self._request_waiter and isinstance (event, ConnectionTerminated):
            loop = asyncio.get_event_loop()
            loop.stop ()

    async def handle_request(self, request):
        stream_id = self._quic.get_next_available_stream_id()
        self._http.send_headers(
            stream_id=stream_id,
            headers=[
                (b":method", request.method.encode("utf8")),
                (b":scheme", request.url.scheme.encode("utf8")),
                (b":authority", request.url.authority.encode("utf8")),
                (b":path", request.url.full_path.encode("utf8")),
                (b"user-agent", b"aioquic"),
            ]
            + [
                (k.encode("utf8"), v.encode("utf8"))
                for (k, v) in request.headers.items()
            ],
        )
        self._http.send_data(stream_id=stream_id, data=request.content, end_stream=True)

        self.waiter = waiter = self._loop.create_future()
        self._request_events[stream_id] = deque()
        self._request_waiter[stream_id] = waiter
        self.transmit()

        return await asyncio.shield(waiter)

SESSION_TICKET = '/tmp/http3-session-ticket.pik'
def save_session_ticket(ticket):
    logger.info("New session ticket received")
    with open(SESSION_TICKET, "wb") as fp:
        pickle.dump(ticket, fp)


async def perform_http_request(client, req):
    # perform request
    start = time.time()
    http_events = await client.handle_request(req)
    elapsed = time.time() - start

    # print speed
    octets = 0
    for http_event in http_events:
        if isinstance(http_event, DataReceived):
            octets += len(http_event.data)
    logger.info(
        "Received %d bytes in %.1f s (%.3f Mbps)"
        % (octets, elapsed, octets * 8 / elapsed / 1000000)
    )

    response = req.response
    for http_event in http_events:
        response.events.append (http_event)
        if isinstance(http_event, HeadersReceived):
            resp_headers = {}
            for k, v in http_event.headers:
                resp_headers [k] = v
            response.headers = resp_headers
        elif isinstance(http_event, DataReceived):
            response.data += http_event.data
        elif isinstance(http_event, PushPromiseReceived):
            # server push
            if not req.allow_push:
                if hasattr (client._http, 'cancel_push'):
                    client._http.cancel_push (http_event.push_id)
                    client.transmit()
                continue
            push_headers = {}
            for k, v in http_event.headers:
                push_headers [k.decode ()] = v.decode ()
            response.promises.append (push_headers)


async def run(configuration, reqs, repeat = 1):
    if not isinstance (reqs, list):
        reqs = [reqs]

    netlocs = set ()
    for req in reqs:
        assert req.url.scheme == "https", "Only https:// URLs are supported."
        if ":" in req.url.netloc:
            host, port_str = req.url.netloc.split(":")
            port = int(port_str)
        else:
            host = req.url.netloc
            port = 443
        netlocs.add ((host, port))
        assert len (netlocs) == 1, 'different netloc'

    async with connect(
        host,
        port,
        configuration=configuration,
        create_protocol=HttpClient,
        session_ticket_handler=save_session_ticket,
    ) as client:
        client = cast(HttpClient, client)

        # perform request
        coros = []
        for req in reqs:
            coros.extend ([perform_http_request(client, i == 0 and req or req.clone ()) for i in range (repeat)])
        await asyncio.gather(*coros)


class MultiCall:
    def __init__ (self, endpoint):
        self._calls = []
        self.endpoint = endpoint

         # prepare configuration
        self.configuration = QuicConfiguration(
            is_client=True, alpn_protocols=H3_ALPN
        )
        self.configuration.load_verify_locations(os.path.join (os.path.dirname (__file__), 'pycacert.pem'))
        self.configuration.verify_mode = ssl.CERT_NONE
        try:
            with open(SESSION_TICKET, "rb") as fp:
                self.configuration.session_ticket = pickle.load(fp)
        except FileNotFoundError:
            pass

    @property
    def control_event_history (self):
        global EVENT_HISTORY
        eh, EVENT_HISTORY = EVENT_HISTORY, []
        return eh

    def get (self, url, headers = {}, allow_push = True, repeat = 1):
        self._calls.append (HttpRequest ('GET', self.endpoint + url, b'', headers, allow_push))

    def post (self, url, data, headers = {}, allow_push = True, repeat = 1):
        self._calls.append (HttpRequest ('POST', self.endpoint + url, data, headers, allow_push))

    def request (self):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(run(self.configuration, self._calls))
        except RuntimeError:
            pass
        return [req.response for req in self._calls]



if __name__ == "__main__":
    r = get ('https://localhost:4433/')
    print (r.headers)
    print (r.data)
