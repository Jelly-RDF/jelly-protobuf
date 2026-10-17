"""Definitions of the Jelly-RDF 1.2 conformance test cases.

Each case is registered with one of from_pos, from_neg, to_pos, to_neg. Cases
are numbered in the order they are registered, per direction, category, and
polarity – append new cases at the end of their group to keep the numbers of
existing cases stable.

`see` is the anchor of the rule in the Jelly-RDF specification that the case
exercises, or "<page>#<anchor>" for a rule in another specification page.
`error` (negative cases) is a fragment of the reference decoder's or encoder's
error message; the generator checks that the case fails for that reason.

The expected result of a FLAT stream is a list of statements (St). The
expected result of a stream of RDF Messages is a Messages list, with one list
of statements per message.
"""

from dataclasses import dataclass, field
from typing import Optional

import msgs
from encoder import Opts, encode
from generator_common import pb
from generator_common.pb import Msg
from model import (
    RDF,
    RDF_DIR_LANG_STRING,
    RDF_LANG_STRING,
    XSD,
    XSD_STRING,
    Bnode,
    Iri,
    Lit,
    Messages,
    St,
    Triple,
)
from msgs import (
    K_SIMPLE,
    QUADS,
    T_BNODE,
    T_IRI,
    T_LIT,
    T_TRIPLE,
    batch,
    bnode_col,
    col,
    entry,
    frame,
    iri,
    iri_col,
    k_dt,
    k_lang,
    lit,
    lit_col,
    namespace,
    options_row,
    rep,
    triple,
    unb,
)

TRIPLES_1_1 = "triples_rdf_1_1"
QUADS_1_1 = "quads_rdf_1_1"
TRIPLES_1_2_BASIC = "triples_rdf_1_2_basic"
QUADS_1_2_BASIC = "quads_rdf_1_2_basic"
TRIPLES_1_2 = "triples_rdf_1_2"
QUADS_1_2 = "quads_rdf_1_2"
MESSAGES = "messages"
CATEGORIES = [TRIPLES_1_1, QUADS_1_1, TRIPLES_1_2_BASIC, QUADS_1_2_BASIC, TRIPLES_1_2, QUADS_1_2, MESSAGES]


@dataclass
class Case:
    direction: str  # "from_jelly" or "to_jelly"
    category: str
    positive: bool
    name: str
    see: str
    comment: Optional[str] = None
    frames: list = field(default_factory=list)  # from_jelly input (Msg or raw bytes)
    raw: Optional[bytes] = None  # from_jelly input as raw bytes, overrides frames
    expected: object = None  # from_jelly positive: the statements
    error: Optional[str] = None  # negative: expected error fragment
    input: object = None  # to_jelly: the statements to serialize
    opts: Optional[Opts] = None  # to_jelly: stream options
    max_rows: int = 64  # to_jelly: batch size of the reference output
    should: bool = False  # the rule is a SHOULD in the spec, not a MUST
    delimited: bool = True  # from_jelly: the input is in the delimited variant
    physical: Optional[int] = None  # the physical type, set by the generator


CASES = []


def from_pos(category, name, see, frames, expected, comment=None, raw=None, should=False,
             delimited=True):
    CASES.append(Case("from_jelly", category, True, name, see, comment, frames, raw, expected,
                      should=should, delimited=delimited))


def from_neg(category, name, see, frames, error, comment=None, raw=None, should=False):
    CASES.append(Case("from_jelly", category, False, name, see, comment, frames, raw, error=error,
                      should=should))


def from_pos_encoded(category, name, see, data, opts, max_rows=64, comment=None):
    """A positive case whose input is produced by the reference encoder."""
    from_pos(category, name, see, encode(data, opts, max_rows), data, comment)


def to_pos(category, name, see, data, opts, max_rows=64, comment=None):
    CASES.append(Case("to_jelly", category, True, name, see, comment, input=data, opts=opts,
                      max_rows=max_rows))


def to_neg(category, name, see, data, opts, error, comment=None):
    CASES.append(Case("to_jelly", category, False, name, see, comment, error=error, input=data,
                      opts=opts))


# --- helpers ------------------------------------------------------------------

E = "http://example.org/"
FOAF = "http://xmlns.com/foaf/0.1/"
O = msgs.options
F = frame
V11 = msgs.RDF_VERSION_1_1
V12B = msgs.RDF_VERSION_1_2_BASIC
V12 = msgs.RDF_VERSION_1_2


def OQ(**kw):
    """Stream options of a QUADS stream."""
    return O(physical_type=QUADS, **kw)


def OM(**kw):
    """Stream options of a stream of RDF Messages."""
    return O(stream_type=msgs.MESSAGES, **kw)


def I(name: str) -> Iri:
    return Iri(E + name)


def L(lex, dt=None, lang=None, d=None) -> Lit:
    if dt is not None and ":" not in dt:
        dt = XSD + dt
    return Lit(lex, dt, lang, d)


def B(label: str) -> Bnode:
    return Bnode(label)


def T(s, p, o) -> Triple:
    return Triple(s, p, o)


def S(s, p, o, g=None) -> St:
    return St(s, p, o, g)


def N(*values, id=None):
    return entry(list(values), id)


def const(name_id, n, prefix_ids=None):
    """A column of IRIs with the same IRI in all n cells."""
    return iri_col([name_id], rep(0, n) if n > 1 else [], prefix_ids)


# The standard lookups: the prefix ex: at 1, the names a to e at 1 to 5 (used
# with the prefix), and the whole IRIs ex:s and ex:p at 6 and 7 (used without
# a prefix).
STD = dict(prefixes=[N(E)], names=[N("a", "b", "c", "d", "e", E + "s", E + "p")])
SID, PID = 6, 7


def std(o, n, s=None, p=None, **kw):
    """A column batch with the standard lookups. The subjects and predicates are
    ex:s and ex:p in every row, unless given."""
    b = dict(rows=n, **STD, s=const(SID, n) if s is None else s, p=const(PID, n) if p is None else p, o=o)
    b.update(kw)
    return batch(**b)


def more(o, n, s=None, p=None, **kw):
    """Like std, for a later frame: no lookup entries, the standard ones are still there."""
    return batch(rows=n, s=const(SID, n) if s is None else s, p=const(PID, n) if p is None else p,
                 o=o, **kw)


def obj(o, n, opts=None, **kw):
    """One frame: the stream options and a standard batch with the given objects column."""
    return [F(options=O(prefix=8) if opts is None else opts, columns=std(o, n, **kw))]


def objs(*terms):
    """The statements ex:s ex:p <term>, one per term."""
    return [S(I("s"), I("p"), t) for t in terms]


IRI_ABC = {c: I(c) for c in "abcde"}


def objs_of(layout, values=IRI_ABC):
    """Statements from a compact object string, e.g. "aab"."""
    return objs(*(values[ch] for ch in layout))


def grf(g, n, opts=None, **kw):
    """One QUADS frame: a standard batch with the objects "0", "1", ... (simple
    literals) and the given graphs column."""
    return [F(options=OQ(prefix=8) if opts is None else opts,
              columns=std(lit_col(lex=[str(i) for i in range(n)]), n, g=g, **kw))]


def in_graphs(layout, values=IRI_ABC):
    """The statements of grf, with graph names from a compact string: "_" is the default graph."""
    return [S(I("s"), I("p"), L(str(i)), None if ch == "_" else values[ch])
            for i, ch in enumerate(layout)]


def one(names=(), **kw):
    """A batch with one triple, ex:s ex:p "x", with the names as whole IRIs at 1 and 2,
    and the given extra name entries."""
    return batch(rows=1, names=[N(E + "s", E + "p"), *names], s=iri_col([1]), p=iri_col([2]),
                 o=lit_col(lex=["x"]), **kw)


ONE = objs(L("x"))


def row_triple():
    """An RdfStreamRow of the row layout (Jelly-RDF 1.1) with a triple."""
    return Msg().msg(2, triple(s_iri=iri(None, 1), p_iri=iri(None, 2), o_literal=lit("x")))


# =============================================================================
# From Jelly – TRIPLES, RDF 1.1
# =============================================================================

C = TRIPLES_1_1

# --- common usage patterns (produced by the reference encoder) -------------------

PEOPLE = [
    st
    for i in range(10)
    for st in (
        S(I(f"person/{i}"), Iri(RDF + "type"), Iri(FOAF + "Person")),
        S(I(f"person/{i}"), Iri(FOAF + "name"), L(f"Person {i}", lang="en")),
        S(I(f"person/{i}"), Iri(FOAF + "age"), L(str(20 + i), "integer")),
        S(I(f"person/{i}"), Iri(FOAF + "homepage"), Iri(f"https://site{i % 3}.example/home")),
    )
]
from_pos_encoded(C, "Typical graph: IRIs, language-tagged and typed literals. Prefix and datatype lookups enabled. Single frame.",
                 "column-batches", PEOPLE, Opts(prefix=16, datatype=8))
from_pos_encoded(C, "Typical graph with the prefix lookup disabled. The names hold whole IRIs.",
                 "stream-options", PEOPLE, Opts(prefix=0, datatype=8))
from_pos_encoded(C, "Typical graph split into frames of 3 statements. Lookup entries are kept between frames.",
                 "prefix-name-and-datatype-lookup-entries", PEOPLE, Opts(prefix=16, datatype=8), max_rows=3)

MANY = [
    S(I(f"s{i % 97}"), I(f"p{i % 7}"), I(f"o{i}") if i % 2 else L(str(i % 50), "integer"))
    for i in range(1000)
]
from_pos_encoded(C, "1000 statements with over 600 distinct IRIs, name lookup of size 128. The name lookup entries are overwritten many times (LRU), and frames end early when the working set would not fit.",
                 "the-working-set-of-a-batch", MANY, Opts(name=128, prefix=16, datatype=4))

UNICODE = [
    S(Iri("http://example.org/zażółć/gęślą#jaźń"), I("label"), L("Zażółć gęślą jaźń")),
    S(Iri("http://例え.jp/テスト"), I("label"), L("日本語のテキスト", lang="ja")),
    S(Iri("http://example.org/emoji/😀"), I("label"), L("emoji 😀🎉 and a combining mark: é")),
    S(I("rtl"), I("label"), L("مرحبا بالعالم", lang="ar")),
    S(I("escapes"), I("label"), L("quotes \" and ' backslash \\ tab \t newline \n return \r")),
    S(I("empty"), I("label"), L("")),
]
from_pos_encoded(C, "Non-ASCII IRIs and literals (Polish, Japanese, Arabic, emoji, combining marks), characters that need escaping in text formats, and an empty literal.",
                 "rdf-terms", UNICODE, Opts(prefix=16))

BNODES = [S(B(f"b{i // 3}"), I("knows"), B(f"c{i % 4}")) for i in range(24)]
from_pos_encoded(C, "Blank nodes whose labels repeat across statements and across frames. Equal labels are the same blank node in the whole stream.",
                 "blank-nodes", BNODES, Opts(), max_rows=5)

COUNTER = [S(I("counter"), I("value"), L(str(i), "integer")) for i in range(2000)]
from_pos_encoded(C, "2000 statements about one subject, in frames of 256 statements. Columns of literals with a single literal kind, and subjects and predicates as one repeat run.",
                 "literals-in-columns", COUNTER, Opts(datatype=4), max_rows=256)

from_pos_encoded(C, "Every statement in its own frame.",
                 "stream-frames", [S(I(f"s{i}"), I("p"), L(str(i))) for i in range(10)],
                 Opts(prefix=4), max_rows=1)

