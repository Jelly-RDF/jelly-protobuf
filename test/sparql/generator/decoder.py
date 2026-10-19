"""Helper script for the test generator: decodes Jelly-SPARQL streams.

It is strict: it rejects everything the specification says a consumer MUST or
SHOULD reject. The generator uses it to check that every positive test decodes
to its expected result, and that every negative test fails for the reason the
test is about.
"""

from dataclasses import dataclass

from generator_common import pb
from generator_common.coldec import (
    MAX_ROW_COUNT,
    V_1_2,
    ColumnReader,
    DecodeError,
    fail,
)
from generator_common.coldec import Limits as ColumnLimits
from model import AskResult, ResultSet

ST_FLAT, ST_PUNCTUATED = 0, 1


@dataclass
class Limits(ColumnLimits):
    supported_version: int = 1


def decode(data: bytes, limits: Limits = Limits()):
    try:
        return _Decoder(limits).run(data)
    except pb.DecodeError as e:
        raise DecodeError(f"protobuf: {e}")


class _Decoder(ColumnReader):
    def __init__(self, limits: Limits):
        self.limits = limits
        self.stream_type = None  # FLAT or PUNCTUATED, set by the first options
        self.results = []  # finished result sets (PUNCTUATED)
        self.new_result_set()
        self.trailer_seen = False

    def new_result_set(self):
        self.first = True  # the next frame is the first frame of a result set
        self.kind = None  # "select" or "ask"
        self.header = None  # variable names of the result set
        self.rows = []
        self.links = []
        self.ask_value = None

    def result(self):
        if self.kind == "ask":
            return AskResult(self.ask_value)
        return ResultSet(self.header, self.rows, self.links)

    def run(self, data: bytes):
        frames = pb.split_delimited(data)
        if not frames:
            fail("the stream contains no frames")
        for index, raw in enumerate(frames):
            self.frame(index, pb.Fields(raw))
        if self.stream_type == ST_FLAT:
            return self.result()
        if not self.first:
            # The last result set has no trailer: possibly truncated, but valid.
            self.results.append(self.result())
        return self.results

    # --- frames --------------------------------------------------------------

    def frame(self, index: int, f: pb.Fields):
        opts = f.msg(1)
        first = self.first
        self.first = False
        if self.kind == "ask" and not first:
            fail("a frame follows the frame with the boolean result")
        if self.stream_type == ST_FLAT and self.trailer_seen and opts is None:
            fail("a frame without the stream options follows a trailer")
        if self.stream_type == ST_PUNCTUATED and opts is not None and not first:
            fail("stream options in a frame other than the first frame of a result set")

        if opts is not None:
            self.options(opts)
        elif index == 0:
            fail("the first frame has no stream options")

        variables = f.strings(2)
        row_count = f.uint32(3)
        columns = f.msgs(7)
        ask = f.msg(8)

        # Lookup entries are applied before any column is decoded. A frame with a
        # boolean result may also have them, for the next result set to use.
        self.names.apply(f.msgs(4))
        self.prefixes.apply(f.msgs(5))
        self.datatypes.apply(f.msgs(6))

        if ask is not None:
            if not first:
                fail("a boolean result in a frame other than the first frame of a result set")
            if variables:
                fail("the frame with a boolean result declares variables")
            if columns:
                fail("the frame with a boolean result contains columns")
            if row_count != 0:
                fail("the frame with a boolean result has row_count != 0")
            self.kind = "ask"
            self.ask_value = ask.bool(1)
        else:
            if first:
                self.kind = "select"
            self.header_of(first or opts is not None, variables)
            self.body(row_count, columns)

        self.metadata(f)
        trailer = f.msg(9)
        if trailer is not None:
            self.trailer_seen = True
            error = trailer.string(1)
            if error:
                fail(f"error trailer: {error}")
            if self.stream_type == ST_PUNCTUATED:
                self.results.append(self.result())
                self.new_result_set()

    def options(self, o: pb.Fields):
        version = o.uint32(15)
        if version == 0:
            fail("version tag is 0")
        if version > self.limits.supported_version:
            fail(f"version tag {version} is newer than supported")
        stream_type = o.uint32(2)
        if stream_type > ST_PUNCTUATED:
            fail(f"unknown stream_type {stream_type}")
        if self.stream_type is not None and stream_type != self.stream_type:
            fail(f"stream_type {stream_type} differs from the stream_type {self.stream_type} of the stream")
        rdf_version = o.uint32(5)
        if rdf_version > V_1_2:
            fail(f"unknown rdf_version {rdf_version}")
        # A repeated options message resets the stream state.
        self.check_table_sizes(o.uint32(9), o.uint32(10), o.uint32(11))
        self.stream_type = stream_type
        self.rdf_version = rdf_version
        self.trailer_seen = False

    def header_of(self, declares: bool, names):
        if not declares:
            if names:
                fail("a header in a frame that is neither the first frame of the result set "
                     "nor a frame with the stream options")
            return
        # An empty header here declares a zero-variable result set.
        if self.header is None:
            self.header = names
        elif names != self.header:
            fail(
                "the header in a frame repeating the stream options does not "
                f"declare the variables of the first header: {names} != {self.header}"
            )

    def body(self, row_count: int, columns):
        n_vars = len(self.header)
        if row_count > MAX_ROW_COUNT:
            fail(f"row_count {row_count} is larger than 2^27 - 1")
        if not columns:
            if n_vars > 0 and row_count > 0:
                fail("a frame with rows but no columns")
            self.rows.extend({} for _ in range(row_count))
            return
        if len(columns) != n_vars:
            fail(f"the frame has {len(columns)} columns, but the header declares {n_vars} variables")
        cells = [self.column(c, row_count) for c in columns]
        for r in range(row_count):
            row = {}
            for v, name in enumerate(self.header):
                t = cells[v][r]
                if t is not None:
                    row[name] = t
            self.rows.append(row)

    def metadata(self, f: pb.Fields):
        for e in f.msgs(15):
            if e.string(1) != "link":
                continue
            raw = e.bytes(2, b"")
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue  # the spec says to ignore an invalid well-known key
            self.links = text.split("\n") if text else []
