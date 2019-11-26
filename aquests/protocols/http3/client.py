# This is NOT for production BUT just for unit test

import socket
from urllib.parse import urlparse
from aioquic.quic.connection import QuicConnection
from aioquic.quic.configuration import QuicConfiguration
from aioquic.h3.connection import H3_ALPN
from aioquic.quic import events
from .connection import H3Connection
import pickle
import os
import ssl
import ipaddress
import time
from aioquic.h3.events import DataReceived, H3Event, HeadersReceived, PushPromiseReceived
from .events import PushCanceled, MaxPushIdReceived, DuplicatePushReceived

class ConnectionClosed (Exception):
    pass

class URL:
    def __init__(self, url):
        parsed = urlparse(url)

        self.authority = parsed.netloc
        self.full_path = parsed.path
        if parsed.query:
            self.full_path += "?" + parsed.query
        self.scheme = parsed.scheme
        self.netloc = parsed.netloc

class HttpResponse:
    def __init__ (self):
        self.stream_id = None
        self.events = []
        self.promises = []
        self.headers = {}
        self.data = b''

class HttpRequest:
    def __init__(self, method, url, content = b"", headers = {}, allow_push = True):
        self.args = (method, url, content, headers, allow_push)
        self.content = content or b''
        if isinstance (self.content, str):
            self.content = self.content.encode("utf8")
        self.headers = headers
        self.method = method
        self.url = URL (url)
        self.allow_push = allow_push
        self.response = HttpResponse ()

    def clone (self):
        return HttpRequest (*self.args)


class Connection:
    session_ticket = '/tmp/http3-session-ticket.pik'
    socket_timeout = 1
    def __init__ (self, addr, enable_push = True):
        # prepare configuration
        self.netloc = addr
        try:
            host, port = addr.split (":", 1)
            port = int (port)
        except ValueError:
            host, port = addr, 443

        self.addr = (host, port)
        self.configuration = QuicConfiguration(is_client = True, alpn_protocols = H3_ALPN)
        self.configuration.load_verify_locations(os.path.join (os.path.dirname (__file__), 'pycacert.pem'))
        self.configuration.verify_mode = ssl.CERT_NONE
        self.load_session_ticket ()
        self.socket = socket.socket (socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout (self.socket_timeout)
        self._connected = False
        self._closed = False
        self._history = []
        self._allow_push = enable_push
        self._response = None

    def connect (self):
        host, port = self.addr
        try:
            ipaddress.ip_address(host)
            server_name = None
        except ValueError:
            server_name = host
        if server_name is not None:
            self.configuration.server_name = server_name
        self._quic = QuicConnection (
            configuration = self.configuration, session_ticket_handler = self.save_session_ticket
        )
        self._http = H3Connection(self._quic)
        self._quic.connect(self.addr, now=time.monotonic ())
        self.transmit ()

    def close (self):
        self.transmit ()
        self.recv ()
        #self.socket.close ()
        self._closed = True

    def transmit (self):
        dts = self._quic.datagrams_to_send(now=time.monotonic ())
        if not dts:
            return

        for data, addr in dts:
            #print ('<---', len (data), repr (data [:30]))
            sent = self.socket.sendto (data, self.addr)
        self.recv ()

    def recv (self):
        while 1:
            try:
                data, addr = self.socket.recvfrom (4096)
            except socket.timeout:
                break
            #print ('--->', len (data), repr (data [:30]))
            self._quic.receive_datagram(data, addr, now = time.monotonic ())
            self._process_events()
        self.transmit ()

    def save_session_ticket (self, ticket):
        with open(self.session_ticket, "wb") as fp:
            pickle.dump(ticket, fp)

    def load_session_ticket (self):
        try:
            with open(self.session_ticket, "rb") as fp:
                self.configuration.session_ticket = pickle.load(fp)
        except FileNotFoundError:
            pass

    def _process_events(self):
        event = self._quic.next_event()
        while event is not None:
            if isinstance(event, events.ConnectionTerminated):
                self._connected = False
                self.close ()
            elif isinstance(event, events.HandshakeCompleted):
                self._connected = True
            elif isinstance(event, events.PingAcknowledged):
                pass
            self.quic_event_received(event)
            event = self._quic.next_event()

    def http_event_received (self, http_event):
        if isinstance(http_event, HeadersReceived):
            self._response.headers = {k: v for k, v in http_event.headers}
        elif isinstance(http_event, DataReceived):
            if http_event.stream_id % 4 == 0:
                self._response.data += http_event.data
        elif isinstance(http_event, PushPromiseReceived):
            push_headers = {}
            for k, v in http_event.headers:
                push_headers [k.decode ()] = v.decode ()
            self._response.promises.append (push_headers)

    def quic_event_received (self, event):
        #  pass event to the HTTP layer
        if self._response and not isinstance (event, events.StreamDataReceived):
            self._response.events.append (event)

        for http_event in self._http.handle_event(event):
            if not isinstance (http_event, (HeadersReceived, PushPromiseReceived, DataReceived)):
                # logging only control frames
                self._response.events.append (http_event)
            self.http_event_received(http_event)

    def handle_request (self, request):
        if self._closed:
            raise ConnectionClosed

        if not self._connected:
            self.connect ()

        self._response = request.response
        stream_id = self._quic.get_next_available_stream_id()
        self._response.stream_id = stream_id
        self._http.send_headers(
            stream_id=stream_id,
            headers = [
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
        self._http.send_data (stream_id=stream_id, data=request.content, end_stream=True)
        self.transmit()

        self._response = None
        return request.response

    def get (self, url, headers = {}):
        req = HttpRequest ('GET', 'https://{}{}'.format (self.netloc, url), b'', headers)
        return self.handle_request (req)

    def post (self, url, data, headers = {}):
        req = HttpRequest ('POST', 'https://{}{}'.format (self.netloc, url), data, headers)
        return self.handle_request (req)

    def request (self, method, url, data = b'', headers = {}):
        req = HttpRequest (method, 'https://{}{}'.format (self.netloc, url), data, headers)
        return self.handle_request (req)