GROUPED = [S(I(f"item/{i}"), I(f"prop{j}"), L(f"{i}.{j}")) for i in range(5) for j in range(8)]
from_pos_encoded(C, "Statements grouped by subject: the subjects column is a few long repeat runs.",
                 "column-batches", GROUPED, Opts(prefix=8))

# --- the example from the specification ----------------------------------------------

from_pos(C, "The example from the specification: two frames, the second restating the stream options.",
         "example",
         [F(options=O(rdf_version=V11, prefix=16),
            columns=batch(rows=3, names=[N("", "alice", "bob", "knows", "name")], prefixes=[N(E)],
                          namespaces=[namespace("ex", iri(1))],
                          s=iri_col([2, 0], [0], [1]), p=iri_col([4, 0], [32], [1]),
                          o=col([T_IRI, T_LIT, T_LIT], name_ids=[3], prefix_ids=[1],
                                lex=["Alice", "Bob"], lit_kinds=[0, 2], langtags=["en"]))),
          F(options=O(rdf_version=V11, prefix=16),
            columns=batch(rows=1, names=[N("carol", "name")], prefixes=[N(E)],
                          s=iri_col([0], [], [1]), p=iri_col([2], [], [1]), o=lit_col(lex=["Carol"])))],
         [S(I("alice"), I("knows"), I("bob")), S(I("alice"), I("name"), L("Alice")),
          S(I("bob"), I("name"), L("Bob", lang="en")), S(I("carol"), I("name"), L("Carol"))])

# --- frames ----------------------------------------------------------------------------

from_pos(C, "An empty file: a stream with no frames. It is a valid, empty RDF graph.",
         "stream-frames", [], [])
from_pos(C, "A stream of two empty frames (no rows, no column batch). It is a valid, empty RDF graph.",
         "stream-frames", [F(), F()], [])
from_pos(C, "Empty frames before the first frame with the stream options, between frames, and at the end.",
         "stream-frames",
         [F(), obj(lit_col(lex=["x"]), 1)[0], F(), F(columns=more(lit_col(lex=["y"]), 1)), F()],
         objs(L("x"), L("y")))
from_pos(C, "A frame with only the stream options, followed by a frame with a column batch and no options.",
         "stream-options",
         [F(options=O(prefix=8)), F(columns=std(lit_col(lex=["x"]), 1))],
         ONE)
from_pos(C, "A stream with only the stream options: an empty RDF graph.",
         "stream-options", [F(options=O())], [])
from_pos(C, "A column batch with row_count 0 and only lookup entries, used by the next frame.",
         "column-batches",
         [F(options=O(prefix=8), columns=batch(**STD)),
          F(columns=more(lit_col(lex=["x"]), 1))],
         ONE)
from_pos(C, "Metadata with an implementation-defined key whose value is not valid UTF-8. Consumers must not assume that the value is valid UTF-8, and should ignore the key.",
         "stream-frame-metadata",
         [F(options=O(), columns=one(), metadata={"com.example.binary": b"\xff\xfe\x00\x80"})],
         ONE)
from_pos(C, "Metadata in an empty frame.",
         "stream-frame-metadata",
         [F(options=O(), columns=one()), F(metadata={"com.example.time": b"2026-01-01"})],
         ONE)
from_pos(C, "Stream options with a stream name.",
         "stream-options", [F(options=O(stream_name="graphs/1"), columns=one())], ONE)
from_pos(C, "Stream options that declare RDF 1.1.",
         "rdf-version", [F(options=O(rdf_version=V11), columns=one())], ONE)
from_pos(C, "A single non-delimited frame. Producers must write files in the delimited variant, but consumers should be able to read this.",
         "delimited-variant-of-jelly", [F(options=O(), columns=one())], ONE, should=True,
         delimited=False)

# --- restating the stream options (concatenation) ----------------------------------

from_pos(C, "Two streams concatenated. The second segment restates the stream options (with other table sizes), and its lookup identifiers restart from 1.",
         "restating-the-stream-options",
         [F(options=O(prefix=8), columns=batch(rows=1, prefixes=[N(E)], names=[N("a", "b", "c")],
                                               s=iri_col([0], [], [1]), p=iri_col([2], [], [1]),
                                               o=bnode_col(["x"]))),
          F(columns=batch(rows=1, s=iri_col([1], [], [1]), p=iri_col([2], [], [1]), o=iri_col([3], [], [1]))),
          F(options=O(name=256, prefix=4),
            columns=batch(rows=1, prefixes=[N("https://b.org/")], names=[N("s2", "p2")],
                          s=iri_col([0], [], [1]), p=iri_col([2], [], [1]), o=bnode_col(["x"])))],
         [S(I("a"), I("b"), B("x")), S(I("a"), I("b"), I("c")),
          S(Iri("https://b.org/s2"), Iri("https://b.org/p2"), B("x"))],
         comment="Blank node labels are not reset by the restated options: the label x in both segments is one blank node.")
from_pos(C, "Concatenated streams with other lookup settings: the first segment has no prefix lookup, the second has prefix and datatype lookups, and the third declares RDF 1.1.",
         "restating-the-stream-options",
         [F(options=O(), columns=one()),
          F(options=O(name=200, prefix=4, datatype=4),
            columns=batch(rows=1, prefixes=[N(E)], names=[N("s", "p")], datatypes=[N(XSD + "integer")],
                          s=iri_col([0], [], [1]), p=iri_col([2], [], [1]), o=lit_col(lex=["1"], kinds=[k_dt(1)]))),
          F(options=O(rdf_version=V11), columns=one())],
         [S(I("s"), I("p"), L("x")), S(I("s"), I("p"), L("1", "integer")), S(I("s"), I("p"), L("x"))])
from_pos(C, "The stream options restated in a frame without a column batch, and then in a frame with one.",
         "restating-the-stream-options",
         [F(options=O(), columns=one()), F(options=O()), F(options=O(), columns=one())],
         ONE + ONE)

# --- namespace declarations ------------------------------------------------------------

NS_NAMES = dict(prefixes=[N(E)], names=[N("a", "b", "c", "d", "e", E + "s", E + "p", "", "ns/")])
from_pos(C, "Namespace declarations do not change the statements: two declarations, the second with its IRI inferred from the first (prefix_id 0 and name_id 0), an empty namespace name, and a name declared again.",
         "namespace-declarations",
         [F(options=O(prefix=8),
            columns=batch(rows=1, **NS_NAMES,
                          namespaces=[namespace("ex", iri(1, 8)), namespace("", iri()),
                                      namespace("ex", iri(None, 1))],
                          s=const(SID, 1), p=const(PID, 1), o=lit_col(lex=["x"])))],
         ONE,
         comment="The IRIs of the namespace declarations are one IRI sequence: ex: is http://example.org/, the empty name is http://example.org/ns/ (prefix 1, name 9), and ex: is then http://example.org/a.")
from_pos(C, "A column batch with only namespace declarations (row_count 0), between two batches with statements.",
         "namespace-declarations",
         [F(options=O(prefix=8), columns=std(lit_col(lex=["x"]), 1, names=NS_NAMES["names"])),
          F(columns=batch(namespaces=[namespace("ex", iri(1, 8))])),
          F(columns=more(lit_col(lex=["y"]), 1))],
         objs(L("x"), L("y")))
from_pos(C, "Namespace declarations without the prefix lookup: the IRI of the namespace is a whole name.",
         "namespace-declarations",
         [F(options=O(), columns=batch(rows=1, names=[N(E, E + "s", E + "p")],
                                        namespaces=[namespace("ex", iri())],
                                        s=iri_col([2]), p=iri_col([3]), o=lit_col(lex=["x"])))],
         ONE)

# --- lookup entries --------------------------------------------------------------------

from_pos(C, "Lookup identifiers continue across frames: an entry with id 0 in the second frame takes the next identifier.",
         "packed-lookup-entries",
         [F(options=O(prefix=8), columns=batch(rows=1, prefixes=[N(E)], names=[N("s", "p", "a")],
                                               s=iri_col([1], [], [1]), p=iri_col([2], [], [1]),
                                               o=iri_col([3], [], [1]))),
          F(columns=batch(rows=1, names=[N("b")], s=iri_col([1], [], [1]), p=iri_col([2], [], [1]),
                          o=iri_col([4], [], [1])))],
         objs(I("a"), I("b")))
from_pos(C, "Packed entries with explicit identifiers: id 10 with two values, then id 0 continuing at 12.",
         "packed-lookup-entries",
         [F(options=O(), columns=batch(rows=3, names=[N(E + "s", E + "p", id=10), N(E + "x")],
                                        s=const(10, 3), p=const(11, 3), o=iri_col([12, 10, 11])))],
         objs(I("x"), I("s"), I("p")))
from_pos(C, "An entry overwritten in a later frame: the later frame sees the new value.",
         "prefix-name-and-datatype-lookup-entries",
         [obj(iri_col([1], [], [1]), 1)[0],
          F(columns=more(iri_col([1], [], [1]), 1, names=[N("b", id=1)]))],
         objs_of("ab"))
from_pos(C, "All lookup entries of a batch are applied before its columns: a name overwritten twice in one batch decodes to the last value.",
         "the-working-set-of-a-batch",
         obj(iri_col([1], [], [1]), 1, names=[N("a", "b", "c", "d", "e", E + "s", E + "p"), N("x", id=1), N("b", id=1)]),
         objs_of("b"),
         comment="A producer must not write such a batch if the column is meant to refer to the first value (see the working set rule). A consumer must still decode it this way.")
from_pos(C, "A name lookup entry at the largest identifier the table allows.",
         "stream-options",
         [F(options=O(name=128), columns=batch(rows=1, names=[N(E + "s", E + "p"), N(E + "last", id=128)],
                                                s=iri_col([1]), p=iri_col([2]), o=iri_col([128])))],
         objs(I("last")))
from_pos(C, "Lookup table sizes at the recommended default consumer limits: 16384 names, 4096 prefixes, 256 datatypes.",
         "stream-options",
         [F(options=O(name=16384, prefix=4096, datatype=256),
            columns=batch(rows=1, prefixes=[N(E, id=4096)], names=[N("s", "p"), N("a", id=16384)],
                          datatypes=[N(XSD + "int", id=256)],
                          s=iri_col([1], [], [4096]), p=iri_col([2], [], [4096]), o=iri_col([16384], [], [4096]))),
          F(columns=batch(rows=1, s=iri_col([1], [], [4096]), p=iri_col([2], [], [4096]),
                          o=lit_col(lex=["7"], kinds=[k_dt(256)])))],
         objs(I("a"), L("7", "int")),
         comment="Consumers may set lower limits than the recommended defaults, and then reject this stream.",
         should=True)

# --- IRIs ------------------------------------------------------------------------------

from_pos(C, "IRI example from the specification: name_ids [0, 0, 1, 3], prefix_ids [1, 0, 0, 2].",
         "iris-in-columns",
         obj(iri_col([0, 0, 1, 3], [], [1, 0, 0, 2]), 4,
             prefixes=[N("https://a.org/", "https://b.org/")], names=[N("x1", "x2", "z", E + "s", E + "p")],
             s=const(4, 4), p=const(5, 4)),
         objs(Iri("https://a.org/x1"), Iri("https://a.org/x2"), Iri("https://a.org/x1"), Iri("https://b.org/z")))
from_pos(C, "prefix_ids with a single entry: every value uses that prefix.",
         "iris-in-columns",
         obj(iri_col([0, 0, 0], [], [2]), 3,
             prefixes=[N("https://a.org/", "https://b.org/")], names=[N("x", "y", "z", E + "s", E + "p")],
             s=const(4, 3), p=const(5, 3)),
         objs(Iri("https://b.org/x"), Iri("https://b.org/y"), Iri("https://b.org/z")))
