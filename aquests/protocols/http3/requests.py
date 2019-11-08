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
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import DataReceived, H3Event, HeadersReceived, PushPromiseReceived
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent
from aioquic.quic.logger import QuicLogger

try:
    import uvloop
except ImportError:
    uvloop = None

logger = logging.getLogger("client")

HttpConnection = Union[H0Connection, H3Connection]


class URL:
    def __init__(self, url: str):
        parsed = urlparse(url)

        self.authority = parsed.netloc
        self.full_path = parsed.path
        if parsed.query:
            self.full_path += "?" + parsed.query
        self.scheme = parsed.scheme


class HttpRequest:
    def __init__(
        self, method: str, url: URL, content: bytes = b"", headers: Dict = {}, allow_push: bool = True
    ) -> None:
        self.content = content
        self.headers = headers
        self.method = method
        self.url = url
        self.allow_push = allow_push



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

    async def get(self, url: str, headers: Dict = {}, allow_push: bool = True) -> Deque[H3Event]:
        return await self._request(
            HttpRequest(method="GET", url=URL(url), headers=headers, allow_push=allow_push)
        )

    async def post(self, url: str, data: bytes, headers: Dict = {}, allow_push: bool = True) -> Deque[H3Event]:
        return await self._request(
            HttpRequest(method="POST", url=URL(url), content=data, headers=headers, allow_push=allow_push)
        )

    def http_event_received(self, event: H3Event):
        if isinstance(event, (HeadersReceived, DataReceived, PushPromiseReceived)):
            stream_id = event.stream_id
            if stream_id in self._request_events:
                # http
                self._request_events[event.stream_id].append(event)
                if hasattr (event, 'stream_ended') and event.stream_ended:
                    request_waiter = self._request_waiter.pop(stream_id)
                    request_waiter.set_result(self._request_events.pop(stream_id))

    def quic_event_received(self, event: QuicEvent):
        #  pass event to the HTTP layer
        if self._http is not None:
            for http_event in self._http.handle_event(event):
                self.http_event_received(http_event)

    async def _request(self, request: HttpRequest):
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


def save_session_ticket(ticket):
    logger.info("New session ticket received")


class Response:
    promises = []
    headers = None
    data = b''

async def run(configuration: QuicConfiguration, url: str, data: str, headers: Dict = {}, allow_push: bool = True, response: Response = None) -> None:
    # parse URL
    parsed = urlparse(url)
    assert parsed.scheme in (
        "https"
    ), "Only https:// URLs are supported."

    if ":" in parsed.netloc:
        host, port_str = parsed.netloc.split(":")
        port = int(port_str)
    else:
        host = parsed.netloc
        port = 443

    async with connect(
        host,
        port,
        configuration=configuration,
        create_protocol=HttpClient,
        session_ticket_handler=save_session_ticket,
    ) as client:
        client = cast(HttpClient, client)

        if parsed.scheme == "wss":
            pass
        else:
            # perform request
            start = time.time()
            if data is not None:
                headers ['content-type'] = "application/x-www-form-urlencoded"
                http_events = await client.post(
                    url,
                    data=data.encode("utf8"),
                    headers = headers,
                    allow_push = allow_push
                )
            else:
                http_events = await client.get(url, headers, allow_push)
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

            # print response
            for http_event in http_events:
                if isinstance(http_event, HeadersReceived):
                    resp_headers = {}
                    for k, v in http_event.headers:
                        resp_headers [k.decode ()] = v.decode ()
                    response.headers = resp_headers
                elif isinstance(http_event, DataReceived):
                    response.data += http_event.data
                else:
                    # server push
                    if not allow_push:
                        if hasattr (client._http, 'send_cancel_push'):
                            client._http.send_cancel_push (http_event.push_id)
                            client.transmit()
                        continue
                    push_headers = {}
                    for k, v in http_event.headers:
                        push_headers [k.decode ()] = v.decode ()
                    response.promises.append (push_headers)


def _request (url, data = None, headers = {}, allow_push = True):
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )
    # prepare configuration
    configuration = QuicConfiguration(
        is_client=True, alpn_protocols=H3_ALPN
    )
    configuration.load_verify_locations(os.path.join (os.path.dirname (__file__), 'pycacert.pem'))
    configuration.verify_mode = ssl.CERT_NONE
    loop = asyncio.get_event_loop()
    response = Response ()
    loop.run_until_complete(
        run(configuration=configuration, url=url, data=data, headers = headers, allow_push = allow_push, response=response)
    )
    return response

def get (url, headers = {}, allow_push = True):
    return _request (url, headers = headers, allow_push = allow_push)

def post (url, data, headers = {}, allow_push = True):
    return _request (url, data, headers = headers, allow_push = allow_push)


if __name__ == "__main__":
    r = get ('https://localhost:4433/')
    print (r.headers)
    print (r.data)

