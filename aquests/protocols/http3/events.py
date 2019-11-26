from aioquic.h3.events import H3Event, DataReceived, HeadersReceived, PushPromiseReceived
from dataclasses import dataclass

@dataclass
class ConnectionShutdownInitiated (H3Event):
    last_stream_id: int

@dataclass
class PushCanceled (H3Event):
    push_id: int

@dataclass
class MaxPushIdReceived (H3Event):
    push_id: int

@dataclass
class DuplicatePushReceived (H3Event):
    stream_id: int
    push_id: int
    stream_ended: bool = True