from_pos(C, "Empty prefix_ids with the prefix lookup enabled: no value has a prefix, the names hold whole IRIs.",
         "iris-in-columns",
         obj(iri_col([0, 0]), 2, prefixes=None, names=[N(E + "a", E + "b", E + "s", E + "p")],
             s=const(3, 2), p=const(4, 2)),
         objs_of("ab"))
from_pos(C, "prefix_ids with one entry per value, starting with 0: the prefix inference state starts from \"no prefix\".",
         "iris-in-columns",
         obj(iri_col([6, 1, 0], [], [0, 1, 0]), 3),
         objs(I("s"), I("a"), I("b")))
from_pos(C, "name_ids mixing explicit identifiers and 0 (previous + 1): [5, 0, 0, 2, 0] is 5, 6, 7, 2, 3.",
         "iris-in-columns",
         [F(options=O(), columns=batch(rows=5, names=[N(*[E + f"n{i}" for i in range(1, 8)], E + "s", E + "p")],
                                        s=const(8, 5), p=const(9, 5), o=iri_col([5, 0, 0, 2, 0])))],
         objs(*(I(f"n{i}") for i in (5, 6, 7, 2, 3))))
from_pos(C, "The name_id and prefix_id inference state resets at the start of every column.",
         "iris-in-columns",
         [F(options=O(prefix=8),
            columns=batch(rows=2, prefixes=[N(E, "https://b.org/")], names=[N("urn:x:full", "a", "b", E + "p")],
                          s=iri_col([2, 0], [], [2, 0]), p=const(4, 2), o=iri_col([0, 0], [], [0, 1])))],
         [S(Iri("https://b.org/a"), I("p"), Iri("urn:x:full")), S(Iri("https://b.org/b"), I("p"), I("a"))],
         comment="The subjects column ends at name 3 with prefix 2. The objects column still starts from name 0 and no prefix: its first name_id of 0 means name 1, and its first prefix_id of 0 means no prefix, not the prefix of the previous column.")
from_pos(C, "The name_id inference state resets at the start of every batch.",
         "iris-in-columns",
         [obj(iri_col([0, 0, 0], [], [1]), 3)[0], F(columns=more(iri_col([0], [], [1]), 1))],
         objs_of("abca"))
from_pos(C, "An empty name: the IRI is equal to its prefix.",
         "iris-in-columns",
         obj(iri_col([0, 0], [], [1]), 2, names=[N("", "a", E + "s", E + "p")], s=const(3, 2), p=const(4, 2)),
         objs(Iri(E), I("a")))
from_pos(C, "Subjects, predicates, and objects with different prefixes, all IRIs inferred from 0.",
         "iris-in-columns",
         [F(options=O(prefix=8),
            columns=batch(rows=2, prefixes=[N("https://s.org/", "https://p.org/", "https://o.org/")],
                          names=[N("x", "y")],
                          s=iri_col([0, 0], [], [1]), p=iri_col([0, 0], [], [2]), o=iri_col([0, 0], [], [3])))],
         [S(Iri("https://s.org/x"), Iri("https://p.org/x"), Iri("https://o.org/x")),
          S(Iri("https://s.org/y"), Iri("https://p.org/y"), Iri("https://o.org/y"))])

# --- literals ------------------------------------------------------------------------------

from_pos(C, "A column of simple literals: literal_kinds is empty.",
         "literals-in-columns", obj(lit_col(lex=["x", "y"]), 2), objs(L("x"), L("y")))
from_pos(C, "xsd:string literals encoded three ways: no literal kinds, a single literal kind referring to an xsd:string datatype entry, and one literal kind per value mixing 0 and that entry. All are the same simple literal.",
         "literals-in-columns",
         [obj(lit_col(lex=["a"]), 1, opts=O(prefix=8, datatype=4), datatypes=[N(XSD_STRING)])[0],
          F(columns=more(lit_col(lex=["b"], kinds=[k_dt(1)]), 1)),
          F(columns=more(lit_col(lex=["c", "d"], kinds=[K_SIMPLE, k_dt(1)]), 2))],
         objs(L("a"), L("b"), L("c"), L("d")))
from_pos(C, "A column of literals with a single literal kind for the whole column: xsd:integer, then xsd:dateTime.",
         "literals-in-columns",
         [obj(lit_col(lex=["1", "-20"], kinds=[k_dt(1)]), 2, opts=O(prefix=8, datatype=4),
              datatypes=[N(XSD + "integer", XSD + "dateTime")])[0],
          F(columns=more(lit_col(lex=["2024-01-01T00:00:00Z"], kinds=[k_dt(2)]), 1))],
         objs(L("1", "integer"), L("-20", "integer"), L("2024-01-01T00:00:00Z", "dateTime")))
from_pos(C, "A column of literals with one language tag for the whole column: a single literal kind of 2.",
         "literals-in-columns",
         obj(lit_col(lex=["cat", "dog", "cat"], kinds=[k_lang(0)], langtags=["en"]), 3),
         objs(L("cat", lang="en"), L("dog", lang="en"), L("cat", lang="en")))
from_pos(C, "A column of literals with one literal kind per value, mixing simple, typed, and language-tagged literals with different tags.",
         "literals-in-columns",
         obj(lit_col(lex=["a", "1", "b", "c"], kinds=[K_SIMPLE, k_dt(1), k_lang(0), k_lang(1)], langtags=["en", "de"]), 4,
             opts=O(prefix=8, datatype=4), datatypes=[N(XSD + "integer")]),
         objs(L("a"), L("1", "integer"), L("b", lang="en"), L("c", lang="de")))
from_pos(C, "Literal kind values: 0 is a simple literal, odd values 1, 3, 5 are datatypes 1, 2, 3, and even values 2, 4, 6 are language tags 0, 1, 2.",
         "literals-in-columns",
         obj(lit_col(lex=["s", "1", "2.5", "true", "en", "de", "pl"], kinds=[0, 1, 3, 5, 2, 4, 6],
                     langtags=["en", "de", "pl"]), 7,
             opts=O(prefix=8, datatype=4), datatypes=[N(XSD + "integer", XSD + "decimal", XSD + "boolean")]),
         objs(L("s"), L("1", "integer"), L("2.5", "decimal"), L("true", "boolean"), L("en", lang="en"),
              L("de", lang="de"), L("pl", lang="pl")))
from_pos(C, "Empty lexical forms, with a single literal kind and with one literal kind per value.",
         "literals-in-columns",
         [obj(lit_col(lex=[""], layouts=rep(0, 2), kinds=[k_lang(0)], langtags=["en"]), 2)[0],
          F(columns=more(lit_col(lex=["", ""], kinds=[K_SIMPLE, k_lang(0)], langtags=["fr"]), 2))],
         objs(L("", lang="en"), L("", lang="en"), L(""), L("", lang="fr")))
from_pos(C, "langtag_directions with only 0 entries (no base direction) in a stream that declares RDF 1.1.",
         "literals-in-columns",
         obj(lit_col(lex=["a", "b"], kinds=[k_lang(0), k_lang(1)], langtags=["en", "de"],
                     dirs=[msgs.DIR_UNSPECIFIED, msgs.DIR_UNSPECIFIED]), 2, opts=O(prefix=8, rdf_version=V11)),
         objs(L("a", lang="en"), L("b", lang="de")),
         comment="Producers should leave langtag_directions empty instead, but a list of zeros is valid.")

# --- columns with several term types ---------------------------------------------------

from_pos(C, "An objects column with values of several term types: kinds says which list holds each run value. Six values need two bytes of kinds.",
         "term-types",
         obj(col([T_IRI, T_BNODE, T_LIT, T_IRI, T_IRI, T_IRI], name_ids=[0, 0, 4, 0], prefix_ids=[1],
                 lex=["l"], bnodes=["x"]), 6),
         objs(I("a"), B("x"), L("l"), I("b"), I("d"), I("e")),
         comment="kinds = [0x18, 0x00]: IRI, blank node, literal, IRI in the first byte, then IRI, IRI. The IRIs are decoded from name_ids [0, 0, 4, 0]: names 1, 2, 4, 5.")
from_pos(C, "An objects column with exactly four values of several term types: kinds is one full byte.",
         "term-types",
         obj(col([T_LIT, T_BNODE, T_IRI, T_LIT], name_ids=[1], prefix_ids=[1], lex=["x", "y"], bnodes=["n"]), 4),
         objs(L("x"), B("n"), I("a"), L("y")))
from_pos(C, "The IRI inference state of a column with several term types resets at the start of every batch.",
         "term-types",
         [obj(col([T_IRI, T_LIT], name_ids=[0], prefix_ids=[1], lex=["x"]), 2)[0],
          F(columns=more(col(name_ids=[0, 0], prefix_ids=[1]), 2))],
         objs(I("a"), L("x"), I("a"), I("b")))
from_pos(C, "A column with literals and an IRI: the literal kinds and language tags apply to the literals.",
         "term-types",
         obj(col([T_LIT, T_IRI, T_LIT], name_ids=[1], prefix_ids=[1], lex=["x", "1"],
                 lit_kinds=[k_lang(0), k_dt(1)], langtags=["en"]), 3,
             opts=O(prefix=8, datatype=4), datatypes=[N(XSD + "integer")]),
         objs(L("x", lang="en"), I("a"), L("1", "integer")))
from_pos(C, "prefix_ids with one entry per IRI in a column with several term types: it has one entry per IRI, not per run value, and its inference runs along the IRIs only.",
         "iris-in-columns",
         obj(col([T_IRI, T_LIT, T_IRI, T_IRI], name_ids=[1, 2, 1], prefix_ids=[1, 2, 0], lex=["l"]), 4,
             prefixes=[N(E, "https://b.org/")], names=[N("a", "x", E + "s", E + "p")], s=const(3, 4), p=const(4, 4)),
         objs(I("a"), L("l"), Iri("https://b.org/x"), Iri("https://b.org/a")))
from_pos(C, "literal_kinds with one entry per literal in a column with several term types: it has one entry per literal, not per run value.",
         "literals-in-columns",
         obj(col([T_LIT, T_IRI, T_LIT], name_ids=[1], prefix_ids=[1], lex=["a", "b"],
                 lit_kinds=[k_lang(0), K_SIMPLE], langtags=["en"]), 3),
         objs(L("a", lang="en"), I("a"), L("b")))
from_pos(C, "Columns whose values are all of one term type need no kinds: an objects column of blank nodes, and one of literals.",
         "term-types",
         [obj(bnode_col(["n", "m"]), 2)[0], F(columns=more(lit_col(lex=["a", "b"]), 2))],
         objs(B("n"), B("m"), L("a"), L("b")))
from_pos(C, "kinds set for a column whose values are all of one term type (allowed, producers should leave it empty).",
         "term-types", obj(col([T_LIT, T_LIT], lex=["1", "2"]), 2), objs(L("1"), L("2")))
from_pos(C, "A subjects column mixing IRIs and blank nodes.",
         "column-batches",
         obj(lit_col(lex=["1", "2", "3"]), 3, s=col([T_IRI, T_BNODE, T_IRI], name_ids=[1, 2], prefix_ids=[1], bnodes=["n"])),
         [S(I("a"), I("p"), L("1")), S(B("n"), I("p"), L("2")), S(I("b"), I("p"), L("3"))])
from_pos(C, "A column of IRIs only, with no kinds, and a repeat run.",
         "term-types", obj(col(layouts=rep(1, 2), name_ids=[0, 0], prefix_ids=[1]), 3), objs_of("abb"),
         comment="kinds may be empty when all run values are of one term type.")

# --- sequence layout -----------------------------------------------------------------

