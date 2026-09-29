"""Reference Jelly-SPARQL consumer, written directly from the specification.

It is strict: it rejects everything the specification says a consumer MUST or
SHOULD reject. The generator uses it to check that every positive test decodes
to its expected result, and that every negative test fails for the reason the
test is about.
"""

from dataclasses import dataclass

import pb
from model import (
    RDF_DIR_LANG_STRING,
    RDF_LANG_STRING,
    AskResult,
    Bnode,
    Iri,
    Lit,
    ResultSet,
    Triple,
)

MAX_ROW_COUNT = (1 << 27) - 1
DIRECTIONS = {0: None, 1: "ltr", 2: "rtl"}
V_UNSPECIFIED, V_1_1, V_1_2_BASIC, V_1_2 = 0, 1, 2, 3
SUB_NAMES = ["iris", "literals", "bnodes", "triple_terms"]


class SparqlDecodeError(Exception):
    pass


@dataclass
class Limits:
    """The largest lookup tables the consumer accepts (the spec's defaults)."""

    max_name: int = 16384
    max_prefix: int = 4096
    max_datatype: int = 256
    supported_version: int = 1
    max_nesting: int = 64


class Lookup:
    def __init__(self, what: str, size: int):
        self.what = what
        self.size = size
        self.table = [None] * (size + 1)
        self.last_id = 0

    def apply(self, entries):
        for e in entries:
            id = e.uint32(1)
            values = e.strings(2)
            if id == 0:
                id = self.last_id + 1
            for v in values:
                if self.size == 0:
                    fail(f"{self.what} lookup entry, but the {self.what} lookup is disabled")
                if id < 1 or id > self.size:
                    fail(f"{self.what} lookup entry id {id} outside of the table (size {self.size})")
                self.table[id] = v
                self.last_id = id
                id += 1

    def get(self, id: int) -> str:
        if id < 1 or id > self.size:
            fail(f"{self.what} id {id} outside of the table (size {self.size})")
        v = self.table[id]
        if v is None:
            fail(f"{self.what} id {id} refers to an empty lookup entry")
        return v


def fail(msg: str):
    raise SparqlDecodeError(msg)


def decode(data: bytes, limits: Limits = Limits()):
    try:
        return _Decoder(limits).run(data)
    except pb.DecodeError as e:
        raise SparqlDecodeError(f"protobuf: {e}")


