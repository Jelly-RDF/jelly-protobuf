"""Reference Jelly-RDF 1.2 consumer, written directly from the specification.

It is strict: it rejects everything the specification says a consumer MUST or
SHOULD reject. The generator uses it to check that every positive test decodes
to its expected result, and that every negative test fails for the reason the
test is about.

It reads only streams with version tag 3 (the column layout). Streams with
version tags 1 and 2 follow the Jelly-RDF 1.1 specification, and are tested
by the Jelly-RDF 1.1 test suite.
"""

from generator_common import pb
from generator_common.coldec import (
    MAX_ROW_COUNT,
    V_1_2,
    ColumnReader,
    DecodeError,
    Limits,
    fail,
)
from model import Bnode, Iri, St, Triple

VERSION = 3
TRIPLES, QUADS, GRAPHS = 1, 2, 3
FLAT, MESSAGES = 0, 1
ROW_LAYOUT_ROWS = {2: "triple", 3: "quad", 4: "graph_start", 5: "graph_end", 6: "namespace",
                   9: "name", 10: "prefix", 11: "datatype"}
COLUMNS = {6: "subjects", 7: "predicates", 8: "objects", 9: "graphs"}


def decode(data: bytes, delimited: bool = True, limits: Limits = Limits()):
    """Decode a stream: a list of statements (FLAT), or a list of messages (MESSAGES)."""
    return decode_stream(data, delimited, limits)[0]


def decode_stream(data: bytes, delimited: bool = True, limits: Limits = Limits()):
    """Like decode, but returns (result, physical type, stream type)."""
    try:
        frames = pb.split_delimited(data) if delimited else [data]
        d = _Decoder(limits)
        result = d.run(frames)
    except pb.DecodeError as e:
        raise DecodeError(f"protobuf: {e}")
    return result, d.physical_type, d.stream_type


class _Decoder(ColumnReader):
    def __init__(self, limits: Limits):
        self.limits = limits
        self.physical_type = None  # set by the first stream options
        self.stream_type = None
        self.statements = []  # FLAT: all statements
        self.messages = []  # MESSAGES: finished messages
        self.current = []  # MESSAGES: statements of the current message
        self.namespaces = {}

    def run(self, frames):
        for raw in frames:
            self.frame(pb.Fields(raw))
        if self.stream_type == MESSAGES:
            self.end_of_messages()
            return self.messages
        return self.statements

    def end_of_messages(self):
        """End of the stream, or restated options: the open message ends if it has statements."""
        if self.current:
            self.messages.append(self.current)
        self.current = []

    # --- frames --------------------------------------------------------------

    def frame(self, f: pb.Fields):
        rows = f.msgs(1)
        if len(rows) > 1:
            fail(f"the frame has {len(rows)} rows")
        if rows:
            row = rows[0]
            other = sorted(n for n in row.raw if n != 1)
            if other:
                fail("a row with a field other than options: "
                     + ", ".join(ROW_LAYOUT_ROWS.get(n, str(n)) for n in other))
            if row.has(1):
                self.options(row.msg(1))
        if f.has(2):
            if self.physical_type is None:
                fail("a column batch before any stream options")
            self.batch(f.msg(2))

    def options(self, o: pb.Fields):
        version = o.uint32(15)
        if version == 0:
            fail("version tag is 0")
        if version > VERSION:
            fail(f"version tag {version} is newer than supported")
        if version < VERSION:
            fail(f"version tag {version}: a Jelly-RDF 1.1 stream, out of the scope of this decoder")
        for num, name in ((3, "generalized_statements"), (4, "rdf_star"), (14, "logical_type")):
            if o.uint32(num):
                fail(f"{name} is set, but it is used only in Jelly-RDF 1.0.x and 1.1.x")
        physical = o.uint32(2)
        if physical == 0:
            fail("physical_type is unspecified")
        if physical == GRAPHS:
            fail("physical_type GRAPHS, which is used only in Jelly-RDF 1.0.x and 1.1.x")
        if physical > GRAPHS:
            fail(f"unknown physical_type {physical}")
        stream_type = o.uint32(5)
        if stream_type > MESSAGES:
            fail(f"unknown stream_type {stream_type}")
        if self.physical_type is not None and physical != self.physical_type:
            fail(f"physical_type {physical} differs from the physical_type {self.physical_type} of the stream")
        if self.stream_type is not None and stream_type != self.stream_type:
            fail(f"stream_type {stream_type} differs from the stream_type {self.stream_type} of the stream")
        rdf_version = o.uint32(6)
        if rdf_version > V_1_2:
            fail(f"unknown rdf_version {rdf_version}")
        # The stream options empty the lookups, also when they are restated.
        self.check_table_sizes(o.uint32(9), o.uint32(10), o.uint32(11))
        if self.stream_type == MESSAGES:
            self.end_of_messages()
        self.physical_type = physical
        self.stream_type = stream_type

    # --- batches -------------------------------------------------------------

    def batch(self, b: pb.Fields):
        n = b.uint32(1)
        if n > MAX_ROW_COUNT:
            fail(f"row_count {n} is larger than 2^27 - 1")
        # 1. Lookup entries.
        self.names.apply(b.msgs(2))
        self.prefixes.apply(b.msgs(3))
        self.datatypes.apply(b.msgs(4))
        # 2. Namespace declarations: one IRI sequence per batch.
        state = [0, 0]
        for ns in b.msgs(5):
            value = ns.msg(2)
            self.namespaces[ns.string(1)] = self.triple_iri(value or pb.Fields(b""), state)
        # 3. Statements.
        if self.physical_type == TRIPLES and b.has(9):
            fail("a graphs column in a stream of physical type TRIPLES")
        cells = {}
        for num, name in COLUMNS.items():
            c = b.msg(num) or pb.Fields(b"")
            cells[name] = self.column(c, n)
        for name in ("subjects", "predicates", "objects"):
            if any(t is None for t in cells[name]):
                fail(f"an unbound cell in the {name} column")
        self.check_types(cells["subjects"], "subjects", (Iri, Bnode))
        self.check_types(cells["predicates"], "predicates", (Iri,))
        self.check_types(cells["graphs"], "graphs", (Iri, Bnode, type(None)))
        statements = [
            St(*(cells[name][i] for name in COLUMNS.values()))
            for i in range(n)
        ]
        lengths = b.uint32s(15)
        if self.stream_type == FLAT:
            if lengths:
                fail("message_lengths in a FLAT stream")
            self.statements += statements
            return
        if sum(lengths) > n:
            fail(f"the message_lengths add up to {sum(lengths)}, more than row_count {n}")
        pos = 0
        for length in lengths:
            self.current += statements[pos:pos + length]
            pos += length
            self.messages.append(self.current)
            self.current = []
        self.current += statements[pos:]

    def check_types(self, cells, name, allowed):
        for t in cells:
            if not isinstance(t, allowed):
                kind = {Iri: "an IRI", Bnode: "a blank node", Triple: "a triple term"}.get(type(t), "a literal")
                fail(f"{kind} in the {name} column")