from_pos(C, "Every cell bound, no value repeated in consecutive rows: layouts is empty.",
         "sequence-layout", obj(iri_col([0, 0, 0, 0], [], [1]), 4), objs_of("abcd"))
from_pos(C, "Two repeat runs in a row (skip = 0 between them), then the implicit tail.",
         "sequence-layout", obj(iri_col([0, 0, 0], rep(0, 2) + rep(0, 3), [1]), 6), objs_of("aabbbc"))
from_pos(C, "Second example of the sequence layout from the specification: A, then B repeated 40 times, then C. layouts = [47, 23].",
         "sequence-layout", obj(iri_col([0, 0, 0], [47, 23], [1]), 42), objs_of("a" + "b" * 40 + "c"))
from_pos(C, "The largest repeat run that fits in one token: 16 cells (len_code 14).",
         "sequence-layout", obj(iri_col([0, 0], rep(0, 16), [1]), 17), objs_of("a" * 16 + "b"))
from_pos(C, "The smallest repeat run that needs an extension varint: 17 cells (len_code 15, extension 0).",
         "sequence-layout", obj(iri_col([0, 0], rep(0, 17), [1]), 18), objs_of("a" * 17 + "b"))
from_pos(C, "A long repeat run with a multi-byte extension varint: 1000 cells.",
         "sequence-layout", obj(iri_col([0, 0], rep(0, 1000), [1]), 1001), objs_of("a" * 1000 + "b"))
from_pos(C, "Tokens that take more than one byte: skip = 4 and skip = 300.",
         "sequence-layout",
         obj(lit_col(lex=[str(i) for i in range(306)], layouts=rep(4, 2) + rep(300, 3)), 309),
         objs(*[L(str(i)) for i in range(4)], L("4"), L("4"), *[L(str(i)) for i in range(5, 305)],
              L("305"), L("305"), L("305")))
from_pos(C, "The subjects and predicates columns as one repeat run each, and an objects column without layouts.",
         "sequence-layout", obj(lit_col(lex=["1", "2", "3"]), 3), objs(L("1"), L("2"), L("3")))
from_pos(C, "Equal values in consecutive rows stored as separate run values, without a repeat run. All statements must be kept. Consumers must not remove duplicates.",
         "sequence-layout", obj(iri_col([1, 1, 1, 2], [], [1]), 4), objs_of("aaab"),
         comment="Producers should merge equal adjacent run values into one run, so they usually do not write this. The consumer must still decode it.")
from_pos(C, "Two repeat runs of the same value next to each other, not merged into one.",
         "sequence-layout", obj(iri_col([1, 1], rep(0, 2) + rep(0, 3), [1]), 5), objs_of("aaaaa"),
         comment="Producers should merge adjacent runs, so they usually do not write this. The consumer must still decode it.")
from_pos(C, "Duplicate statements within a frame and across frames are all kept, in order.",
         "ordering",
         [obj(iri_col([2], rep(0, 3), [1]), 3)[0], F(columns=more(iri_col([2], rep(0, 2), [1]), 2))],
         objs_of("bbbbb"))

# --- blank nodes -------------------------------------------------------------------------

from_pos(C, "Blank node labels are scoped to the whole stream: the same label in different frames and in different columns is the same blank node.",
         "blank-nodes",
         [obj(bnode_col(["n2", "n1"]), 2, s=bnode_col(["n1", "n2"]))[0],
          F(columns=more(bnode_col(["n1"]), 1, s=bnode_col(["n2"])))],
         [S(B("n1"), I("p"), B("n2")), S(B("n2"), I("p"), B("n1")), S(B("n2"), I("p"), B("n1"))])

# --- negative ---------------------------------------------------------------------------


def ONE_F(opts, **kw):
    """One frame with the given stream options and the batch of one()."""
    return [F(options=opts, columns=one(**kw))]



from_neg(C, "The last frame is truncated: the length prefix is larger than the rest of the file.",
         "delimited-variant-of-jelly", [], "truncated",
         raw=pb.varint(127) + F(options=O(), columns=one()).encode(),
         comment="The length prefix 127 (0x7F) cannot be read as the start of a non-delimited frame: it would be field 15 with the invalid wire type 7.")

# stream options
from_neg(C, "Version tag 0.", "version-tag", ONE_F(O(version=0)), "version tag is 0", should=True)
from_neg(C, "Version tag 4, newer than version 3 of the format.", "version-tag",
         ONE_F(O(version=4)), "newer than supported", should=True)
from_neg(C, "generalized_statements set in the stream options. The field is used only in Jelly-RDF 1.0.x and 1.1.x.",
         "stream-options", ONE_F(O(generalized=True)), "generalized_statements is set", should=True)
from_neg(C, "rdf_star set in the stream options. The field is used only in Jelly-RDF 1.0.x and 1.1.x.",
         "stream-options", ONE_F(O(rdf_star=True)), "rdf_star is set", should=True)
from_neg(C, "logical_type set in the stream options. The field is used only in Jelly-RDF 1.0.x and 1.1.x.",
         "stream-options", ONE_F(O(logical_type=msgs.LOGICAL_FLAT_TRIPLES)), "logical_type is set", should=True)
from_neg(C, "physical_type not set (PHYSICAL_STREAM_TYPE_UNSPECIFIED).", "physical-stream-types",
         ONE_F(O(physical_type=None)), "physical_type is unspecified", should=True)
from_neg(C, "physical_type GRAPHS, which is used only in Jelly-RDF 1.0.x and 1.1.x.", "physical-stream-types",
         ONE_F(O(physical_type=msgs.GRAPHS)), "physical_type GRAPHS", should=True)
from_neg(C, "Unknown physical_type value 4.", "physical-stream-types",
         ONE_F(O(physical_type=4)), "unknown physical_type", should=True)
from_neg(C, "Unknown stream_type value 2.", "stream-types",
         ONE_F(O(stream_type=2)), "unknown stream_type", should=True)
from_neg(C, "Unknown rdf_version value 4.", "rdf-version",
         ONE_F(O(rdf_version=4)), "unknown rdf_version", should=True)
from_neg(C, "max_name_table_size 127, below the minimum of 128.", "stream-options",
         ONE_F(O(name=127)), "below the minimum", should=True)
from_neg(C, "max_name_table_size not set (0), in a frame with only the stream options.", "stream-options",
         [F(options=O(name=None))], "below the minimum", should=True)
from_neg(C, "max_name_table_size 10000000. Consumers should reject lookup sizes larger than their limit (recommended default 16384).",
         "stream-options", ONE_F(O(name=10_000_000)), "larger than the consumer accepts", should=True)
from_neg(C, "max_prefix_table_size 10000000. Consumers should reject lookup sizes larger than their limit (recommended default 4096).",
         "stream-options", ONE_F(O(prefix=10_000_000)), "larger than the consumer accepts", should=True)
from_neg(C, "max_datatype_table_size 10000000. Consumers should reject lookup sizes larger than their limit (recommended default 256).",
         "stream-options", ONE_F(O(datatype=10_000_000)), "larger than the consumer accepts", should=True)

# rows of a frame
from_neg(C, "A frame with two rows: the stream options twice.", "stream-frames",
         [F(options=O(), rows=[options_row(O())], columns=one())], "the frame has 2 rows", should=True)
from_neg(C, "A frame with two rows: the stream options, and a name entry row of the row layout (Jelly-RDF 1.1).",
         "stream-frames",
         [F(options=O(), rows=[Msg().msg(9, Msg().string(2, E + "x"))], columns=one())],
         "the frame has 2 rows", should=True)
from_neg(C, "A row with a triple (row layout, Jelly-RDF 1.1) in a stream with version tag 3.",
         "stream-frames",
         [F(options=O(), columns=one()), F(rows=[row_triple()])],
         "a row with a field other than options: triple", should=True)
from_neg(C, "A row with a namespace declaration (row layout, Jelly-RDF 1.1) in a stream with version tag 3.",
         "stream-frames",
         [F(options=O(), columns=one()), F(rows=[Msg().msg(6, namespace("ex", iri(None, 1)))])],
         "a row with a field other than options: namespace", should=True)

# lookups
from_neg(C, "A prefix lookup entry when the prefix lookup is disabled (max_prefix_table_size 0).",
         "stream-options", ONE_F(O(), prefixes=[N(E)]), "prefix lookup is disabled", should=True)
from_neg(C, "A datatype lookup entry when the datatype lookup is disabled (max_datatype_table_size 0).",
         "stream-options", ONE_F(O(), datatypes=[N(XSD + "int")]), "datatype lookup is disabled", should=True)
from_neg(C, "A name lookup entry with an identifier larger than the table size.",
         "prefix-name-and-datatype-lookup-entries", ONE_F(O(), names=[N("a", id=129)]),
         "outside of the table", should=True)
from_neg(C, "A packed name entry whose last value falls outside the table (ids 127, 128, 129 in a table of 128).",
         "prefix-name-and-datatype-lookup-entries", ONE_F(O(), names=[N("a", "b", "c", id=127)]),
         "outside of the table", should=True)
from_neg(C, "A prefix lookup entry with an identifier larger than the table size.",
         "prefix-name-and-datatype-lookup-entries", ONE_F(O(prefix=8), prefixes=[N(E, id=9)]),
         "outside of the table", should=True)
from_neg(C, "A column refers to a prefix identifier outside the prefix table.",
         "iris-in-columns", obj(iri_col([1], [], [9]), 1), "prefix id 9 outside", should=True)
from_neg(C, "A column refers to a name that was never defined (name_id 0 at the start of a column means 1, and the name table is empty).",
         "prefix-name-and-datatype-lookup-entries",
         [F(options=O(), columns=batch(rows=1, s=iri_col([0]), p=iri_col([0]), o=iri_col([0])))],
         "empty lookup entry", should=True)
from_neg(C, "A column refers to a name identifier outside the name table.",
         "iris-in-columns", obj(iri_col([200], [], [1]), 1), "name id 200 outside", should=True)
from_neg(C, "A column uses prefix_ids while the prefix lookup is disabled.",
         "stream-options", obj(iri_col([1], [], [1]), 1, opts=O(), prefixes=None), "prefix id 1 outside", should=True)
from_neg(C, "A namespace declaration refers to a name that was never defined.",
         "prefix-name-and-datatype-lookup-entries",
         ONE_F(O(), namespaces=[namespace("ex", iri(None, 50))]), "empty lookup entry", should=True)
from_neg(C, "prefix_ids with 2 entries for 3 values. The length must be 0, 1, or the number of values.",
         "iris-in-columns", obj(iri_col([0, 0, 0], [], [1, 1]), 3), "prefix_ids has 2 entries")

# literals
from_neg(C, "A literal kind refers to a datatype identifier outside the datatype table.",
         "literals-in-columns", obj(lit_col(lex=["1"], kinds=[k_dt(9)]), 1, opts=O(prefix=8, datatype=8)),
         "datatype id 9 outside", should=True)
from_neg(C, "A literal kind refers to a datatype while the datatype lookup is disabled.",
         "stream-options", obj(lit_col(lex=["1"], kinds=[k_dt(1)]), 1), "datatype id 1 outside", should=True)
from_neg(C, "A literal kind refers to a datatype entry holding rdf:langString.",
         "literals-in-columns",
         obj(lit_col(lex=["x"], kinds=[k_dt(1)]), 1, opts=O(prefix=8, datatype=8), datatypes=[N(RDF_LANG_STRING)]),
         "needs a language tag", should=True)
from_neg(C, "literal_kinds with 2 entries for 3 values. The length must be 0, 1, or the number of values.",
         "literals-in-columns",
         obj(lit_col(lex=["a", "b", "c"], kinds=[k_lang(0), k_lang(0)], langtags=["en"]), 3),
         "literal_kinds has 2 entries")