class _Decoder:
    def __init__(self, limits: Limits):
        self.limits = limits
        self.kind = None  # "select" or "ask"
        self.header = None  # variable names of the first header
        self.mapping = None  # column index per variable, header in effect
        self.rows = []
        self.links = []
        self.ask_value = None
        self.trailer_seen = False

    def run(self, data: bytes):
        frames = pb.split_delimited(data)
        if not frames:
            fail("the stream contains no frames")
        for index, raw in enumerate(frames):
            self.frame(index, pb.Fields(raw))
        if self.kind == "ask":
            return AskResult(self.ask_value)
        return ResultSet(self.header, self.rows, self.links)

    # --- frames --------------------------------------------------------------

    def frame(self, index: int, f: pb.Fields):
        opts = f.msg(1)
        if self.kind == "ask":
            fail("a frame follows the frame with the boolean result")
        if self.trailer_seen and opts is None:
            fail("a frame without the stream options follows a trailer")

        if opts is not None:
            self.options(opts)
        elif index == 0:
            fail("the first frame has no stream options")

        variables = [(v.string(1), v.uint32(2)) for v in f.msgs(2)]
        row_count = f.uint32(3)
        columns = (
            [("iri", c) for c in f.msgs(7)]
            + [("bnode", c) for c in f.msgs(8)]
            + [("literal", c) for c in f.msgs(9)]
            + [("poly", c) for c in f.msgs(10)]
        )
        ask = f.msg(11)

        if ask is not None:
            if index != 0:
                fail("a boolean result in a frame other than the first")
            if variables:
                fail("the frame with a boolean result declares variables")
            if columns:
                fail("the frame with a boolean result contains columns")
            if row_count != 0:
                fail("the frame with a boolean result has row_count != 0")
            self.kind = "ask"
            self.ask_value = ask.bool(1)
        else:
            if index == 0:
                self.kind = "select"
            # Lookup entries are applied before any column is decoded.
            self.names.apply(f.msgs(4))
            self.prefixes.apply(f.msgs(5))
            self.datatypes.apply(f.msgs(6))
            self.header_of(opts is not None, variables)
            self.body(row_count, columns)

        self.metadata(f)
        trailer = f.msg(12)
        if trailer is not None:
            self.trailer_seen = True
            error = trailer.string(1)
            if error:
                fail(f"error trailer: {error}")

    def options(self, o: pb.Fields):
        version = o.uint32(15)
        if version == 0:
            fail("version tag is 0")
        if version > self.limits.supported_version:
            fail(f"version tag {version} is newer than supported")
        rdf_version = o.uint32(5)
        if rdf_version > V_1_2:
            fail(f"unknown rdf_version {rdf_version}")
        name, prefix, dt = o.uint32(9), o.uint32(10), o.uint32(11)
        if name < 128:
            fail(f"max_name_table_size {name} is below the minimum of 128")
        if name > self.limits.max_name:
            fail(f"max_name_table_size {name} is larger than the consumer accepts")
        if prefix > self.limits.max_prefix:
            fail(f"max_prefix_table_size {prefix} is larger than the consumer accepts")
        if dt > self.limits.max_datatype:
            fail(f"max_datatype_table_size {dt} is larger than the consumer accepts")
        self.rdf_version = rdf_version
        # A repeated options message resets the stream state.
        self.names = Lookup("name", name)
        self.prefixes = Lookup("prefix", prefix)
        self.datatypes = Lookup("datatype", dt)
        self.mapping = None
        self.trailer_seen = False

    def header_of(self, has_options: bool, variables):
        names = [n for n, _ in variables]
        if has_options:
            # An empty header here declares a zero-variable result set.
            if self.header is None:
                self.header = names
            elif names != self.header:
                fail(
                    "the header in a frame repeating the stream options does not "
                    f"declare the variables of the first header: {names} != {self.header}"
                )
        elif variables:
            if names != self.header:
                fail(f"a restated header declares different variables: {names} != {self.header}")
        else:
            return  # header not restated, the one in effect stays
        indices = [i for _, i in variables]
        if sorted(indices) != list(range(len(indices))):
            fail(f"column indices {indices} are not a permutation of 0..{len(indices) - 1}")
        self.mapping = indices

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
        cells = [self.column(kind, c, row_count) for kind, c in columns]
        for r in range(row_count):
            row = {}
            for v, name in enumerate(self.header):
                t = cells[self.mapping[v]][r]
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

    # --- columns -------------------------------------------------------------

    def column(self, kind: str, c: pb.Fields, n: int):
        if kind == "iri":
            values = self.iri_values(c)
        elif kind == "bnode":
            values = [Bnode(v) for v in c.strings(1)]
        elif kind == "literal":
            values = self.literal_values(c)
        else:
            values = self.poly_values(c)
        return layout(values, c.uint32s(2), n)

    def iri_values(self, c: pb.Fields):
        name_ids = c.uint32s(1)
        prefix_ids = c.uint32s(3)
        m = len(name_ids)
        if len(prefix_ids) not in (0, 1, m):
            fail(f"prefix_ids has {len(prefix_ids)} entries for {m} values")
        out = []
        prev_name = prev_prefix = 0
        for j, nid in enumerate(name_ids):
            nid = nid or prev_name + 1
            prev_name = nid
            if not prefix_ids:
                pid = 0
            elif len(prefix_ids) == 1:
                pid = prefix_ids[0]
            else:
                pid = prefix_ids[j] or prev_prefix
                prev_prefix = pid
            out.append(Iri(self.resolve_iri(pid, nid)))
        return out

    def resolve_iri(self, pid: int, nid: int) -> str:
        prefix = "" if pid == 0 else self.prefixes.get(pid)
        return prefix + self.names.get(nid)

    def literal_values(self, c: pb.Fields):
        lex = c.strings(1)
        kinds = c.uint32s(3)
        langtags = c.strings(4)
        dirs = c.uint32s(5)
        m = len(lex)
        if len(kinds) not in (0, 1, m):
            fail(f"literal_kinds has {len(kinds)} entries for {m} values")
        if len(dirs) not in (0, len(langtags)):
            fail(f"langtag_directions has {len(dirs)} entries for {len(langtags)} language tags")
        # Only the directions of the language tags that are used are checked.
        dirs = dirs or [0] * len(langtags)
        out = []
        for j, x in enumerate(lex):
            k = 0 if not kinds else kinds[0] if len(kinds) == 1 else kinds[j]
            if k == 0:
                out.append(Lit(x))
            elif k % 2 == 1:
                out.append(Lit(x, self.datatype((k + 1) // 2)))
            else:
                index = k // 2 - 1
                if index >= len(langtags):
                    fail(f"literal kind {k} refers to language tag {index}, "
                         f"but the column has {len(langtags)} language tags")
                out.append(Lit(x, None, langtags[index], self.direction(dirs[index])))
        return out

    def poly_values(self, c: pb.Fields):
        # The layouts of the sub-columns are ignored.
        iris, literals, bnodes = c.msg(3), c.msg(4), c.msg(5)
        state = [0, 0]
        subs = [
            self.iri_values(iris) if iris else [],
            self.literal_values(literals) if literals else [],
            [Bnode(v) for v in bnodes.strings(1)] if bnodes else [],
            [self.triple(t, state, 1) for t in c.msgs(6)],
        ]
        total = sum(len(x) for x in subs)
        kinds = c.bytes(1, b"")
        if len(kinds) != (total + 3) // 4:
            fail(f"kinds has {len(kinds)} bytes for {total} values")
        if total % 4 and kinds[-1] >> (2 * (total % 4)):
            fail("the unused bits of the last byte of kinds are not 0")
        next_of = [0, 0, 0, 0]
        out = []
        for j in range(total):
            k = (kinds[j // 4] >> (2 * (j % 4))) & 3
            if next_of[k] >= len(subs[k]):
                fail(f"kinds refers past the end of the {SUB_NAMES[k]} sub-column")
            out.append(subs[k][next_of[k]])
            next_of[k] += 1
        return out

    def literal(self, f: pb.Fields) -> Lit:
        lex = f.string(1)
        direction = f.uint32(4)
        langtag = f.string(2) if f.has(2) else None
        if f.has(3):
            dt_id = f.uint32(3)
            if dt_id == 0:
                fail("a literal has datatype 0, which is invalid")
            if direction:
                fail("a literal sets direction without langtag")
            return Lit(lex, self.datatype(dt_id))
        if direction and langtag is None:
            fail("a literal sets direction without langtag")
        return Lit(lex, None, langtag, self.direction(direction))

    def datatype(self, id: int) -> str:
        dt = self.datatypes.get(id)
        if dt in (RDF_LANG_STRING, RDF_DIR_LANG_STRING):
            fail(f"a literal has the datatype {dt}, which needs a language tag")
        return dt

    def direction(self, value: int):
        if value not in DIRECTIONS:
            fail(f"unknown base direction {value}")
        d = DIRECTIONS[value]
        if d is not None and self.rdf_version == V_1_1:
            fail("a base direction in a stream that declares RDF 1.1")
        return d

    def poly_iri(self, i: pb.Fields, state) -> Iri:
        """RdfIri with the triple terms' shared inference state [prev_prefix, prev_name]."""
        pid = i.uint32(1) or state[0]
        nid = i.uint32(2) or state[1] + 1
        state[0], state[1] = pid, nid
        return Iri(self.resolve_iri(pid, nid))

    def triple(self, t: pb.Fields, state, depth: int) -> Triple:
        if self.rdf_version in (V_1_1, V_1_2_BASIC):
            fail("a triple term in a stream that declares RDF 1.1 or RDF 1.2 Basic")
        if depth > self.limits.max_nesting:
            fail("triple terms nested too deeply")
        if t.has(1):
            s = self.poly_iri(t.msg(1), state)
        elif t.has(2):
            s = Bnode(t.string(2))
        else:
            fail("a triple term has no subject")
        if not t.has(5):
            fail("a triple term has no predicate")
        p = self.poly_iri(t.msg(5), state)
        if t.has(9):
            o = self.poly_iri(t.msg(9), state)
        elif t.has(10):
            o = Bnode(t.string(10))
        elif t.has(11):
            o = self.literal(t.msg(11))
        elif t.has(12):
            o = self.triple(t.msg(12), state, depth + 1)
        else:
            fail("a triple term has no object")
        return Triple(s, p, o)


def layout(values, layouts, n: int):
    """Expand run values into n cells, following the sequence layout rules."""
    m = len(values)
    cells = []
    i = k = 0
    while k < len(layouts):
        tok = layouts[k]
        k += 1
        skip, kind, code = tok >> 5, (tok >> 4) & 1, tok & 15
        if code == 15:
            if k >= len(layouts):
                fail("corrupt layout: len_code 15 without an extension varint")
            length = 15 + layouts[k]
            k += 1
        else:
            length = code
        if i + skip > m:
            fail("corrupt layout: skip runs past the last run value")
        if len(cells) + skip > n:
            fail("corrupt layout: the column decodes to more than row_count cells")
        cells.extend(values[i : i + skip])
        i += skip
        if kind == 0:
            if i == m:
                fail("corrupt layout: a repeat run starts past the last run value")
            count = length + 2
            if len(cells) + count > n:
                fail("corrupt layout: the column decodes to more than row_count cells")
            cells.extend([values[i]] * count)
            i += 1
        else:
            count = length + 1
            if len(cells) + count > n:
                fail("corrupt layout: the column decodes to more than row_count cells")
            cells.extend([None] * count)
    if len(cells) + (m - i) > n:
        fail("corrupt layout: the column decodes to more than row_count cells")
    cells.extend(values[i:])
    cells.extend([None] * (n - len(cells)))
    return cells
