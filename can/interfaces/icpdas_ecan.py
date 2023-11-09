"""
Interface for ECAN CAN Bus gateways manufactured by ICP DAS.
"""

from typing import Any, Optional, Tuple
from can import BusABC
from can.message import Message
import can.typechecking
import socket

DEFAULT_PORT = 10003

def encode_message(msg: Message) -> bytes:
    buf = bytearray()
    # 1-byte prefix depending on whether this is a standard/extended and data/remote frame
    if msg.is_remote_frame:
        if msg.is_extended_id:
            buf.extend(b"E")
        else:
            buf.extend(b"T")
    else:
        if msg.is_extended_id:
            buf.extend(b"e")
        else:
            buf.extend(b"t")
    # encode the id
    if msg.is_extended_id:
        buf.extend(f"{msg.arbitration_id:08x}".encode("ascii"))
    else:
        buf.extend(f"{msg.arbitration_id:03x}".encode("ascii"))
    buf.extend(f"{len(msg.data):01x}".encode("ascii"))
    if not msg.is_remote_frame:
        buf.extend("".join([f"{b:02x}" for b in msg.data]).encode("ascii"))

    assert len(buf) == 1 + (8 if msg.is_extended_id else 3) + 1 + (len(msg.data) * 2)

    buf.extend(b"\r")
    return buf

def decode_message(raw: bytes) -> Message:
    flag = raw[0:1]
    if flag not in [b"e", b"E", b"t", b"T"]:
        raise ValueError(f"Unexpected flag: {raw[0]}")
    is_extended = flag in (b"e", b"E")
    is_remote = flag in (b"T", b"E")
    id_ = int((raw[1:9] if is_extended else raw[1:4]).decode("ascii"), 16)
    length = int(raw[9:10] if is_extended else raw[4:5], 16)
    return Message(
        arbitration_id=id_,
        is_extended_id=is_extended,
        is_remote_frame=is_remote,
        dlc=length,
        data=bytes.fromhex(raw[(10 if is_extended else 5):].decode("ascii")),
        check=True,
    )


class ICPDASEcanBus(BusABC):
    def __init__(self, channel: str, port: int = DEFAULT_PORT, can_filters: can.typechecking.CanFilters | None = None, **kwargs: object):
        super().__init__(channel, can_filters, **kwargs)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((channel, port))
        self.raw_buf = bytearray()

    def _recv_internal(self, timeout: float | None) -> Tuple[Message | None, bool]:
        # If we have stuff in the buffer, decode it
        while b"\r" not in self.raw_buf:
        # TODO: nonblocking?
            self.raw_buf.extend(self._sock.recv(4096))
        raw_msg, rest = self.raw_buf.split(b"\r", maxsplit=1)
        self.raw_buf = rest
        try:
            return decode_message(raw_msg), False
        except ValueError as e:
            print("error decoding message: ", e)
            return None, False

    def send(self, msg: Message, timeout: float | None = None) -> None:
       self._sock.send(encode_message(msg))