from_neg(C, "A literal kind refers to a language tag index past the end of langtags.",
         "literals-in-columns", obj(lit_col(lex=["a"], kinds=[k_lang(1)], langtags=["en"]), 1),
         "refers to language tag 1")
from_neg(C, "A literal kind refers to a language tag, but the column has no language tags.",
         "literals-in-columns", obj(lit_col(lex=["a"], kinds=[k_lang(0)]), 1), "refers to language tag 0")
from_neg(C, "A literal kind in a column with several term types refers to a language tag that is not there.",
         "term-types", obj(col([T_LIT, T_BNODE], lex=["a"], lit_kinds=[k_lang(0)], bnodes=["n"]), 2),
         "refers to language tag 0")

# term types
from_neg(C, "kinds is too short: one byte for five values.",
         "term-types", obj(col(msgs.pack_kinds([T_LIT] * 4), lex=["a", "b", "c", "d", "e"]), 5),
         "kinds has 1 bytes for 5 values")
from_neg(C, "kinds is too long: two bytes for two values.",
         "term-types", obj(col(msgs.pack_kinds([T_LIT, T_LIT]) + b"\x00", lex=["a", "b"]), 2),
         "kinds has 2 bytes for 2 values")
from_neg(C, "kinds is empty, but the column has values of two term types: a literal and a blank node.",
         "term-types", obj(col(lex=["a"], bnodes=["n"]), 2), "kinds has 0 bytes for 2 values")
from_neg(C, "The unused bits of the last byte of kinds are not 0.",
         "term-types", obj(col(bytes([0b00010101]), lex=["a", "b"]), 2), "unused bits",
         comment="kinds = 0x15: literal, literal, and then a third literal in the bits of a value that does not exist.")
from_neg(C, "kinds refers to more IRIs than the column has: two IRIs, but name_ids has one.",
         "term-types", obj(col([T_IRI, T_IRI], name_ids=[1], prefix_ids=[1], lex=["x"]), 2),
         "kinds refers to more IRIs",
         comment="The number of kinds matches the total number of values (2), but not the number of values of each type.")
from_neg(C, "kinds refers to more literals than the column has: two literals, but lex_values has one.",
         "term-types", obj(col([T_LIT, T_LIT], lex=["a"], bnodes=["n"]), 2), "kinds refers to more literals",
         comment="The number of kinds matches the total number of values (2), but not the number of values of each type.")
from_neg(C, "kinds refers to more blank nodes than the column has: two blank nodes, but bnodes has one.",
         "term-types", obj(col([T_BNODE, T_BNODE], lex=["a"], bnodes=["n"]), 2), "kinds refers to more blank nodes")
from_neg(C, "prefix_ids with one entry per run value, in a column with two IRIs and a literal. The list must have 0, 1, or one entry per IRI.",
         "iris-in-columns", obj(col([T_IRI, T_LIT, T_IRI], name_ids=[1, 2], prefix_ids=[1, 1, 1], lex=["l"]), 3),
         "prefix_ids has 3 entries")
from_neg(C, "literal_kinds with one entry per run value, in a column with two literals and an IRI. The list must have 0, 1, or one entry per literal.",
         "literals-in-columns",
         obj(col([T_LIT, T_IRI, T_LIT], name_ids=[1], prefix_ids=[1], lex=["a", "b"],
                 lit_kinds=[K_SIMPLE, K_SIMPLE, K_SIMPLE]), 3),
         "literal_kinds has 3 entries")

# column batches
BIG = 1 << 27
from_neg(C, "row_count of 2^27, larger than the maximum of 2^27 - 1.",
         "column-batches",
         [F(options=O(), columns=batch(rows=BIG, names=[N(E + "s", E + "p")], s=iri_col([1], rep(0, BIG)),
                                        p=iri_col([2], rep(0, BIG)), o=lit_col(lex=["x"], layouts=rep(0, BIG))))],
         "larger than 2^27 - 1",
         comment="Each column is one repeat run of 2^27 cells, so the columns match row_count, and the row count is the only problem.")
from_neg(C, "The subjects column is shorter than row_count: its last cell is unbound.",
         "column-batches", obj(lit_col(lex=["x", "y"]), 2, s=const(SID, 1)),
         "an unbound cell in the subjects column")
from_neg(C, "The predicates column is not set (all its cells are unbound).",
         "column-batches", [F(options=O(), columns=batch(rows=1, names=[N(E + "s")], s=iri_col([1]), o=lit_col(lex=["x"])))],
         "an unbound cell in the predicates column")
from_neg(C, "The objects column has an unbound run.",
         "column-batches", obj(lit_col(lex=["x"], layouts=unb(1, 1)), 2), "an unbound cell in the objects column")
from_neg(C, "The objects column is an empty message, with row_count 1.",
         "column-batches", obj(col(), 1), "an unbound cell in the objects column")
from_neg(C, "A literal in the subjects column.",
         "column-batches", obj(lit_col(lex=["x"]), 1, s=lit_col(lex=["s"])), "a literal in the subjects column",
         should=True)
from_neg(C, "A blank node in the predicates column.",
         "column-batches", obj(lit_col(lex=["x"]), 1, p=bnode_col(["p"])), "a blank node in the predicates column",
         should=True)
from_neg(C, "A literal in the predicates column.",
         "column-batches", obj(lit_col(lex=["x"]), 1, p=lit_col(lex=["p"])), "a literal in the predicates column",
         should=True)
from_neg(C, "A graphs column in a stream of physical type TRIPLES.",
         "physical-stream-types", obj(lit_col(lex=["x"]), 1, g=const(1, 1, [1])),
         "a graphs column in a stream of physical type TRIPLES", should=True)
from_neg(C, "An empty graphs column in a stream of physical type TRIPLES.",
         "physical-stream-types", obj(lit_col(lex=["x"]), 1, g=col()),
         "a graphs column in a stream of physical type TRIPLES", should=True,
         comment="An empty column message is still a set graphs field.")
from_neg(C, "message_lengths in a FLAT stream.",
         "stream-types", ONE_F(O(), lengths=[1]), "message_lengths in a FLAT stream", should=True)

# restating the stream options
from_neg(C, "The physical type changes from TRIPLES to QUADS when the stream options are restated.",
         "restating-the-stream-options", [F(options=O(), columns=one()), F(options=OQ(), columns=one())],
         "differs from the physical_type", should=True)
from_neg(C, "The restated stream options are not valid on their own (max_name_table_size 10).",
         "restating-the-stream-options", [F(options=O(), columns=one()), F(options=O(name=10), columns=one())],
         "below the minimum", should=True)
from_neg(C, "After the stream options are restated, a column refers to a name defined only before. The lookups are emptied by the restated options.",
         "restating-the-stream-options",
         [F(options=O(), columns=one()),
          F(options=O(), columns=batch(rows=1, s=iri_col([1]), p=iri_col([2]), o=lit_col(lex=["y"])))],
         "empty lookup entry", should=True)

# sequence layout
from_neg(C, "Corrupt layout: skip runs past the last run value.",
         "sequence-layout", obj(iri_col([0, 0], rep(3, 2), [1]), 5), "skip runs past")
from_neg(C, "Corrupt layout: a repeat run starts after the last run value.",
         "sequence-layout", obj(iri_col([0, 0], rep(2, 2), [1]), 4), "repeat run starts past")
from_neg(C, "Corrupt layout: len_code 15 is the last token, with no extension varint after it.",
         "sequence-layout", obj(iri_col([0, 0], [15], [1]), 20), "without an extension varint")
from_neg(C, "Corrupt layout: a repeat run makes the column longer than row_count.",
         "sequence-layout", obj(iri_col([0, 0], rep(0, 4), [1]), 4), "more than row_count")
from_neg(C, "Corrupt layout: an unbound run makes the column longer than row_count.",
         "sequence-layout", obj(iri_col([0, 0], unb(1, 3), [1]), 4), "more than row_count")
from_neg(C, "A column with more run values than row_count, and no layouts.",
         "sequence-layout", obj(iri_col([0, 0, 0], [], [1]), 2), "more than row_count")
from_neg(C, "Corrupt layout: an extension varint of 2^32 - 1 (a run far longer than the batch).",
         "sequence-layout", obj(iri_col([0], [15, 0xFFFFFFFF], [1]), 4), "more than row_count",
         comment="Consumers should check the run length against row_count before writing any cells (see the security considerations).")


# =============================================================================
# From Jelly – QUADS, RDF 1.1
# =============================================================================

C = QUADS_1_1

DATASET = [
    st
    for i in range(12)
    for st in (
        S(I(f"obs/{i}"), I("value"), L(str(i * 1.5), "decimal"),
          [None, I("sensors/a"), I("sensors/b"), B("g1")][i % 4]),
        S(I(f"obs/{i}"), I("label"), L(f"Observation {i}", lang="en"), [None, I("sensors/a")][i % 2]),
    )
]
from_pos_encoded(C, "Typical dataset: quads in the default graph, in named graphs with IRI names, and in a named graph with a blank node name. Single frame.",
                 "column-batches", DATASET, Opts(physical_type=QUADS, prefix=16, datatype=8))
from_pos_encoded(C, "Typical dataset split into frames of 5 statements.",
                 "column-batches", DATASET, Opts(physical_type=QUADS, prefix=16, datatype=8), max_rows=5)
from_pos_encoded(C, "Quads that are all in the default graph: the batches have no graphs column.",
                 "column-batches", [S(I(f"s{i}"), I("p"), L(str(i))) for i in range(10)],
                 Opts(physical_type=QUADS, prefix=8))
from_pos_encoded(C, "Quads grouped by graph: the graphs column is a few long repeat runs.",
                 "column-batches",
                 [S(I(f"s{i}"), I("p"), L(str(i)), I(f"graph/{i // 10}")) for i in range(40)],
                 Opts(physical_type=QUADS, prefix=8))

from_pos(C, "The graphs column is an empty message: every quad is in the default graph.",
         "columns", grf(col(), 3), in_graphs("___"))
from_pos(C, "Sequence layout example from the specification, in the graphs column: A B B B _ _ C C, layouts = [33, 17, 0].",
         "sequence-layout", grf(iri_col([0, 0, 0], [33, 17, 0], [1]), 8), in_graphs("abbb__cc"))
from_pos(C, "A graphs column shorter than row_count is padded with unbound cells (the default graph).",
         "sequence-layout", grf(iri_col([0, 0], [], [1]), 5), in_graphs("ab___"))
from_pos(C, "An explicit trailing unbound run (producers should omit it, but it is valid).",
         "sequence-layout", grf(iri_col([0, 0], unb(2, 3), [1]), 5), in_graphs("ab___"))
from_pos(C, "Leading unbound run.",
         "sequence-layout", grf(iri_col([0, 0], unb(0, 3), [1]), 5), in_graphs("___ab"))
from_pos(C, "An unbound run and a repeat run at the same position: the unbound run comes first.",
         "sequence-layout", grf(iri_col([0, 0], unb(0, 2) + rep(0, 3), [1]), 6), in_graphs("__aaab"))
from_pos(C, "Repeat run followed by an unbound run, then a single value.",
         "sequence-layout", grf(iri_col([0, 0], rep(0, 3) + unb(0, 2), [1]), 6), in_graphs("aaa__b"))
from_pos(C, "Largest runs that fit in one token: a repeat run of 16 cells (len_code 14) and an unbound run of 15 cells (len_code 14).",
         "sequence-layout", grf(iri_col([0, 0], rep(0, 16) + unb(0, 15), [1]), 32),
         in_graphs("a" * 16 + "_" * 15 + "b"))
