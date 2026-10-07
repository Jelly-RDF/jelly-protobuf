"""Minimal Protocol Buffers wire format encoder and decoder.

Only what the Jelly-SPARQL test fixtures need: varints, length-delimited
fields, and packed repeated varints. No dependencies, so that the generator
runs with a plain Python 3 installation.

The encoder does not know the schema. It writes exactly the fields it is
given, which is what lets the test cases build deliberately invalid frames.
"""


class DecodeError(Exception):
    """The bytes are not valid Protocol Buffers wire format."""


def varint(n: int) -> bytes:
    if n < 0:
        n += 1 << 64
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


class Msg:
    """Builder for one message. Fields are written in the order they are added.

    A field whose value is None is skipped. Message fields are always written,
    even when empty, because an empty sub-message is still "set".
    """

    def __init__(self):
        self._parts = []

    def _key(self, num: int, wire_type: int):
        self._parts.append(varint((num << 3) | wire_type))

    def uint(self, num: int, value):
        if value is not None:
            self._key(num, 0)
            self._parts.append(varint(value))
        return self

    def bool(self, num: int, value):
        if value is not None:
            self.uint(num, 1 if value else 0)
        return self

    def bytes(self, num: int, value):
        if value is not None:
            self._key(num, 2)
            self._parts.append(varint(len(value)))
            self._parts.append(value)
        return self

    def string(self, num: int, value):
        if value is not None:
            self.bytes(num, value.encode("utf-8"))
        return self

    def msg(self, num: int, value):
        if value is not None:
            self.bytes(num, value.encode() if isinstance(value, Msg) else value)
        return self

    def msgs(self, num: int, values):
        for v in values or []:
            self.msg(num, v)
        return self

    def strings(self, num: int, values):
        for v in values or []:
            self.string(num, v)
        return self

    def packed(self, num: int, values):
        if values:
            self.bytes(num, b"".join(varint(v) for v in values))
        return self

    def encode(self) -> bytes:
        return b"".join(self._parts)


def delimited(messages) -> bytes:
    """Write messages in the delimited variant: each prefixed with its length."""
    out = bytearray()
    for m in messages:
        b = m.encode() if isinstance(m, Msg) else m
        out += varint(len(b))
        out += b
    return bytes(out)


# --- decoding ---------------------------------------------------------------


def read_varint(buf: bytes, pos: int):
    result = 0
    shift = 0
    while True:
        if pos >= len(buf):
            raise DecodeError("truncated varint")
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, pos
        shift += 7
        if shift >= 70:
            raise DecodeError("varint too long")


def split_delimited(data: bytes):
    frames = []
    pos = 0
    while pos < len(data):
        length, pos = read_varint(data, pos)
        if pos + length > len(data):
            raise DecodeError("truncated delimited message")
        frames.append(data[pos : pos + length])
        pos += length
    return frames


class Fields:
    """Parsed fields of one message: field number -> list of raw values.

    Varint fields are ints, length-delimited fields are bytes.
    """

    def __init__(self, buf: bytes):
        self.raw = {}
        pos = 0
        while pos < len(buf):
            key, pos = read_varint(buf, pos)
            num, wire_type = key >> 3, key & 7
            if num == 0:
                raise DecodeError("field number 0")
            if wire_type == 0:
                value, pos = read_varint(buf, pos)
            elif wire_type == 2:
                length, pos = read_varint(buf, pos)
                if pos + length > len(buf):
                    raise DecodeError("truncated length-delimited field")
                value = buf[pos : pos + length]
                pos += length
            elif wire_type == 1:
                value, pos = buf[pos : pos + 8], pos + 8
            elif wire_type == 5:
                value, pos = buf[pos : pos + 4], pos + 4
            else:
                raise DecodeError(f"unsupported wire type {wire_type}")
            self.raw.setdefault(num, []).append((wire_type, value))

    def has(self, num: int) -> bool:
        return num in self.raw

    def uint32(self, num: int, default=0) -> int:
        if num not in self.raw:
            return default
        wire_type, value = self.raw[num][-1]
        if wire_type != 0:
            raise DecodeError(f"field {num}: expected a varint")
        return value & 0xFFFFFFFF

    def bool(self, num: int) -> bool:
        return self.uint32(num) != 0

    def bytes(self, num: int, default=None):
        if num not in self.raw:
            return default
        wire_type, value = self.raw[num][-1]
        if wire_type != 2:
            raise DecodeError(f"field {num}: expected a length-delimited value")
        return value

    def string(self, num: int, default=""):
        b = self.bytes(num)
        if b is None:
            return default
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            raise DecodeError(f"field {num}: invalid UTF-8")

    def msg(self, num: int):
        """A singular message field, or None if not set."""
        b = self.bytes(num)
        return None if b is None else Fields(b)

    def msgs(self, num: int):
        out = []
        for wire_type, value in self.raw.get(num, []):
            if wire_type != 2:
                raise DecodeError(f"field {num}: expected a message")
            out.append(Fields(value))
        return out

    def strings(self, num: int):
        out = []
        for wire_type, value in self.raw.get(num, []):
            if wire_type != 2:
                raise DecodeError(f"field {num}: expected a string")
            try:
                out.append(value.decode("utf-8"))
            except UnicodeDecodeError:
                raise DecodeError(f"field {num}: invalid UTF-8")
        return out

    def uint32s(self, num: int):
        """A repeated uint32 field, packed or not."""
        out = []
        for wire_type, value in self.raw.get(num, []):
            if wire_type == 0:
                out.append(value & 0xFFFFFFFF)
            elif wire_type == 2:
                pos = 0
                while pos < len(value):
                    v, pos = read_varint(value, pos)
                    out.append(v & 0xFFFFFFFF)
            else:
                raise DecodeError(f"field {num}: expected varints")
        return out