from_pos(C, "Smallest runs that need an extension varint: a repeat run of 17 cells and an unbound run of 16 cells (len_code 15, extension 0).",
         "sequence-layout", grf(iri_col([0, 0], rep(0, 17) + unb(0, 16), [1]), 34),
         in_graphs("a" * 17 + "_" * 16 + "b"))
from_pos(C, "Long runs with multi-byte extension varints: a repeat run of 1000 cells and an unbound run of 5000 cells.",
         "sequence-layout", grf(iri_col([0, 0], rep(0, 1000) + unb(0, 5000), [1]), 6001),
         in_graphs("a" * 1000 + "_" * 5000 + "b"))
from_pos(C, "Tokens that take more than one byte, with unbound runs: skip = 4 and skip = 300.",
         "sequence-layout",
         grf(iri_col([0] * 306, unb(4, 1) + unb(300, 2), [1]), 309, opts=OQ(name=512, prefix=8),
             names=[N(*[f"g{i}" for i in range(306)], E + "s", E + "p")], s=const(307, 309), p=const(308, 309)),
         [S(I("s"), I("p"), L(str(i)), g) for i, g in enumerate(
             [I(f"g{i}") for i in range(4)] + [None] + [I(f"g{i}") for i in range(4, 304)] + [None, None]
             + [I(f"g{i}") for i in range(304, 306)])],
         comment="All name_ids are 0: names 1 to 306, which are g0 to g305.")
from_pos(C, "Two unbound runs next to each other (skip = 0 between them), not merged into one.",
         "sequence-layout", grf(iri_col([0], unb(0, 2) + unb(0, 1), [1]), 4), in_graphs("___a"),
         comment="Producers should not write two unbound runs with skip = 0 between them, but the consumer must still decode it.")
from_pos(C, "A graphs column mixing IRIs and blank nodes, with unbound cells.",
         "column-batches",
         grf(col([T_IRI, T_BNODE, T_IRI], unb(1, 1), name_ids=[1, 2], prefix_ids=[1], bnodes=["g"]), 4),
         in_graphs("a_gb", {**IRI_ABC, "g": B("g")}))
from_pos(C, "A blank node graph name with the same label as a blank node subject: the same blank node.",
         "blank-nodes",
         [F(options=OQ(prefix=8),
            columns=std(lit_col(lex=["0", "1"]), 2, s=bnode_col(["x", "y"]), g=bnode_col(["y", "x"])))],
         [S(B("x"), I("p"), L("0"), B("y")), S(B("y"), I("p"), L("1"), B("x"))])

from_neg(C, "A literal in the graphs column.",
         "column-batches", grf(lit_col(lex=["g"]), 1), "a literal in the graphs column", should=True)
from_neg(C, "The physical type changes from QUADS to TRIPLES when the stream options are restated.",
         "restating-the-stream-options", [F(options=OQ(), columns=one()), F(options=O(), columns=one())],
         "differs from the physical_type", should=True)


# =============================================================================
# From Jelly – RDF 1.2 Basic (base direction)
# =============================================================================

C = TRIPLES_1_2_BASIC

from_pos(C, "A column of directional language-tagged strings (ltr and rtl) and a language-tagged string without a direction. The tag en is listed twice in langtags, with different directions.",
         "base-direction",
         obj(lit_col(lex=["hello", "مرحبا", "hello"], kinds=[k_lang(0), k_lang(1), k_lang(2)],
                     langtags=["en", "ar", "en"], dirs=[msgs.DIR_LTR, msgs.DIR_RTL, msgs.DIR_UNSPECIFIED]), 3,
             opts=O(prefix=8, rdf_version=V12B)),
         objs(L("hello", lang="en", d="ltr"), L("مرحبا", lang="ar", d="rtl"), L("hello", lang="en")))
from_pos(C, "A column of literals with a single literal kind: one language tag and base direction for the whole column.",
         "literals-in-columns",
         obj(lit_col(lex=["שלום", "עולם"], kinds=[k_lang(0)], langtags=["he"], dirs=[msgs.DIR_RTL]), 2,
             opts=O(prefix=8, rdf_version=V12B)),
         objs(L("שלום", lang="he", d="rtl"), L("עולם", lang="he", d="rtl")))
from_pos(C, "Directional literals in a stream that declares no RDF version (allowed: no version is announced).",
         "rdf-version",
         obj(lit_col(lex=["x"], kinds=[k_lang(0)], langtags=["en"], dirs=[msgs.DIR_LTR]), 1),
         objs(L("x", lang="en", d="ltr")))
from_pos(C, "A directional literal in a column with several term types.",
         "base-direction",
         obj(col([T_IRI, T_LIT], name_ids=[1], prefix_ids=[1], lex=["x"], lit_kinds=[k_lang(0)],
                 langtags=["en"], dirs=[msgs.DIR_LTR]), 2, opts=O(prefix=8, rdf_version=V12B)),
         objs(I("a"), L("x", lang="en", d="ltr")))
from_pos_encoded(C, "Common usage: labels in several languages and directions, over several frames.",
                 "base-direction",
                 [S(I(f"item{i}"), I("label"), L(f"label {i}", lang=["en", "ar", "he"][i % 3],
                                                    d=[None, "rtl", "rtl", "ltr"][i % 4]))
                  for i in range(40)],
                 Opts(prefix=8, rdf_version=V12B), max_rows=6)

from_neg(C, "langtag_directions with 2 entries for 1 language tag.", "literals-in-columns",
         obj(lit_col(lex=["x"], kinds=[k_lang(0)], langtags=["en"], dirs=[msgs.DIR_LTR, msgs.DIR_RTL]), 1,
             opts=O(prefix=8, rdf_version=V12B)),
         "langtag_directions has 2 entries")
from_neg(C, "langtag_directions set in a column with no language tags.", "literals-in-columns",
         obj(lit_col(lex=["x"], dirs=[msgs.DIR_LTR]), 1, opts=O(prefix=8, rdf_version=V12B)),
         "langtag_directions has 1 entries")
from_neg(C, "langtag_directions with an unknown direction value (7).", "base-direction",
         obj(lit_col(lex=["x"], kinds=[k_lang(0)], langtags=["en"], dirs=[7]), 1, opts=O(prefix=8, rdf_version=V12B)),
         "unknown base direction", should=True)
from_neg(C, "A literal kind refers to a datatype entry holding rdf:dirLangString.", "literals-in-columns",
         obj(lit_col(lex=["x"], kinds=[k_dt(1)]), 1, opts=O(prefix=8, rdf_version=V12B, datatype=4),
             datatypes=[N(RDF_DIR_LANG_STRING)]),
         "needs a language tag", should=True)

C = QUADS_1_2_BASIC

from_pos_encoded(C, "Common usage: directional labels in named graphs, over several frames.",
                 "base-direction",
                 [S(I(f"item{i}"), I("label"), L(f"label {i}", lang=["en", "ar"][i % 2], d=[None, "rtl"][i % 2]),
                    [None, I("graph/a"), I("graph/b")][i % 3])
                  for i in range(20)],
                 Opts(physical_type=QUADS, prefix=8, rdf_version=V12B), max_rows=7)


# =============================================================================
# From Jelly – RDF 1.2 (triple terms)
# =============================================================================

C = TRIPLES_1_2
TT_OPTS = O(prefix=8, rdf_version=V12)


def tt(*triples, n=None, **kw):
    """One frame with the given triple terms as the objects column."""
    return obj(col(triples=list(triples)), n or len(triples), opts=TT_OPTS, **kw)


from_pos(C, "A triple term of three IRIs.", "triple-terms",
         tt(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3))),
         objs(T(I("a"), I("b"), I("c"))))
from_pos(C, "A triple term with a blank node subject and a directional literal object.", "triple-terms",
         tt(triple(s_bnode="b0", p_iri=iri(1, 2), o_literal=lit("x", "en", direction=msgs.DIR_RTL))),
         objs(T(B("b0"), I("b"), L("x", lang="en", d="rtl"))))
from_pos(C, "Triple terms nested three levels deep (in the object position).", "triple-terms",
         tt(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_triple=triple(
             s_iri=iri(None, 3), p_iri=iri(None, 4), o_triple=triple(
                 s_bnode="x", p_iri=iri(None, 5), o_literal=lit("deep"))))),
         objs(T(I("a"), I("b"), T(I("c"), I("d"), T(B("x"), I("e"), L("deep"))))))
from_pos(C, "The IRIs inside the triple terms of a column have their own IRI inference state, separate from the other IRIs of the column.",
         "triple-terms-in-columns",
         obj(col([T_IRI, T_TRIPLE, T_IRI], name_ids=[0, 0], prefix_ids=[1],
                 triples=[triple(s_iri=iri(1, None), p_iri=iri(), o_iri=iri())]), 3, opts=TT_OPTS),
         objs(I("a"), T(I("a"), I("b"), I("c")), I("b")),
         comment="All name_ids are 0. The IRIs of the column (name_ids) give names 1 and 2. The triple term starts from name 0 again: its subject, predicate, and object are names 1, 2, and 3.")
from_pos(C, "The IRI inference state of the triple terms runs through all triple terms of the column, in subject, predicate, object order.",
         "triple-terms-in-columns",
         tt(triple(s_iri=iri(1, None), p_iri=iri(), o_iri=iri()), triple(s_iri=iri(), p_iri=iri(), o_iri=iri()),
            names=[N("a", "b", "c", "d", "e", "f", E + "s", E + "p")], s=const(7, 2), p=const(8, 2)),
         objs(T(I("a"), I("b"), I("c")), T(I("d"), I("e"), I("f"))),
         comment="All name_ids are 0: the second triple term continues from name 3, and keeps the prefix of the first.")
from_pos(C, "The IRI inference state of the triple terms resets at the start of every batch.",
         "triple-terms-in-columns",
         [tt(triple(s_iri=iri(1, None), p_iri=iri(), o_iri=iri()))[0],
          F(columns=more(col(triples=[triple(s_iri=iri(1, None), p_iri=iri(), o_iri=iri())]), 1))],
         objs(T(I("a"), I("b"), I("c")), T(I("a"), I("b"), I("c"))),
         comment="All name_ids are 0. Without the reset, the triple term in the second batch would continue from name 4 (d, e, f).")
from_pos(C, "The name_id inference of the triple terms goes on into a nested triple term.",
         "triple-terms-in-columns",
         tt(triple(s_iri=iri(1, None), p_iri=iri(), o_triple=triple(s_iri=iri(), p_iri=iri(), o_iri=iri()))),
         objs(T(I("a"), I("b"), T(I("c"), I("d"), I("e")))),
         comment="All name_ids are 0: subject and predicate of the outer triple term are names 1 and 2, then the nested triple term gives names 3, 4, and 5.")
from_pos(C, "A triple term with a blank node object.", "triple-terms",
         tt(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_bnode="n")),
         objs(T(I("a"), I("b"), B("n"))))
from_pos(C, "A prefix_id of 0 in the first IRI of the triple terms of a column means no prefix, even after the other IRIs of the column used a prefix.",
         "triple-terms-in-columns",
         obj(col([T_IRI, T_TRIPLE], name_ids=[2], prefix_ids=[1],
                 triples=[triple(s_iri=iri(None, 1), p_iri=iri(1, 2), o_iri=iri(None, 3))]), 2, opts=TT_OPTS,
             names=[N("https://other.org/x", "p", "o", E + "s")], s=const(4, 2), p=const(2, 2, [1])),
         objs(I("p"), T(Iri("https://other.org/x"), I("p"), I("o"))),
         comment="The IRIs of the column use prefix 1. The triple terms have their own state, so the subject, with prefix_id 0, has no prefix: its name holds the whole IRI.")
from_pos(C, "A blank node inside a triple term and the same label in the subjects column are the same blank node.",
         "triple-terms",
         tt(triple(s_bnode="n", p_iri=iri(1, 1), o_iri=iri(None, 2)), s=bnode_col(["n"])),
         [S(B("n"), I("p"), T(B("n"), I("a"), I("b")))])
from_pos(C, "A triple term in a stream that declares no RDF version (allowed: no version is announced).",
         "rdf-version",
         obj(col(triples=[triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3))]), 1),
         objs(T(I("a"), I("b"), I("c"))))
from_pos(C, "The same triple term in consecutive rows, as a repeat run.", "triple-terms-in-columns",
         obj(col(layouts=rep(0, 3), triples=[triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_literal=lit("v"))]), 3,
             opts=TT_OPTS),
         objs(*[T(I("a"), I("b"), L("v"))] * 3))
from_pos(C, "Concatenated streams: the first segment declares RDF 1.1, the second declares RDF 1.2 and has a triple term.",
         "rdf-version",
         [obj(iri_col([1], [], [1]), 1, opts=O(prefix=8, rdf_version=V11))[0],
          tt(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3)))[0]],
         objs(I("a"), T(I("a"), I("b"), I("c"))))
from_pos(C, "A column of triple terms only, with no kinds.", "term-types",
         obj(col(triples=[triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3)),
                          triple(s_iri=iri(1, 4), p_iri=iri(None, 2), o_literal=lit("1", datatype=1))]), 2,
             opts=O(prefix=8, datatype=4, rdf_version=V12), datatypes=[N(XSD + "integer")]),
         objs(T(I("a"), I("b"), I("c")), T(I("d"), I("b"), L("1", "integer"))),
         comment="kinds may be empty when all run values are of one term type. The second triple term has name_id 4 for its subject, and name_id 2 for its predicate.")
from_pos(C, "Directional literals in a stream that declares RDF 1.2 (which includes RDF 1.2 Basic).",
         "rdf-version",
         obj(lit_col(lex=["x"], kinds=[k_lang(0)], langtags=["en"], dirs=[msgs.DIR_RTL]), 1,
             opts=O(prefix=8, rdf_version=V12)),
         objs(L("x", lang="en", d="rtl")))
from_pos_encoded(C, "Common usage: reifiers with rdf:reifies and triple terms, with IRIs, literals, and nested triple terms, over several frames.",
                 "triple-terms",
                 [st for i in range(15) for st in (
                     S(I(f"r{i}"), Iri(RDF + "reifies"),
                       T(I(f"s{i % 5}"), I("knows"), I(f"o{i}")) if i % 4 else
                       T(B(f"x{i}"), I("says"), T(I(f"s{i}"), I("age"), L(str(i), "integer")))),
                     S(I(f"r{i}"), I("confidence"), L(f"0.{i}", "decimal")),
                 )],
                 Opts(prefix=8, datatype=4, rdf_version=V12), max_rows=8)

from_neg(C, "A triple term without a subject.", "triple-terms",
         tt(triple(p_iri=iri(1, 2), o_iri=iri(None, 3))), "no subject")
from_neg(C, "A triple term without a predicate.", "triple-terms",
         tt(triple(s_iri=iri(1, 1), o_iri=iri(None, 3))), "no predicate")
from_neg(C, "A triple term without an object.", "triple-terms",
         tt(triple(s_iri=iri(1, 1), p_iri=iri(None, 2))), "no object")


def tt_lit(literal, datatypes=None):
    """A frame with one triple term whose object is the given RdfLiteral."""
    return obj(col(triples=[triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_literal=literal)]), 1,
               opts=O(prefix=8, datatype=4, rdf_version=V12), datatypes=datatypes)


from_neg(C, "A literal in a triple term with datatype 0, which is invalid.", "literals",
         tt_lit(lit("1", datatype=0), [N(XSD + "int")]), "datatype 0")
from_neg(C, "A literal in a triple term with a direction but no language tag.", "literals",
         tt_lit(lit("x", direction=msgs.DIR_LTR)), "direction without langtag")
from_neg(C, "A literal in a triple term with a direction and a datatype.", "literals",
         tt_lit(lit("1", datatype=1, direction=msgs.DIR_LTR), [N(XSD + "int")]), "direction without langtag")
from_neg(C, "A literal in a triple term with an unknown direction value (3).", "base-direction",
         tt_lit(lit("x", "en", direction=3)), "unknown base direction", should=True)
from_neg(C, "A literal in a triple term whose datatype is rdf:langString.", "literals",
         tt_lit(lit("x", datatype=1), [N(RDF_LANG_STRING)]), "needs a language tag", should=True)
from_neg(C, "A literal in a triple term whose datatype is rdf:dirLangString.", "literals",
         tt_lit(lit("x", datatype=1), [N(RDF_DIR_LANG_STRING)]), "needs a language tag", should=True)
from_neg(C, "kinds is empty, but the column has values of two term types: an IRI and a triple term.",
         "term-types",
         obj(col(name_ids=[4], prefix_ids=[1], triples=[triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3))]), 2,
             opts=TT_OPTS),
         "kinds has 0 bytes for 2 values")
from_neg(C, "A triple term in the subjects column.", "column-batches",
         tt(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3)),
            s=col(triples=[triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3))])),
         "a triple term in the subjects column", should=True)
from_neg(C, "A triple term in the predicates column.", "column-batches",
         tt(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3)),
            p=col(triples=[triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3))])),
         "a triple term in the predicates column", should=True)

C = QUADS_1_2

from_pos_encoded(C, "Common usage: triple terms in named graphs and in the default graph, over several frames.",
                 "triple-terms",
                 [S(I(f"r{i}"), Iri(RDF + "reifies"), T(I(f"s{i % 3}"), I("p"), L(str(i), "integer")),
                    [None, I("graph/a"), B("g")][i % 3])
                  for i in range(20)],
                 Opts(physical_type=QUADS, prefix=8, datatype=4, rdf_version=V12), max_rows=6)
from_neg(C, "A triple term in the graphs column.", "column-batches",
         grf(col(triples=[triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3))]), 1,
             opts=OQ(prefix=8, rdf_version=V12)),
         "a triple term in the graphs column", should=True)


# =============================================================================
# From Jelly – RDF Messages (stream type MESSAGES)
# =============================================================================

C = MESSAGES
M = Messages


def mobj(o, n, lengths, opts=None, **kw):
    """One frame of a stream of RDF Messages: a standard batch with the given objects column."""
    return obj(o, n, opts=OM(prefix=8) if opts is None else opts, lengths=lengths, **kw)


def lits(*lexes):
    """Statements ex:s ex:p "<lex>", one per lexical form."""
    return objs(*(L(x) for x in lexes))


def lcol(*lexes):
    return lit_col(lex=list(lexes))


from_pos_encoded(C, "Ten messages of three statements each, in one frame.",
                 "message-boundaries",
                 M([S(I(f"m{i}"), I("p"), L(str(j))) for j in range(3)] for i in range(10)),
                 Opts(prefix=8, stream_type=msgs.MESSAGES))
from_pos_encoded(C, "Messages larger than a frame: each message spans several frames.",
                 "message-boundaries",
                 M([S(I(f"m{i}"), I("p"), L(str(j))) for j in range(10)] for i in range(3)),
                 Opts(prefix=8, stream_type=msgs.MESSAGES), max_rows=4)
from_pos_encoded(C, "Messages with blank nodes, using the same labels in every message.",
                 "blank-nodes",
                 M([S(B("x"), I("p"), B(f"y{j}")) for j in range(3)] for i in range(4)),
                 Opts(stream_type=msgs.MESSAGES), max_rows=5,
                 comment="Blank node labels are scoped to one message, so the label x in each message is a different blank node. Messages are compared one at a time, so this test does not check that a consumer keeps them apart.")
from_pos_encoded(C, "Messages that are RDF datasets: quads in the default graph and in named graphs.",
                 "stream-types",
                 M([S(I(f"m{i}"), I("p"), L(str(j)), [None, I("g")][j % 2]) for j in range(4)] for i in range(3)),
                 Opts(physical_type=QUADS, prefix=8, stream_type=msgs.MESSAGES), max_rows=5)

from_pos(C, "Example from the specification: a statement left over from the previous frame, and message_lengths [2, 0, 1] in a batch of 5 statements.",
         "message-boundaries",
         [mobj(lcol("0"), 1, None)[0],
          F(columns=more(lcol("1", "2", "3", "4", "5"), 5, lengths=[2, 0, 1])),
          F(columns=more(lcol("6"), 1, lengths=[1]))],
         M([lits("0", "1", "2"), [], lits("3"), lits("4", "5", "6")]),
         comment="The first message is 0, 1, 2. The value 0 then ends an empty message. The value 1 adds statement 3 and ends that message. Statements 4 and 5 start the next message, and the last frame adds 6 and ends it.")
from_pos(C, "One message per frame: message_lengths is [row_count] in every frame.",
         "message-boundaries",
         [mobj(lcol("a", "b"), 2, [2])[0], F(columns=more(lcol("c"), 1, lengths=[1]))],
         M([lits("a", "b"), lits("c")]))
from_pos(C, "Empty messages: a value of 0 at the start of a batch and two in a row.",
         "message-boundaries",
         [mobj(lcol("a"), 1, [0, 1, 0, 0])[0]],
         M([[], lits("a"), [], []]))
from_pos(C, "A batch with row_count 0 and message_lengths [0]: an empty message.",
         "message-boundaries",
         [mobj(lcol("a"), 1, [1])[0], F(columns=batch(lengths=[0])), F(columns=more(lcol("b"), 1, lengths=[1]))],
         M([lits("a"), [], lits("b")]))
from_pos(C, "A batch with row_count 0 and message_lengths [0] ends a message started in the previous frame.",
         "message-boundaries",
         [mobj(lcol("a"), 1, None)[0], F(columns=batch(lengths=[0])), F(columns=more(lcol("b"), 1, lengths=[1]))],
         M([lits("a"), lits("b")]))
from_pos(C, "The last message has no boundary: it ends at the end of the stream.",
         "message-boundaries",
         [mobj(lcol("a", "b", "c"), 3, [1])[0]],
         M([lits("a"), lits("b", "c")]))
from_pos(C, "The stream ends right after a boundary: no further message is added.",
         "message-boundaries",
         [mobj(lcol("a", "b"), 2, [2])[0], F()],
         M([lits("a", "b")]))
from_pos(C, "Restated stream options end the current message.",
         "restating-the-stream-options",
         [mobj(lcol("a", "b"), 2, [1])[0],
          F(options=OM(), columns=batch(rows=1, names=[N(E + "s", E + "p")], s=iri_col([1]), p=iri_col([2]),
                                         o=lcol("c"), lengths=[1]))],
         M([lits("a"), lits("b"), lits("c")]),
         comment="The statement b has no boundary after it, but the restated options end its message.")
from_pos(C, "Restated stream options right after a boundary: no empty message is added.",
         "restating-the-stream-options",
         [mobj(lcol("a"), 1, [1])[0],
          F(options=OM(), columns=batch(rows=1, names=[N(E + "s", E + "p")], s=iri_col([1]), p=iri_col([2]),
                                         o=lcol("b"), lengths=[1]))],
         M([lits("a"), lits("b")]))
from_pos(C, "Lookup entries are kept from one message to the next.",
         "stream-types",
         [mobj(iri_col([1], [], [1]), 1, [1])[0], F(columns=more(iri_col([2], [], [1]), 1, lengths=[1]))],
         M([objs(I("a")), objs(I("b"))]))
from_pos(C, "A blank node label used in two frames of the same message: the same blank node.",
         "blank-nodes",
         [mobj(bnode_col(["x"]), 1, None)[0], F(columns=more(bnode_col(["x"]), 1, lengths=[1]))],
         M([objs(B("x"), B("x"))]))
from_pos(C, "Empty frames between the frames of a message.",
         "stream-frames",
         [mobj(lcol("a"), 1, None)[0], F(), F(columns=more(lcol("b"), 1, lengths=[1])), F()],
         M([lits("a", "b")]))

from_neg(C, "message_lengths add up to more than row_count.", "message-boundaries",
         mobj(lcol("a", "b"), 2, [2, 1]), "more than row_count")
from_neg(C, "message_lengths with a value larger than row_count.", "message-boundaries",
         mobj(lcol("a"), 1, [5]), "more than row_count")
from_neg(C, "The stream type changes from MESSAGES to FLAT when the stream options are restated.",
         "restating-the-stream-options",
         [F(options=OM(), columns=one(lengths=[1])), F(options=O(), columns=one())],
         "differs from the stream_type", should=True)


# =============================================================================
# To Jelly
# =============================================================================

C = TRIPLES_1_1

to_pos(C, "IRIs only, prefix lookup enabled.", "iris-in-columns",
       [S(I(f"s{i % 3}"), Iri(f"https://schema.org/p{i % 2}"), I(f"o{i}")) for i in range(12)],
       Opts(prefix=8))
to_pos(C, "IRIs only, prefix lookup disabled.", "iris-in-columns",
       [S(I(f"s{i}"), I("p"), Iri(f"urn:x:{i}")) for i in range(8)], Opts())
to_pos(C, "Simple, typed, and language-tagged literals.", "literals-in-columns",
       [S(I("s"), I(f"p{i % 3}"), [L(f"text {i}"), L(str(i), "integer"), L("1.5", "decimal"), L("y", lang="en"),
                                   L("z", lang="pl")][i % 5]) for i in range(15)],
       Opts(datatype=8))
to_pos(C, "Blank nodes as subjects and objects, repeated across frames.", "blank-nodes",
       [S(B(f"b{i // 2}"), I("knows"), B("shared")) for i in range(10)], Opts(), max_rows=3)
to_pos(C, "A typical graph with prefix and datatype lookups.", "column-batches",
       PEOPLE, Opts(prefix=16, datatype=8))
to_pos(C, "1000 statements with over 600 distinct IRIs and a name lookup of 128 entries. The producer has to evict lookup entries and end frames before their working set overflows the tables.",
       "the-working-set-of-a-batch", MANY, Opts(name=128, prefix=16, datatype=4))
to_pos(C, "Non-ASCII IRIs and literals, and characters that need escaping in text formats.", "rdf-terms",
       UNICODE, Opts(prefix=16))
to_pos(C, "Duplicate statements: all of them must be kept, in order.", "ordering",
       [S(I("s"), I("p"), L("same"))] * 5 + [S(I("s"), I("p"), L("other"))] + [S(I("s"), I("p"), L("same"))] * 2,
       Opts())
to_pos(C, "An empty graph.", "stream-options",
       [], Opts(),
       comment="The expected output has a frame with the stream options and no statements. An output without any non-empty frame, such as an empty file, is also correct.")
to_pos(C, "Statements grouped by subject.", "column-batches", GROUPED, Opts(prefix=8))
to_pos(C, "Stream options that declare RDF 1.1.", "rdf-version",
       [S(I("s"), I("p"), L("x", lang="en"))], Opts(rdf_version=V11))

to_neg(C, "A typed literal, with the datatype lookup disabled.", "stream-options",
       [S(I("s"), I("p"), L("1", "integer"))], Opts(), "datatype lookup is disabled")

C = QUADS_1_1

to_pos(C, "Quads in the default graph, in named graphs with IRI names, and in a named graph with a blank node name.",
       "column-batches", DATASET, Opts(physical_type=QUADS, prefix=16, datatype=8))
to_pos(C, "Quads that are all in the default graph.", "column-batches",
       [S(I(f"s{i}"), I("p"), L(str(i))) for i in range(5)], Opts(physical_type=QUADS, prefix=8))
to_pos(C, "Quads grouped by graph, over several frames.", "column-batches",
       [S(I(f"s{i}"), I("p"), L(str(i)), I(f"graph/{i // 10}")) for i in range(40)],
       Opts(physical_type=QUADS, prefix=8), max_rows=16)
to_pos(C, "A blank node that is a graph name and a subject.", "blank-nodes",
       [S(B("x"), I("p"), L("0"), B("y")), S(B("y"), I("p"), L("1"), B("x"))], Opts(physical_type=QUADS))

C = TRIPLES_1_2_BASIC
DIR_DATA = [S(I("s"), I("label"), L("hello", lang="en", d="ltr")), S(I("s"), I("label"), L("مرحبا", lang="ar", d="rtl")),
            S(I("s"), I("label"), L("plain", lang="en"))]
to_pos(C, "Directional language-tagged strings, stream options declaring RDF 1.2 Basic.", "base-direction",
       DIR_DATA, Opts(rdf_version=V12B))
to_pos(C, "Directional language-tagged strings, stream options declaring no RDF version.", "rdf-version",
       DIR_DATA, Opts())
to_pos(C, "One language tag and direction for a whole column (a single literal kind).",
       "literals-in-columns", [S(I(f"s{i}"), I("label"), L(f"שורה {i}", lang="he", d="rtl")) for i in range(5)],
       Opts(rdf_version=V12B))
to_neg(C, "A directional language-tagged string, with stream options declaring RDF 1.1.", "base-direction",
       DIR_DATA, Opts(rdf_version=V11), "a base direction, but the stream declares RDF 1.1")

C = QUADS_1_2_BASIC
to_pos(C, "Directional language-tagged strings in named graphs.", "base-direction",
       [S(I("s"), I("label"), L("hello", lang="en", d="ltr"), I("g1")), S(I("s"), I("label"), L("مرحبا", lang="ar", d="rtl"))],
       Opts(physical_type=QUADS, rdf_version=V12B))

C = TRIPLES_1_2
TT_DATA = [S(I("r1"), Iri(RDF + "reifies"), T(I("a"), I("b"), I("c"))),
           S(I("r2"), Iri(RDF + "reifies"), T(B("n"), I("b"), L("v", lang="en", d="ltr"))),
           S(B("n"), I("says"), T(I("a"), I("b"), T(I("c"), I("d"), L("1", "integer"))))]
to_pos(C, "Triple terms, including nested ones, stream options declaring RDF 1.2.", "triple-terms",
       TT_DATA, Opts(prefix=8, datatype=4, rdf_version=V12))
to_pos(C, "Triple terms, stream options declaring no RDF version.", "rdf-version",
       TT_DATA, Opts(prefix=8, datatype=4))
TT_PLAIN = [S(I("r1"), Iri(RDF + "reifies"), T(I("a"), I("b"), I("c"))),
            S(B("n"), I("says"), T(I("a"), I("b"), T(I("c"), I("d"), L("1", "integer"))))]
to_neg(C, "A triple term, with stream options declaring RDF 1.2 Basic.", "rdf-version",
       TT_PLAIN, Opts(prefix=8, datatype=4, rdf_version=V12B), "a triple term, but the stream declares")
to_neg(C, "A triple term, with stream options declaring RDF 1.1.", "rdf-version",
       TT_PLAIN, Opts(prefix=8, datatype=4, rdf_version=V11), "a triple term, but the stream declares")

C = QUADS_1_2
to_pos(C, "Triple terms in named graphs.", "triple-terms",
       [S(I(f"r{i}"), Iri(RDF + "reifies"), T(I(f"s{i}"), I("p"), L(str(i))), [None, I("g")][i % 2]) for i in range(4)],
       Opts(physical_type=QUADS, prefix=8, rdf_version=V12))

C = MESSAGES
to_pos(C, "Several messages of a few statements each.", "message-boundaries",
       M([S(I(f"m{i}"), I("p"), L(str(j))) for j in range(i % 3 + 1)] for i in range(6)),
       Opts(prefix=8, stream_type=msgs.MESSAGES))
to_pos(C, "Messages with an empty message among them.", "message-boundaries",
       M([lits("a"), [], lits("b", "c")]), Opts(stream_type=msgs.MESSAGES))
to_pos(C, "Messages larger than a frame.", "message-boundaries",
       M([S(I(f"m{i}"), I("p"), L(str(j))) for j in range(10)] for i in range(3)),
       Opts(prefix=8, stream_type=msgs.MESSAGES), max_rows=4)
to_pos(C, "Messages with blank nodes, using the same labels in every message.", "blank-nodes",
       M([S(B("x"), I("p"), B(f"y{j}")) for j in range(2)] for i in range(3)),
       Opts(stream_type=msgs.MESSAGES),
       comment="Each input file is one message, and its blank node labels are scoped to that message.")
to_pos(C, "Messages that are RDF datasets.", "stream-types",
       M([S(I(f"m{i}"), I("p"), L(str(j)), [None, I("g")][j % 2]) for j in range(3)] for i in range(3)),
       Opts(physical_type=QUADS, prefix=8, stream_type=msgs.MESSAGES))


# =============================================================================
# From Jelly – more cases (kept at the end so that the numbers of the others stay)
# =============================================================================

from_neg(TRIPLES_1_1, "A datatype lookup entry with an identifier larger than the table size.",
         "prefix-name-and-datatype-lookup-entries", ONE_F(O(datatype=4), datatypes=[N(XSD + "int", id=5)]),
         "outside of the table", should=True)
from_neg(TRIPLES_1_1, "The restated stream options have version tag 0.",
         "restating-the-stream-options", [F(options=O(), columns=one()), F(options=O(version=0), columns=one())],
         "version tag is 0", should=True)
from_neg(TRIPLES_1_1, "The restated stream options set generalized_statements, which is used only in Jelly-RDF 1.0.x and 1.1.x.",
         "restating-the-stream-options", [F(options=O(), columns=one()), F(options=O(generalized=True), columns=one())],
         "generalized_statements is set", should=True)
from_pos(TRIPLES_1_1, "Prefix and datatype lookup identifiers continue across frames: entries with id 0 in the second frame take the next identifiers.",
         "packed-lookup-entries",
         [F(options=O(prefix=8, datatype=4),
            columns=batch(rows=1, prefixes=[N(E)], names=[N("s", "p")], datatypes=[N(XSD + "integer")],
                          s=iri_col([1], [], [1]), p=iri_col([2], [], [1]), o=lit_col(lex=["1"], kinds=[k_dt(1)]))),
          F(columns=batch(rows=1, prefixes=[N("https://b.org/")], datatypes=[N(XSD + "decimal")],
                          s=iri_col([1], [], [2]), p=iri_col([2], [], [1]), o=lit_col(lex=["1.5"], kinds=[k_dt(2)])))],
         [S(I("s"), I("p"), L("1", "integer")), S(Iri("https://b.org/s"), I("p"), L("1.5", "decimal"))])

from_neg(TRIPLES_1_2, "A triple term refers to a name that was never defined.", "triple-terms",
         tt(triple(s_iri=iri(1, 50), p_iri=iri(None, 2), o_iri=iri(None, 3))), "empty lookup entry", should=True)
from_neg(TRIPLES_1_2, "A literal in a triple term refers to a datatype that was never defined.", "literals",
         tt_lit(lit("1", datatype=2), [N(XSD + "int")]), "empty lookup entry", should=True)

from_neg(MESSAGES, "The stream type changes from FLAT to MESSAGES when the stream options are restated.",
         "restating-the-stream-options", [F(options=O(), columns=one()), F(options=OM(), columns=one(lengths=[1]))],
         "differs from the stream_type", should=True)
