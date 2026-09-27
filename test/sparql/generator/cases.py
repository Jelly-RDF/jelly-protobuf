"""Definitions of the Jelly-SPARQL conformance test cases.

Each case is registered with one of from_pos, from_neg, to_pos, to_neg. Cases
are numbered in the order they are registered, per direction, category, and
polarity – append new cases at the end of their group to keep the numbers of
existing cases stable.

`see` is the anchor of the rule in the specification that the case exercises.
`error` (negative cases) is a fragment of the reference decoder's or encoder's
error message; the generator checks that the case fails for that reason.
"""

from dataclasses import dataclass, field
from typing import Optional

import msgs
import pb
from encoder import Opts, encode
from model import (
    RDF_DIR_LANG_STRING,
    RDF_LANG_STRING,
    XSD,
    XSD_STRING,
    AskResult,
    Bnode,
    Iri,
    Lit,
    ResultSet,
    Triple,
)
from msgs import (
    bnode_col,
    entry,
    frame,
    iri,
    iri_col,
    lit,
    lit_col,
    poly_col,
    rep,
    t_bnode,
    t_empty,
    t_iri,
    t_lit,
    t_triple,
    triple,
    unb,
)

SELECT_1_1 = "select_rdf_1_1"
ASK = "ask"
SELECT_1_2_BASIC = "select_rdf_1_2_basic"
SELECT_1_2 = "select_rdf_1_2"
CATEGORIES = [SELECT_1_1, ASK, SELECT_1_2_BASIC, SELECT_1_2]


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
    expected: object = None  # from_jelly positive: the result
    error: Optional[str] = None  # negative: expected error fragment
    input: object = None  # to_jelly: the result to serialize
    opts: Optional[Opts] = None  # to_jelly: stream options
    max_rows: int = 64  # to_jelly: frame size of the reference output
    should: bool = False  # the rule is a SHOULD in the spec, not a MUST


CASES = []


def from_pos(category, name, see, frames, expected, comment=None, raw=None, should=False):
    CASES.append(Case("from_jelly", category, True, name, see, comment, frames, raw, expected,
                      should=should))


def from_neg(category, name, see, frames, error, comment=None, raw=None, should=False):
    CASES.append(Case("from_jelly", category, False, name, see, comment, frames, raw, error=error,
                      should=should))


def from_pos_encoded(category, name, see, result, opts, max_rows=64, comment=None):
    """A positive case whose input is produced by the reference encoder."""
    from_pos(category, name, see, encode(result, opts, max_rows), result, comment)


def to_pos(category, name, see, result, opts, max_rows=64, comment=None):
    CASES.append(
        Case("to_jelly", category, True, name, see, comment, input=result, opts=opts,
             max_rows=max_rows)
    )


def to_neg(category, name, see, result, opts, error, comment=None):
    CASES.append(
        Case("to_jelly", category, False, name, see, comment, error=error, input=result,
             opts=opts)
    )


# --- helpers ------------------------------------------------------------------

E = "http://example.org/"
O = msgs.options
F = frame


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


def RS(vars, *rows, links=None) -> ResultSet:
    return ResultSet(list(vars), [dict(r) for r in rows], links or [])


def row(**kw):
    return kw


def N(*values, id=None):
    return entry(list(values), id)


def ex_frame_1var(col, rows, names=("a", "b", "c", "d", "e"), extra=None, **kw):
    """One frame, prefix E at 1, the given names, one variable ?v."""
    k = dict(options=O(prefix=8), vars=[("v", 0)], rows=rows, prefixes=[N(E)],
             names=[N(*names)], iri=[col], trailer="")
    k.update(kw)
    k.update(extra or {})
    return [F(**k)]


def cells(values, layout):
    """Expected rows for ?v from a compact cell string, e.g. "ab_c"."""
    out = []
    for ch in layout:
        out.append({} if ch == "_" else {"v": values[ch]})
    return out


def rs_v(values, layout):
    return ResultSet(["v"], cells(values, layout))


IRI_ABC = {c: I(c) for c in "abcde"}
LIT_ABC = {c: L(c) for c in "abcde"}


# =============================================================================
# From Jelly – SELECT, RDF 1.1
# =============================================================================

C = SELECT_1_1

# --- common usage patterns (produced by the reference encoder) -------------------

TYPICAL = RS(
    ["person", "name", "age", "homepage"],
    *[
        row(person=I(f"person/{i}"), name=L(f"Person {i}", lang="en"),
            age=L(str(20 + i), "integer"), homepage=Iri(f"https://site{i % 3}.example/home"))
        for i in range(10)
    ],
)
from_pos_encoded(C, "Typical SELECT result: IRIs, language-tagged and typed literals. Prefix and datatype lookups enabled. Single frame.",
                 "result-frames", TYPICAL, Opts(prefix=16, datatype=8))
from_pos_encoded(C, "Typical SELECT result with the prefix lookup disabled – names hold whole IRIs.",
                 "stream-options", TYPICAL, Opts(prefix=0, datatype=8))
from_pos_encoded(C, "Typical SELECT result split into frames of 3 rows. Lookup entries carry over between frames.",
                 "prefix-name-and-datatype-lookup-entries", TYPICAL, Opts(prefix=16, datatype=8), max_rows=3)

MANY = RS(
    ["s", "p", "o", "n"],
    *[
        row(s=I(f"s{i % 97}"), p=I(f"p{i % 7}"), o=I(f"o{i}"), n=L(str(i % 50), "integer"))
        for i in range(1000)
    ],
)
from_pos_encoded(C, "1000 rows with over 1000 distinct IRIs, name lookup of size 128. The name lookup entries are overwritten many times (LRU), and frames end early when the working set would not fit.",
                 "the-working-set-of-a-frame", MANY, Opts(name=128, prefix=16, datatype=4))

OPTIONAL = RS(
    ["book", "title", "author", "isbn"],
    *[
        {k: v for k, v in {
            "book": I(f"book/{i // 4}"),
            "title": L(f"Title {i // 4}"),
            "author": I(f"author/{i % 3}") if i % 5 else None,
            "isbn": L(f"978-{i // 8}") if i % 3 == 0 else None,
        }.items() if v is not None}
        for i in range(60)
    ],
)
from_pos_encoded(C, "Sparse result, as produced by OPTIONAL: many unbound cells and values repeated in consecutive rows (repeat and unbound runs).",
                 "sequence-layout", OPTIONAL, Opts(prefix=16), max_rows=25)

MIXED = RS(
    ["x", "label"],
    *([row(x=I(f"n{i}"), label=L(f"n{i}")) for i in range(5)]
      + [row(x=L(f"literal {i}"), label=L(f"l{i}")) for i in range(5)]
      + [row(x=B(f"b{i}"), label=L(f"b{i}")) for i in range(5)]
      + [row(x=I("n1") if i % 2 else L("mixed"), label=L("m")) for i in range(5)]),
)
from_pos_encoded(C, "A variable whose values change type between frames: IRIs, then literals, then blank nodes, then a mix. The header is restated whenever the column layout changes, and the last frame uses a polymorphic column.",
                 "restating-the-header", MIXED, Opts(prefix=16), max_rows=5)

UNICODE = RS(
    ["s", "text"],
    row(s=Iri("http://example.org/zażółć/gęślą#jaźń"), text=L("Zażółć gęślą jaźń")),
    row(s=Iri("http://例え.jp/テスト"), text=L("日本語のテキスト", lang="ja")),
    row(s=Iri("http://example.org/emoji/😀"), text=L("emoji 😀🎉 and a combining mark: é")),
    row(s=I("rtl"), text=L("مرحبا بالعالم", lang="ar")),
    row(s=I("escapes"), text=L("quotes \" and ' backslash \\ tab \t newline \n return \r")),
    row(s=I("empty"), text=L("")),
)
from_pos_encoded(C, "Non-ASCII IRIs and literals (Polish, Japanese, Arabic, emoji, combining marks), characters that need escaping in text formats, and an empty literal.",
                 "rdf-terms", UNICODE, Opts(prefix=16))

BNODES = RS(
    ["s", "o"],
    *[row(s=B(f"b{i // 3}"), o=B(f"c{i % 4}")) for i in range(24)],
)
from_pos_encoded(C, "Blank nodes whose labels repeat across rows and across frames. Equal labels are the same blank node in the whole stream.",
                 "blank-node-columns", BNODES, Opts(), max_rows=5)

from_pos_encoded(C, "An empty result set with three variables: one frame with the options and the header, no rows.",
                 "frames-with-no-rows", RS(["s", "p", "o"]), Opts())

from_pos_encoded(C, "2000 rows of a single integer variable, in frames of 256 rows. Literal columns in the lexical form.",
                 "literal-columns", RS(["n"], *[row(n=L(str(i), "integer")) for i in range(2000)]),
                 Opts(datatype=4), max_rows=256)

from_pos_encoded(C, "Every row in its own frame.",
                 "result-frames", RS(["s", "o"], *[row(s=I(f"s{i}"), o=L(str(i))) for i in range(10)]),
                 Opts(prefix=4), max_rows=1)

# --- sequence layout ---------------------------------------------------------------

from_pos(C, "Sequence layout example from the specification: A B B B _ _ C C, layouts = [33, 17, 0].",
         "sequence-layout",
         [F(options=O(), vars=[("v", 0)], rows=8,
            literal=[lit_col(lex=["A", "B", "C"], layouts=[33, 17, 0])], trailer="")],
         rs_v({"A": L("A"), "B": L("B"), "C": L("C")}, "ABBB__CC"))
from_pos(C, "Every cell bound, no value repeated in consecutive rows: layouts is empty.",
         "sequence-layout",
         ex_frame_1var(iri_col([0, 0, 0, 0], [], [1]), 4),
         rs_v(IRI_ABC, "abcd"))
from_pos(C, "A column shorter than row_count is padded with unbound cells.",
         "sequence-layout",
         ex_frame_1var(iri_col([0, 0], [], [1]), 5),
         rs_v(IRI_ABC, "ab___"))
from_pos(C, "An explicit trailing unbound run (producers should omit it, but it is valid).",
         "sequence-layout",
         ex_frame_1var(iri_col([0, 0], unb(2, 3), [1]), 5),
         rs_v(IRI_ABC, "ab___"))
from_pos(C, "Leading unbound run.",
         "sequence-layout",
         ex_frame_1var(iri_col([0, 0], unb(0, 3), [1]), 5),
         rs_v(IRI_ABC, "___ab"))
from_pos(C, "An unbound run and a repeat run at the same position: the unbound run comes first.",
         "sequence-layout",
         ex_frame_1var(iri_col([0, 0], unb(0, 2) + rep(0, 3), [1]), 6),
         rs_v(IRI_ABC, "__aaab"))
from_pos(C, "Two repeat runs in a row (skip = 0 between them), then the implicit tail.",
         "sequence-layout",
         ex_frame_1var(iri_col([0, 0, 0], rep(0, 2) + rep(0, 3), [1]), 6),
         rs_v(IRI_ABC, "aabbbc"))
from_pos(C, "Repeat run followed by an unbound run, then a single value.",
         "sequence-layout",
         ex_frame_1var(iri_col([0, 0], rep(0, 3) + unb(0, 2), [1]), 6),
         rs_v(IRI_ABC, "aaa__b"))
from_pos(C, "Largest runs that fit in one token: a repeat run of 16 cells (len_code 14) and an unbound run of 15 cells (len_code 14).",
         "sequence-layout",
         ex_frame_1var(iri_col([0, 0], rep(0, 16) + unb(0, 15), [1]), 32),
         rs_v(IRI_ABC, "a" * 16 + "_" * 15 + "b"))
from_pos(C, "Smallest runs that need an extension varint: a repeat run of 17 cells and an unbound run of 16 cells (len_code 15, extension 0).",
         "sequence-layout",
         ex_frame_1var(iri_col([0, 0], rep(0, 17) + unb(0, 16), [1]), 34),
         rs_v(IRI_ABC, "a" * 17 + "_" * 16 + "b"))
from_pos(C, "Long runs with multi-byte extension varints: a repeat run of 1000 cells and an unbound run of 5000 cells.",
         "sequence-layout",
         ex_frame_1var(iri_col([0, 0], rep(0, 1000) + unb(0, 5000), [1]), 6001),
         rs_v(IRI_ABC, "a" * 1000 + "_" * 5000 + "b"))
from_pos(C, "Tokens that take more than one byte: skip = 4 and skip = 300.",
         "sequence-layout",
         [F(options=O(), vars=[("v", 0)], rows=309,
            literal=[lit_col(lex=[str(i) for i in range(306)],
                             layouts=unb(4, 1) + unb(300, 2))], trailer="")],
         ResultSet(["v"], [{"v": L(str(i))} for i in range(4)] + [{}]
                   + [{"v": L(str(i))} for i in range(4, 304)] + [{}, {}]
                   + [{"v": L(str(i))} for i in range(304, 306)]))
from_pos(C, "The sequence layout in every column type: blank node, literal (lexical form), literal (full form), and polymorphic columns.",
         "sequence-layout",
         [F(options=O(prefix=8), vars=[("b", 0), ("l", 1), ("f", 2), ("p", 3)], rows=6,
            prefixes=[N(E)], names=[N("a")],
            bnode=[bnode_col(["x", "y"], rep(0, 2) + unb(0, 2))],
            literal=[lit_col(lex=["1", "2"], layouts=unb(0, 1) + rep(0, 4)),
                     lit_col(values=[lit("hi", langtag="en"), lit("hej", langtag="sv")],
                             layouts=unb(1, 3))],
            poly=[poly_col([t_iri(1, 1), t_bnode("x"), t_lit("z")], rep(1, 3))],
            trailer="")],
         RS(["b", "l", "f", "p"],
            row(b=B("x"), f=L("hi", lang="en"), p=I("a")),
            row(b=B("x"), l=L("1"), p=B("x")),
            row(l=L("1"), p=B("x")),
            row(l=L("1"), p=B("x")),
            row(b=B("y"), l=L("1"), f=L("hej", lang="sv"), p=L("z")),
            row(l=L("2"))),
         comment="Cells: b = x x _ _ y _; l = _ 1 1 1 1 2; f = hi _ _ _ hej _; p = a x x x z _.")
from_pos(C, "Equal values in consecutive rows stored as separate run values, without a repeat run. Both rows must be kept – consumers must not deduplicate.",
         "ordering",
         ex_frame_1var(iri_col([1, 1, 1, 2], [], [1]), 4),
         rs_v(IRI_ABC, "aaab"))
from_pos(C, "Duplicate solutions within a frame and across frames are all preserved, in order.",
         "ordering",
         [F(options=O(prefix=8), vars=[("s", 0), ("o", 1)], rows=3, prefixes=[N(E)],
            names=[N("a", "b")],
            iri=[iri_col([1], rep(0, 3), [1]), iri_col([2], rep(0, 3), [1])]),
          F(rows=2, iri=[iri_col([1], rep(0, 2), [1]), iri_col([2], rep(0, 2), [1])], trailer="")],
         RS(["s", "o"], *[row(s=I("a"), o=I("b"))] * 5))

# --- IRI columns ---------------------------------------------------------------------

from_pos(C, "IRI column example from the specification: name_ids [0, 0, 1, 3], prefix_ids [1, 0, 0, 2].",
         "iri-columns",
         [F(options=O(prefix=8), vars=[("v", 0)], rows=4,
            prefixes=[N("https://a.org/", "https://b.org/")], names=[N("x1", "x2", "z")],
            iri=[iri_col([0, 0, 1, 3], [], [1, 0, 0, 2])], trailer="")],
         RS(["v"], row(v=Iri("https://a.org/x1")), row(v=Iri("https://a.org/x2")),
            row(v=Iri("https://a.org/x1")), row(v=Iri("https://b.org/z"))))
from_pos(C, "prefix_ids with a single entry: every value uses that prefix.",
         "iri-columns",
         [F(options=O(prefix=8), vars=[("v", 0)], rows=3,
            prefixes=[N("https://a.org/", "https://b.org/")], names=[N("x", "y", "z")],
            iri=[iri_col([0, 0, 0], [], [2])], trailer="")],
         RS(["v"], row(v=Iri("https://b.org/x")), row(v=Iri("https://b.org/y")),
            row(v=Iri("https://b.org/z"))))
from_pos(C, "Empty prefix_ids with the prefix lookup enabled: no value has a prefix, the names hold whole IRIs.",
         "iri-columns",
         [F(options=O(prefix=8), vars=[("v", 0)], rows=2,
            names=[N(E + "a", E + "b")], iri=[iri_col([0, 0], [], [])], trailer="")],
         RS(["v"], row(v=I("a")), row(v=I("b"))))
from_pos(C, "prefix_ids with one entry per value, starting with 0: the prefix inference state starts from \"no prefix\".",
         "iri-columns",
         [F(options=O(prefix=8), vars=[("v", 0)], rows=3,
            prefixes=[N(E)], names=[N(E + "full", "a", "b")],
            iri=[iri_col([0, 0, 0], [], [0, 1, 0])], trailer="")],
         RS(["v"], row(v=I("full")), row(v=I("a")), row(v=I("b"))))
from_pos(C, "name_ids mixing explicit identifiers and 0 (previous + 1): [5, 0, 0, 2, 0] is 5, 6, 7, 2, 3.",
         "iri-columns",
         [F(options=O(), vars=[("v", 0)], rows=5,
            names=[N(*[E + f"n{i}" for i in range(1, 8)])],
            iri=[iri_col([5, 0, 0, 2, 0])], trailer="")],
         RS(["v"], *[row(v=I(f"n{i}")) for i in (5, 6, 7, 2, 3)]))
from_pos(C, "The name_id and prefix_id inference state resets at the start of every column.",
         "iri-columns",
         [F(options=O(prefix=8), vars=[("x", 0), ("y", 1)], rows=2,
            prefixes=[N(E, "https://b.org/")], names=[N("a", "b")],
            iri=[iri_col([0, 0], [], [2, 0]), iri_col([0, 0], [], [0, 1])], trailer="")],
         RS(["x", "y"], row(x=Iri("https://b.org/a"), y=Iri("a")),
            row(x=Iri("https://b.org/b"), y=I("b"))),
         comment="In the second column, the first prefix_id of 0 means no prefix, not the prefix of the previous column.")
from_pos(C, "The name_id inference state resets at the start of every frame.",
         "iri-columns",
         [F(options=O(prefix=8), vars=[("v", 0)], rows=3, prefixes=[N(E)], names=[N("a", "b", "c")],
            iri=[iri_col([0, 0, 0], [], [1])]),
          F(rows=1, iri=[iri_col([0], [], [1])], trailer="")],
         rs_v(IRI_ABC, "abca"))
from_pos(C, "An empty name: the IRI is equal to its prefix.",
         "iri-columns",
         [F(options=O(prefix=8), vars=[("v", 0)], rows=2, prefixes=[N(E)], names=[N("", "a")],
            iri=[iri_col([0, 0], [], [1])], trailer="")],
         RS(["v"], row(v=Iri(E)), row(v=I("a"))))

# --- lookup entries --------------------------------------------------------------------

from_pos(C, "Lookup identifiers continue across frames: an entry with id 0 in the second frame takes the next identifier.",
         "packed-lookup-entries",
         [F(options=O(prefix=8), vars=[("v", 0)], rows=3, prefixes=[N(E)], names=[N("a", "b", "c")],
            iri=[iri_col([0, 0, 0], [], [1])]),
          F(rows=1, names=[N("d")], iri=[iri_col([4], [], [1])], trailer="")],
         rs_v(IRI_ABC, "abcd"))
from_pos(C, "Packed entries with explicit identifiers: id 10 with two values, then id 0 continuing at 12.",
         "packed-lookup-entries",
         [F(options=O(), vars=[("v", 0)], rows=3,
            names=[N(E + "x", E + "y", id=10), N(E + "z")],
            iri=[iri_col([10, 0, 0])], trailer="")],
         RS(["v"], row(v=I("x")), row(v=I("y")), row(v=I("z"))))
from_pos(C, "An entry overwritten in a later frame: the later frame sees the new value.",
         "prefix-name-and-datatype-lookup-entries",
         [F(options=O(prefix=8), vars=[("v", 0)], rows=1, prefixes=[N(E)], names=[N("a")],
            iri=[iri_col([1], [], [1])]),
          F(rows=1, names=[N("b", id=1)], iri=[iri_col([1], [], [1])], trailer="")],
         rs_v(IRI_ABC, "ab"))
from_pos(C, "All lookup entries of a frame are applied before its columns: a name overwritten twice in one frame decodes to the last value.",
         "the-working-set-of-a-frame",
         [F(options=O(prefix=8), vars=[("v", 0)], rows=1, prefixes=[N(E)],
            names=[N("a", id=1), N("b", id=1)], iri=[iri_col([1], [], [1])], trailer="")],
         rs_v(IRI_ABC, "b"),
         comment="A producer must not write such a frame if it means the first value (the working set rule), but a consumer has to decode it this way.")
from_pos(C, "A name lookup entry at the largest identifier the table allows.",
         "stream-options",
         [F(options=O(name=128), vars=[("v", 0)], rows=1, names=[N(E + "last", id=128)],
            iri=[iri_col([128])], trailer="")],
         RS(["v"], row(v=I("last"))))
from_pos(C, "Lookup table sizes at the recommended default consumer limits: 16384 names, 4096 prefixes, 256 datatypes.",
         "stream-options",
         [F(options=O(name=16384, prefix=4096, datatype=256), vars=[("v", 0)], rows=1,
            prefixes=[N(E, id=4096)], names=[N("a", id=16384)], datatypes=[N(XSD + "int", id=256)],
            iri=[iri_col([16384], [], [4096])]),
          F(vars=[("v", 0)], rows=1, literal=[lit_col(lex=["7"], datatype=256)], trailer="")],
         RS(["v"], row(v=I("a")), row(v=L("7", "int"))))

# --- header and columns ----------------------------------------------------------------

from_pos(C, "Column order is not projection order: the variables are returned in header order, whatever their column indices.",
         "column-indices",
         [F(options=O(prefix=8), vars=[("label", 1), ("item", 0)], rows=1, prefixes=[N(E)],
            names=[N("a")], iri=[iri_col([1], [], [1])], literal=[lit_col(lex=["A"])], trailer="")],
         RS(["label", "item"], row(label=L("A"), item=I("a"))))
from_pos(C, "All four column types in one frame. Column indices follow the virtual concatenation iri, bnode, literal, poly.",
         "column-indices",
         [F(options=O(prefix=8), vars=[("p", 3), ("l", 2), ("b", 1), ("i", 0)], rows=2,
            prefixes=[N(E)], names=[N("a", "b")],
            iri=[iri_col([0, 0], [], [1])], bnode=[bnode_col(["x", "y"])],
            literal=[lit_col(lex=["1", "2"])], poly=[poly_col([t_bnode("z"), t_lit("w")])],
            trailer="")],
         RS(["p", "l", "b", "i"],
            row(p=B("z"), l=L("1"), b=B("x"), i=I("a")),
            row(p=L("w"), l=L("2"), b=B("y"), i=I("b"))))
from_pos(C, "Variables unbound in every row, each encoded as an empty column message of a different type.",
         "columns",
         [F(options=O(prefix=8), vars=[("v", 4), ("i", 0), ("b", 1), ("l", 2), ("p", 3)], rows=2,
            prefixes=[N(E)], names=[N("a")],
            iri=[iri_col()], bnode=[bnode_col()], literal=[lit_col()],
            poly=[poly_col(), poly_col([t_iri(1, 1)], rep(0, 2))], trailer="")],
         RS(["v", "i", "b", "l", "p"], row(v=I("a")), row(v=I("a"))))
from_pos(C, "Header restated to move a variable from an IRI column to a polymorphic column. A later frame without a header keeps the restated layout.",
         "restating-the-header",
         [F(options=O(prefix=8), vars=[("s", 0), ("o", 1)], rows=1, prefixes=[N(E)], names=[N("a", "b")],
            iri=[iri_col([1], [], [1]), iri_col([2], [], [1])]),
          F(vars=[("s", 0), ("o", 1)], rows=1,
            iri=[iri_col([1], [], [1])], poly=[poly_col([t_lit("x")])]),
          F(rows=2, iri=[iri_col([1], rep(0, 2), [1])], poly=[poly_col([t_iri(1, 2), t_lit("y")])],
            trailer="")],
         RS(["s", "o"], row(s=I("a"), o=I("b")), row(s=I("a"), o=L("x")),
            row(s=I("a"), o=I("b")), row(s=I("a"), o=L("y"))))
from_pos(C, "Header restated with only the column indices changed (the columns of the same type swap places).",
         "restating-the-header",
         [F(options=O(), vars=[("x", 0), ("y", 1)], rows=1, literal=[lit_col(lex=["x1"]), lit_col(lex=["y1"])]),
          F(vars=[("x", 1), ("y", 0)], rows=1, literal=[lit_col(lex=["y2"]), lit_col(lex=["x2"])], trailer="")],
         RS(["x", "y"], row(x=L("x1"), y=L("y1")), row(x=L("x2"), y=L("y2"))))
from_pos(C, "Header restated identically to the one in effect (allowed, producers should not do it).",
         "restating-the-header",
         [F(options=O(), vars=[("x", 0)], rows=1, literal=[lit_col(lex=["1"])]),
          F(vars=[("x", 0)], rows=1, literal=[lit_col(lex=["2"])], trailer="")],
         RS(["x"], row(x=L("1")), row(x=L("2"))))
from_pos(C, "A variable with an empty name (allowed, not recommended).",
         "result-set-header",
         [F(options=O(), vars=[("", 0), ("x", 1)], rows=1, literal=[lit_col(lex=["a"]), lit_col(lex=["b"])], trailer="")],
         RS(["", "x"], {"": L("a"), "x": L("b")}))

# --- frames with no rows ------------------------------------------------------------

from_pos(C, "A frame with no rows and no columns in the middle of a stream, carrying only lookup entries for the next frame.",
         "frames-with-no-rows",
         [F(options=O(prefix=8), vars=[("x", 0), ("y", 1)], rows=1, prefixes=[N(E)], names=[N("a")],
            iri=[iri_col([1], [], [1]), iri_col([1], [], [1])]),
          F(names=[N("b")]),
          F(rows=1, iri=[iri_col([2], [], [1]), iri_col([1], [], [1])], trailer="")],
         RS(["x", "y"], row(x=I("a"), y=I("a")), row(x=I("b"), y=I("a"))))
from_pos(C, "A frame with no rows that carries one empty column per variable (allowed, producers should omit the columns).",
         "frames-with-no-rows",
         [F(options=O(), vars=[("x", 0), ("y", 1)], rows=1, literal=[lit_col(lex=["1"]), lit_col(lex=["2"])]),
          F(literal=[lit_col(), lit_col()]),
          F(rows=1, literal=[lit_col(lex=["3"]), lit_col(lex=["4"])], trailer="")],
         RS(["x", "y"], row(x=L("1"), y=L("2")), row(x=L("3"), y=L("4"))))
from_pos(C, "An empty result set whose first frame carries one empty column per variable.",
         "frames-with-no-rows",
         [F(options=O(), vars=[("x", 0), ("y", 1)], iri=[iri_col(), iri_col()], trailer="")],
         RS(["x", "y"]))

# --- zero-variable result sets -------------------------------------------------------

from_pos(C, "A zero-variable result set with one empty solution (e.g., SELECT * WHERE {}).",
         "zero-variable-result-sets",
         [F(options=O(), rows=1, trailer="")],
         RS([], {}))
from_pos(C, "A zero-variable result set with three empty solutions over two frames.",
         "zero-variable-result-sets",
         [F(options=O(), rows=2), F(rows=1, trailer="")],
         RS([], {}, {}, {}))
from_pos(C, "A zero-variable result set with no solutions.",
         "zero-variable-result-sets",
         [F(options=O(), trailer="")],
         RS([]))
from_pos(C, "Two zero-variable streams concatenated: the repeated options come with an empty header, which declares zero variables again.",
         "repeating-the-stream-options",
         [F(options=O(), rows=1, trailer=""), F(options=O(), rows=2, trailer="")],
         RS([], {}, {}, {}))

# --- literal columns -------------------------------------------------------------------

from_pos(C, "Literal column, lexical form, simple literals (datatype 0).",
         "literal-columns",
         [F(options=O(), vars=[("v", 0)], rows=2, literal=[lit_col(lex=["x", "y"])], trailer="")],
         RS(["v"], row(v=L("x")), row(v=L("y"))))
from_pos(C, "xsd:string literals encoded three ways: lexical form with datatype 0, lexical form with an xsd:string datatype entry, and full form with an xsd:string datatype entry. All are the same simple literal.",
         "literal-columns",
         [F(options=O(datatype=4), vars=[("v", 0)], rows=1, datatypes=[N(XSD_STRING)],
            literal=[lit_col(lex=["a"])]),
          F(rows=1, literal=[lit_col(lex=["b"], datatype=1)]),
          F(rows=1, literal=[lit_col(values=[lit("c", datatype=1)])], trailer="")],
         RS(["v"], row(v=L("a")), row(v=L("b")), row(v=L("c"))))
from_pos(C, "Literal column, lexical form, typed literals (xsd:integer, then xsd:dateTime).",
         "literal-columns",
         [F(options=O(datatype=4), vars=[("v", 0)], rows=2, datatypes=[N(XSD + "integer", XSD + "dateTime")],
            literal=[lit_col(lex=["1", "-20"], datatype=1)]),
          F(rows=1, literal=[lit_col(lex=["2024-01-01T00:00:00Z"], datatype=2)], trailer="")],
         RS(["v"], row(v=L("1", "integer")), row(v=L("-20", "integer")),
            row(v=L("2024-01-01T00:00:00Z", "dateTime"))))
from_pos(C, "Literal column, lexical form, one language tag for the whole column.",
         "literal-columns",
         [F(options=O(), vars=[("v", 0)], rows=3, literal=[lit_col(lex=["cat", "dog", "cat"], langtag="en")], trailer="")],
         RS(["v"], row(v=L("cat", lang="en")), row(v=L("dog", lang="en")), row(v=L("cat", lang="en"))))
from_pos(C, "Literal column, full form, mixing simple, typed, and language-tagged literals with different tags.",
         "literal-columns",
         [F(options=O(datatype=4), vars=[("v", 0)], rows=4, datatypes=[N(XSD + "integer")],
            literal=[lit_col(values=[lit("a"), lit("1", datatype=1), lit("b", langtag="en"),
                                     lit("c", langtag="de")])], trailer="")],
         RS(["v"], row(v=L("a")), row(v=L("1", "integer")), row(v=L("b", lang="en")),
            row(v=L("c", lang="de"))))
from_pos(C, "Empty lexical forms, in the lexical form and in the full form.",
         "literal-columns",
         [F(options=O(), vars=[("x", 0), ("y", 1)], rows=2,
            literal=[lit_col(lex=["", ""], langtag="en"), lit_col(values=[lit(""), lit("", langtag="fr")])],
            trailer="")],
         RS(["x", "y"], row(x=L("", lang="en"), y=L("")), row(x=L("", lang="en"), y=L("", lang="fr"))))

# --- polymorphic columns and blank nodes ----------------------------------------------

from_pos(C, "Polymorphic column: the IRI inference state is shared by the IRIs of the column and skips other values.",
         "polymorphic-columns",
         [F(options=O(prefix=8), vars=[("v", 0)], rows=6, prefixes=[N(E)], names=[N("a", "b", "c", "d", "e", "f")],
            poly=[poly_col([t_iri(1, None), t_bnode("x"), t_lit("l"), t_iri(), t_iri(None, 5), t_iri()])],
            trailer="")],
         RS(["v"], row(v=I("a")), row(v=B("x")), row(v=L("l")), row(v=I("b")), row(v=I("e")), row(v=I("f"))),
         comment="Values: iri(prefix 1, name 0 -> 1), bnode, literal, iri(0, 0 -> 2), iri(0, 5), iri(0, 0 -> 6).")
from_pos(C, "Polymorphic column: the IRI inference state resets at the start of every frame.",
         "polymorphic-columns",
         [F(options=O(prefix=8), vars=[("v", 0)], rows=2, prefixes=[N(E)], names=[N("a", "b")],
            poly=[poly_col([t_iri(1, None), t_lit("x")])]),
          F(rows=2, poly=[poly_col([t_iri(1, None), t_iri()])], trailer="")],
         RS(["v"], row(v=I("a")), row(v=L("x")), row(v=I("a")), row(v=I("b"))))
from_pos(C, "Blank node labels are scoped to the whole stream: the same label in different frames and in different column types is the same blank node.",
         "blank-node-columns",
         [F(options=O(), vars=[("x", 0), ("y", 1)], rows=2,
            bnode=[bnode_col(["n1", "n2"])], poly=[poly_col([t_bnode("n2"), t_lit("z")])]),
          F(rows=1, bnode=[bnode_col(["n2"])], poly=[poly_col([t_bnode("n1")])], trailer="")],
         RS(["x", "y"], row(x=B("n1"), y=B("n2")), row(x=B("n2"), y=L("z")), row(x=B("n2"), y=B("n1"))))

# --- metadata, options, trailer --------------------------------------------------------

from_pos(C, "The well-known link metadata key with two IRIs, mapped to head.link.",
         "well-known-metadata-keys",
         [F(options=O(), vars=[("v", 0)], rows=1, literal=[lit_col(lex=["x"])],
            metadata={"link": f"{E}doc1\n{E}doc2".encode()}, trailer="")],
         RS(["v"], row(v=L("x")), links=[E + "doc1", E + "doc2"]),
         comment="The equivalence of result sets does not cover links. Implementations that expose links should check them against head.link.")
from_pos(C, "Metadata with an implementation-defined key whose value is not valid UTF-8. It must be ignored.",
         "frame-metadata",
         [F(options=O(), vars=[("v", 0)], rows=1, literal=[lit_col(lex=["x"])],
            metadata={"com.example.binary": b"\xff\xfe\x00\x80"}, trailer="")],
         RS(["v"], row(v=L("x"))))
from_pos(C, "The link metadata key with a value that is not valid UTF-8. Consumers should ignore it.",
         "well-known-metadata-keys",
         [F(options=O(), vars=[("v", 0)], rows=1, literal=[lit_col(lex=["x"])],
            metadata={"link": b"http://example.org/\xff"}, trailer="")],
         RS(["v"], row(v=L("x"))), should=True)
from_pos(C, "Stream options with a stream name.",
         "stream-options",
         [F(options=O(stream_name="results/query-1"), vars=[("v", 0)], rows=1, literal=[lit_col(lex=["x"])], trailer="")],
         RS(["v"], row(v=L("x"))))
from_pos(C, "A trailer-only final frame (row_count 0, no columns, only the trailer).",
         "stream-trailer",
         [F(options=O(), vars=[("v", 0)], rows=2, literal=[lit_col(lex=["x", "y"])]), F(trailer="")],
         RS(["v"], row(v=L("x")), row(v=L("y"))))
from_pos(C, "A stream without a trailer. The result set is valid; consumers should report that it may be truncated.",
         "stream-trailer",
         [F(options=O(), vars=[("v", 0)], rows=2, literal=[lit_col(lex=["x", "y"])])],
         RS(["v"], row(v=L("x")), row(v=L("y"))),
         comment="Consumers may warn or report the missing trailer, but must not fail this test.")

# --- repeating the stream options (concatenation) --------------------------------------

from_pos(C, "Two streams of the same query concatenated. The second segment repeats the options (with other table sizes) and the header, and its lookup identifiers restart from 1.",
         "repeating-the-stream-options",
         [F(options=O(prefix=8), vars=[("s", 0), ("o", 1)], rows=1, prefixes=[N(E)], names=[N("a", "b")],
            iri=[iri_col([0], [], [1])], bnode=[bnode_col(["x"])]),
          F(rows=1, iri=[iri_col([2], [], [1])], bnode=[bnode_col(["y"])], trailer=""),
          F(options=O(name=256, prefix=4), vars=[("s", 0), ("o", 1)], rows=1,
            prefixes=[N("https://b.org/")], names=[N("c")],
            iri=[iri_col([0], [], [1])], bnode=[bnode_col(["x"])], trailer="")],
         RS(["s", "o"], row(s=I("a"), o=B("x")), row(s=I("b"), o=B("y")),
            row(s=Iri("https://b.org/c"), o=B("x"))),
         comment="Blank node labels are not reset by the repeated options: the label x in both segments is one blank node.")
from_pos(C, "Concatenated streams with different column layouts: the restated header maps the same variables to other column types.",
         "repeating-the-stream-options",
         [F(options=O(), vars=[("a", 0), ("b", 1)], rows=1, literal=[lit_col(lex=["1"]), lit_col(lex=["2"])], trailer=""),
          F(options=O(), vars=[("a", 1), ("b", 0)], rows=1, bnode=[bnode_col(["x"])],
            poly=[poly_col([t_lit("3")])], trailer="")],
         RS(["a", "b"], row(a=L("1"), b=L("2")), row(a=L("3"), b=B("x"))))
from_pos(C, "Options repeated without a trailer before them (a producer that did not write trailers).",
         "repeating-the-stream-options",
         [F(options=O(), vars=[("a", 0)], rows=1, literal=[lit_col(lex=["1"])]),
          F(options=O(), vars=[("a", 0)], rows=1, literal=[lit_col(lex=["2"])], trailer="")],
         RS(["a"], row(a=L("1")), row(a=L("2"))))

# --- negative ---------------------------------------------------------------------------

ONE = dict(vars=[("v", 0)], rows=1, literal=[lit_col(lex=["x"])], trailer="")

from_neg(C, "An empty file: a result stream must contain at least one frame.",
         "result-frames", [], "no frames")
from_neg(C, "The last frame is truncated: the length prefix promises more bytes than the file has.",
         "framing", [], "truncated",
         raw=pb.varint(50) + F(options=O(), **ONE).encode())
from_neg(C, "Version tag 0.", "stream-options", [F(options=O(version=0), **ONE)], "version tag is 0",
         should=True)
from_neg(C, "Version tag 2, newer than version 1 of the format.", "stream-options",
         [F(options=O(version=2), **ONE)], "newer than supported", should=True)
from_neg(C, "max_name_table_size 127, below the minimum of 128.", "stream-options",
         [F(options=O(name=127), **ONE)], "below the minimum")
from_neg(C, "max_name_table_size not set (0).", "stream-options",
         [F(options=O(name=None), **ONE)], "below the minimum")
from_neg(C, "max_name_table_size 10000000. Consumers must limit the lookup sizes they accept (recommended default 16384).",
         "overly-large-lookup-tables", [F(options=O(name=10_000_000), **ONE)], "larger than the consumer accepts",
         should=True)
from_neg(C, "max_prefix_table_size 10000000. Consumers must limit the lookup sizes they accept (recommended default 4096).",
         "overly-large-lookup-tables", [F(options=O(prefix=10_000_000), **ONE)], "larger than the consumer accepts",
         should=True)
from_neg(C, "max_datatype_table_size 10000000. Consumers must limit the lookup sizes they accept (recommended default 256).",
         "overly-large-lookup-tables", [F(options=O(datatype=10_000_000), **ONE)], "larger than the consumer accepts",
         should=True)
from_neg(C, "Unknown rdf_version value 4.", "rdf-version",
         [F(options=O(rdf_version=4), **ONE)], "unknown rdf_version")
from_neg(C, "A prefix lookup entry when the prefix lookup is disabled (max_prefix_table_size 0).",
         "stream-options", [F(options=O(), prefixes=[N(E)], **ONE)], "prefix lookup is disabled")
from_neg(C, "A datatype lookup entry when the datatype lookup is disabled (max_datatype_table_size 0).",
         "stream-options", [F(options=O(), datatypes=[N(XSD + "int")], **ONE)], "datatype lookup is disabled")
from_neg(C, "A name lookup entry with an identifier larger than the table size.",
         "stream-options", [F(options=O(), names=[N("a", id=129)], **ONE)], "outside of the table")
from_neg(C, "A packed name entry whose last value falls outside the table (ids 127, 128, 129 in a table of 128).",
         "packed-lookup-entries", [F(options=O(), names=[N("a", "b", "c", id=127)], **ONE)], "outside of the table")
from_neg(C, "A prefix lookup entry with an identifier larger than the table size.",
         "stream-options", [F(options=O(prefix=8), prefixes=[N(E, id=9)], **ONE)], "outside of the table")
from_neg(C, "An IRI column refers to a prefix identifier outside the prefix table.",
         "iri-columns",
         ex_frame_1var(iri_col([1], [], [9]), 1), "prefix id 9 outside")
from_neg(C, "An IRI column refers to a name that was never defined (name_id 0 at the start of a column means 1, and the name table is empty).",
         "iri-columns",
         [F(options=O(), vars=[("v", 0)], rows=1, iri=[iri_col([0])], trailer="")], "empty lookup entry")
from_neg(C, "An IRI column refers to a name identifier outside the name table.",
         "iri-columns",
         [F(options=O(), vars=[("v", 0)], rows=1, names=[N(E + "a")], iri=[iri_col([200])], trailer="")],
         "name id 200 outside")
from_neg(C, "An IRI column uses prefix_ids while the prefix lookup is disabled.",
         "stream-options",
         [F(options=O(), vars=[("v", 0)], rows=1, names=[N("a")], iri=[iri_col([1], [], [1])], trailer="")],
         "prefix id 1 outside")
from_neg(C, "prefix_ids with 2 entries for 3 values. The length must be 0, 1, or the number of values.",
         "iri-columns",
         ex_frame_1var(iri_col([0, 0, 0], [], [1, 1]), 3), "prefix_ids has 2 entries")
from_neg(C, "A literal column refers to a datatype identifier outside the datatype table.",
         "literal-columns",
         [F(options=O(datatype=8), vars=[("v", 0)], rows=1, literal=[lit_col(lex=["1"], datatype=9)], trailer="")],
         "datatype id 9 outside")
from_neg(C, "A literal column refers to a datatype while the datatype lookup is disabled.",
         "stream-options",
         [F(options=O(), vars=[("v", 0)], rows=1, literal=[lit_col(lex=["1"], datatype=1)], trailer="")],
         "datatype id 1 outside")
from_neg(C, "A literal in the full form with datatype 0, which is invalid (unlike in the lexical form).",
         "literal-columns",
         [F(options=O(datatype=8), vars=[("v", 0)], rows=1, datatypes=[N(XSD + "int")],
            literal=[lit_col(values=[lit("1", datatype=0)])], trailer="")],
         "datatype 0")
from_neg(C, "A literal column in the lexical form whose datatype is rdf:langString.",
         "literal-columns",
         [F(options=O(datatype=8), vars=[("v", 0)], rows=1, datatypes=[N(RDF_LANG_STRING)],
            literal=[lit_col(lex=["x"], datatype=1)], trailer="")],
         "needs a language tag", should=True)
from_neg(C, "A literal in the full form whose datatype is rdf:langString.",
         "base-direction",
         [F(options=O(datatype=8), vars=[("v", 0)], rows=1, datatypes=[N(RDF_LANG_STRING)],
            literal=[lit_col(values=[lit("x", datatype=1)])], trailer="")],
         "needs a language tag", should=True)
from_neg(C, "A literal column with both values and lex_values set.",
         "literal-columns",
         [F(options=O(), vars=[("v", 0)], rows=2, literal=[lit_col(values=[lit("a")], lex=["b"])], trailer="")],
         "both values and lex_values")
from_neg(C, "A literal column in the full form (lex_values empty) that sets datatype.",
         "literal-columns",
         [F(options=O(datatype=8), vars=[("v", 0)], rows=1, datatypes=[N(XSD + "int")],
            literal=[lit_col(values=[lit("a")], datatype=1)], trailer="")],
         "sets datatype, but lex_values is empty")
from_neg(C, "A literal column in the full form (lex_values empty) that sets langtag.",
         "literal-columns",
         [F(options=O(), vars=[("v", 0)], rows=1, literal=[lit_col(values=[lit("a")], langtag="en")], trailer="")],
         "sets langtag, but lex_values is empty")
from_neg(C, "A literal column in the lexical form that sets both datatype and langtag.",
         "literal-columns",
         [F(options=O(datatype=8), vars=[("v", 0)], rows=1, datatypes=[N(XSD + "int")],
            literal=[lit_col(lex=["a"], datatype=1, langtag="en")], trailer="")],
         "both datatype and langtag")
from_neg(C, "A term in a polymorphic column with no field of the oneof set.",
         "polymorphic-columns",
         [F(options=O(), vars=[("v", 0)], rows=2, poly=[poly_col([t_lit("a"), t_empty()])], trailer="")],
         "no value set")
from_neg(C, "row_count of 2^27, larger than the maximum of 2^27 - 1.",
         "result-frames",
         [F(options=O(), rows=1 << 27, trailer="")], "larger than 2^27 - 1",
         comment="The stream has zero variables, so the frame needs no columns and the row count is the only problem.")
from_neg(C, "A frame with more columns than the header declares variables.",
         "column-indices",
         [F(options=O(), vars=[("v", 0)], rows=1, literal=[lit_col(lex=["x"]), lit_col(lex=["y"])], trailer="")],
         "has 2 columns")
from_neg(C, "A frame with fewer columns than the header declares variables (but not zero).",
         "column-indices",
         [F(options=O(), vars=[("x", 0), ("y", 1)], rows=1, literal=[lit_col(lex=["x"])], trailer="")],
         "has 1 columns")
from_neg(C, "A frame with rows but no columns, in a stream with variables.",
         "column-indices",
         [F(options=O(), vars=[("x", 0)], rows=1, literal=[lit_col(lex=["x"])]), F(rows=2, trailer="")],
         "rows but no columns")
from_neg(C, "A zero-variable result set with a column.",
         "zero-variable-result-sets",
         [F(options=O(), rows=1, literal=[lit_col(lex=["x"])], trailer="")], "has 1 columns")
from_neg(C, "Two variables mapped to the same column index.",
         "column-indices",
         [F(options=O(), vars=[("x", 0), ("y", 0)], rows=1, literal=[lit_col(lex=["a"]), lit_col(lex=["b"])], trailer="")],
         "not a permutation")
from_neg(C, "A column index outside the columns of the frame.",
         "column-indices",
         [F(options=O(), vars=[("x", 0), ("y", 2)], rows=1, literal=[lit_col(lex=["a"]), lit_col(lex=["b"])], trailer="")],
         "not a permutation")
from_neg(C, "A restated header with a different variable name.",
         "restating-the-header",
         [F(options=O(), vars=[("x", 0)], rows=1, literal=[lit_col(lex=["a"])]),
          F(vars=[("z", 0)], rows=1, literal=[lit_col(lex=["b"])], trailer="")],
         "different variables")
from_neg(C, "A restated header with the variables in a different order.",
         "restating-the-header",
         [F(options=O(), vars=[("x", 0), ("y", 1)], rows=1, literal=[lit_col(lex=["a"]), lit_col(lex=["b"])]),
          F(vars=[("y", 0), ("x", 1)], rows=1, literal=[lit_col(lex=["c"]), lit_col(lex=["d"])], trailer="")],
         "different variables")
from_neg(C, "A restated header with fewer variables.",
         "restating-the-header",
         [F(options=O(), vars=[("x", 0), ("y", 1)], rows=1, literal=[lit_col(lex=["a"]), lit_col(lex=["b"])]),
          F(vars=[("x", 0)], rows=1, literal=[lit_col(lex=["c"])], trailer="")],
         "different variables")
from_neg(C, "The stream options are repeated, but the frame does not restate the header. An empty header next to the options declares zero variables, which does not match the first header.",
         "repeating-the-stream-options",
         [F(options=O(), vars=[("x", 0)], rows=1, literal=[lit_col(lex=["a"])], trailer=""),
          F(options=O(), rows=1, literal=[lit_col(lex=["b"])], trailer="")],
         "does not declare the variables")
from_neg(C, "The stream options are repeated with a header declaring other variables than the first header.",
         "repeating-the-stream-options",
         [F(options=O(), vars=[("x", 0)], rows=1, literal=[lit_col(lex=["a"])], trailer=""),
          F(options=O(), vars=[("y", 0)], rows=1, literal=[lit_col(lex=["b"])], trailer="")],
         "does not declare the variables")
from_neg(C, "The repeated stream options are not valid on their own (max_name_table_size 10).",
         "repeating-the-stream-options",
         [F(options=O(), vars=[("x", 0)], rows=1, literal=[lit_col(lex=["a"])], trailer=""),
          F(options=O(name=10), vars=[("x", 0)], rows=1, literal=[lit_col(lex=["b"])], trailer="")],
         "below the minimum")
from_neg(C, "After the options are repeated, a column refers to a name defined only before the reset. The lookups are emptied by the reset.",
         "repeating-the-stream-options",
         [F(options=O(prefix=8), vars=[("x", 0)], rows=1, prefixes=[N(E)], names=[N("a")],
            iri=[iri_col([1], [], [1])], trailer=""),
          F(options=O(prefix=8), vars=[("x", 0)], rows=1, iri=[iri_col([1], [], [1])], trailer="")],
         "empty lookup entry")
from_neg(C, "Corrupt layout: skip runs past the last run value.",
         "sequence-layout", ex_frame_1var(iri_col([0, 0], unb(3, 1), [1]), 4), "skip runs past")
from_neg(C, "Corrupt layout: a repeat run starts after the last run value.",
         "sequence-layout", ex_frame_1var(iri_col([0, 0], rep(2, 2), [1]), 4), "repeat run starts past")
from_neg(C, "Corrupt layout: len_code 15 is the last token, with no extension varint after it.",
         "sequence-layout", ex_frame_1var(iri_col([0, 0], [15], [1]), 20), "without an extension varint")
from_neg(C, "Corrupt layout: a repeat run makes the column longer than row_count.",
         "sequence-layout", ex_frame_1var(iri_col([0, 0], rep(0, 4), [1]), 4), "more than row_count")
from_neg(C, "Corrupt layout: an unbound run makes the column longer than row_count.",
         "sequence-layout", ex_frame_1var(iri_col([0, 0], unb(1, 3), [1]), 4), "more than row_count")
from_neg(C, "A column with more run values than row_count, and no layouts.",
         "sequence-layout", ex_frame_1var(iri_col([0, 0, 0], [], [1]), 2), "more than row_count")
from_neg(C, "Corrupt layout: an extension varint of 2^32 - 1 (a run far longer than the frame).",
         "column-layouts", ex_frame_1var(iri_col([0], [15, 0xFFFFFFFF], [1]), 4), "more than row_count",
         comment="Consumers must check the run length against row_count before writing any cells.")
from_neg(C, "A trailer with an error. The rows before it are valid, but the result set is incomplete and the consumer must report it.",
         "stream-trailer",
         [F(options=O(), vars=[("v", 0)], rows=2, literal=[lit_col(lex=["x", "y"])]),
          F(trailer="Query timed out after 30 seconds")],
         "error trailer",
         comment="Implementations may deliver the two rows before the error, but must signal the error to the caller.")
from_neg(C, "A frame without the stream options after a frame with a trailer.",
         "stream-trailer",
         [F(options=O(), vars=[("v", 0)], rows=1, literal=[lit_col(lex=["x"])], trailer=""),
          F(rows=1, literal=[lit_col(lex=["y"])])],
         "follows a trailer")
from_neg(C, "A boolean result in the second frame of a stream of solutions.",
         "boolean-results",
         [F(options=O(), vars=[("v", 0)], rows=1, literal=[lit_col(lex=["x"])]), F(ask=True, trailer="")],
         "other than the first")


# =============================================================================
# From Jelly – ASK
# =============================================================================

C = ASK

from_pos(C, "Boolean result true.", "boolean-results", [F(options=O(), ask=True, trailer="")], AskResult(True))
from_pos(C, "Boolean result false (an empty SparqlAskResult message: value defaults to false).",
         "boolean-results", [F(options=O(), ask=False, trailer="")], AskResult(False))
from_pos(C, "Boolean result with metadata and a trailer in the same frame (neither is result content).",
         "boolean-results",
         [F(options=O(), ask=True, metadata={"com.example.info": b"\x01\x02"}, trailer="")], AskResult(True))
from_pos(C, "Boolean result without a trailer.", "boolean-results", [F(options=O(), ask=True)], AskResult(True))

from_neg(C, "A boolean result frame that declares a variable.", "boolean-results",
         [F(options=O(), vars=[("v", 0)], ask=True, trailer="")], "declares variables", should=True)
from_neg(C, "A boolean result frame that contains a column.", "boolean-results",
         [F(options=O(), ask=True, literal=[lit_col()], trailer="")], "contains columns", should=True)
from_neg(C, "A boolean result frame with row_count 1.", "boolean-results",
         [F(options=O(), rows=1, ask=True, trailer="")], "row_count != 0", should=True)
from_neg(C, "A frame follows the boolean result.", "boolean-results",
         [F(options=O(), ask=True), F(trailer="")], "follows the frame carrying the boolean result", should=True)
from_neg(C, "A second boolean result stream concatenated after the first. Boolean results cannot be concatenated.",
         "boolean-results",
         [F(options=O(), ask=True, trailer=""), F(options=O(), ask=True, trailer="")],
         "follows the frame carrying the boolean result", should=True)
from_neg(C, "A boolean result with an error trailer.", "stream-trailer",
         [F(options=O(), ask=True, trailer="Service unavailable")], "error trailer")


# =============================================================================
# From Jelly – RDF 1.2 Basic (base direction)
# =============================================================================

C = SELECT_1_2_BASIC
V12B = msgs.RDF_VERSION_1_2_BASIC

from_pos(C, "Full-form literal column with directional language-tagged strings (ltr and rtl) next to a language-tagged string without a direction.",
         "base-direction",
         [F(options=O(rdf_version=V12B), vars=[("v", 0)], rows=3,
            literal=[lit_col(values=[lit("hello", "en", direction=msgs.DIR_LTR),
                                     lit("مرحبا", "ar", direction=msgs.DIR_RTL), lit("hello", "en")])],
            trailer="")],
         RS(["v"], row(v=L("hello", lang="en", d="ltr")), row(v=L("مرحبا", lang="ar", d="rtl")),
            row(v=L("hello", lang="en"))))
from_pos(C, "Lexical-form literal column with a shared language tag and base direction.",
         "literal-columns",
         [F(options=O(rdf_version=V12B), vars=[("v", 0)], rows=2,
            literal=[lit_col(lex=["שלום", "עולם"], langtag="he", direction=msgs.DIR_RTL)], trailer="")],
         RS(["v"], row(v=L("שלום", lang="he", d="rtl")), row(v=L("עולם", lang="he", d="rtl"))))
from_pos(C, "Directional literals in a stream that declares no RDF version (allowed: no version is announced).",
         "rdf-version",
         [F(options=O(), vars=[("v", 0)], rows=1,
            literal=[lit_col(lex=["x"], langtag="en", direction=msgs.DIR_LTR)], trailer="")],
         RS(["v"], row(v=L("x", lang="en", d="ltr"))))
from_pos(C, "Directional literals in a stream that declares RDF 1.2.",
         "rdf-version",
         [F(options=O(rdf_version=msgs.RDF_VERSION_1_2), vars=[("v", 0)], rows=1,
            literal=[lit_col(values=[lit("x", "en", direction=msgs.DIR_RTL)])], trailer="")],
         RS(["v"], row(v=L("x", lang="en", d="rtl"))))
from_pos(C, "A directional literal in a polymorphic column.",
         "base-direction",
         [F(options=O(rdf_version=V12B, prefix=8), vars=[("v", 0)], rows=2, prefixes=[N(E)], names=[N("a")],
            poly=[poly_col([t_iri(1, 1), t_lit("x", "en", direction=msgs.DIR_LTR)])], trailer="")],
         RS(["v"], row(v=I("a")), row(v=L("x", lang="en", d="ltr"))))
from_pos_encoded(C, "Common usage: labels in several languages and directions, over several frames.",
                 "base-direction",
                 RS(["item", "label"], *[
                     row(item=I(f"item{i}"), label=L(f"label {i}", lang=["en", "ar", "he"][i % 3],
                                                      d=[None, "rtl", "rtl", "ltr"][i % 4]))
                     for i in range(40)]),
                 Opts(prefix=8, rdf_version=V12B), max_rows=6)

from_neg(C, "A directional literal (full form) in a stream that declares RDF 1.1.", "rdf-version",
         [F(options=O(rdf_version=msgs.RDF_VERSION_1_1), vars=[("v", 0)], rows=1,
            literal=[lit_col(values=[lit("x", "en", direction=msgs.DIR_LTR)])], trailer="")],
         "declares RDF 1.1")
from_neg(C, "A directional literal (lexical form) in a stream that declares RDF 1.1.", "rdf-version",
         [F(options=O(rdf_version=msgs.RDF_VERSION_1_1), vars=[("v", 0)], rows=1,
            literal=[lit_col(lex=["x"], langtag="en", direction=msgs.DIR_RTL)], trailer="")],
         "declares RDF 1.1")
from_neg(C, "A full-form literal with a direction but no language tag.", "base-direction",
         [F(options=O(rdf_version=V12B), vars=[("v", 0)], rows=1,
            literal=[lit_col(values=[lit("x", direction=msgs.DIR_LTR)])], trailer="")],
         "direction without langtag")
from_neg(C, "A full-form literal with a direction and a datatype.", "base-direction",
         [F(options=O(rdf_version=V12B, datatype=4), vars=[("v", 0)], rows=1, datatypes=[N(XSD + "int")],
            literal=[lit_col(values=[lit("1", datatype=1, direction=msgs.DIR_LTR)])], trailer="")],
         "direction without langtag")
from_neg(C, "A lexical-form literal column with a direction but no language tag.", "base-direction",
         [F(options=O(rdf_version=V12B), vars=[("v", 0)], rows=1,
            literal=[lit_col(lex=["x"], direction=msgs.DIR_RTL)], trailer="")],
         "direction without langtag")
from_neg(C, "A lexical-form literal column with a direction and a datatype.", "base-direction",
         [F(options=O(rdf_version=V12B, datatype=4), vars=[("v", 0)], rows=1, datatypes=[N(XSD + "int")],
            literal=[lit_col(lex=["1"], datatype=1, direction=msgs.DIR_RTL)], trailer="")],
         "direction without langtag")
from_neg(C, "A full-form literal with an unknown direction value (3).", "base-direction",
         [F(options=O(rdf_version=V12B), vars=[("v", 0)], rows=1,
            literal=[lit_col(values=[lit("x", "en", direction=3)])], trailer="")],
         "unknown base direction")
from_neg(C, "A lexical-form literal column with an unknown direction value (7).", "base-direction",
         [F(options=O(rdf_version=V12B), vars=[("v", 0)], rows=1,
            literal=[lit_col(lex=["x"], langtag="en", direction=7)], trailer="")],
         "unknown base direction")
from_neg(C, "A lexical-form literal column whose datatype is rdf:dirLangString.", "base-direction",
         [F(options=O(rdf_version=V12B, datatype=4), vars=[("v", 0)], rows=1, datatypes=[N(RDF_DIR_LANG_STRING)],
            literal=[lit_col(lex=["x"], datatype=1)], trailer="")],
         "needs a language tag", should=True)
from_neg(C, "A full-form literal whose datatype is rdf:dirLangString.", "base-direction",
         [F(options=O(rdf_version=V12B, datatype=4), vars=[("v", 0)], rows=1, datatypes=[N(RDF_DIR_LANG_STRING)],
            literal=[lit_col(values=[lit("x", datatype=1)])], trailer="")],
         "needs a language tag", should=True)


# =============================================================================
# From Jelly – RDF 1.2 (triple terms)
# =============================================================================

C = SELECT_1_2
V12 = msgs.RDF_VERSION_1_2
ABC_FRAME = dict(prefixes=[N(E)], names=[N("a", "b", "c", "d", "e", "f")])

from_pos(C, "A triple term of three IRIs in a polymorphic column.", "triple-terms",
         [F(options=O(rdf_version=V12, prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3)))])],
            trailer="")],
         RS(["t"], row(t=T(I("a"), I("b"), I("c")))))
from_pos(C, "A triple term with a blank node subject and a directional literal object.", "triple-terms",
         [F(options=O(rdf_version=V12, prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(s_bnode="b0", p_iri=iri(1, 2),
                                            o_literal=lit("x", "en", direction=msgs.DIR_RTL)))])],
            trailer="")],
         RS(["t"], row(t=T(B("b0"), I("b"), L("x", lang="en", d="rtl")))))
from_pos(C, "Triple terms nested three levels deep (in the object position).", "triple-terms",
         [F(options=O(rdf_version=V12, prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(
                s_iri=iri(1, 1), p_iri=iri(None, 2), o_triple=triple(
                    s_iri=iri(None, 3), p_iri=iri(None, 4), o_triple=triple(
                        s_bnode="x", p_iri=iri(None, 5), o_literal=lit("deep")))))])],
            trailer="")],
         RS(["t"], row(t=T(I("a"), I("b"), T(I("c"), I("d"), T(B("x"), I("e"), L("deep")))))))
from_pos(C, "The IRIs inside a triple term take part in the IRI inference state of the polymorphic column, in subject, predicate, object order.",
         "triple-terms",
         [F(options=O(rdf_version=V12, prefix=8), vars=[("t", 0)], rows=3, **ABC_FRAME,
            poly=[poly_col([t_iri(1, None),
                            t_triple(triple(s_iri=iri(), p_iri=iri(), o_iri=iri())),
                            t_iri()])],
            trailer="")],
         RS(["t"], row(t=I("a")), row(t=T(I("b"), I("c"), I("d"))), row(t=I("e"))),
         comment="All name_ids are 0: the first IRI is name 1, the subject, predicate, and object of the triple term are names 2, 3, and 4, and the last IRI is name 5.")
from_pos(C, "A blank node inside a triple term and the same label in a blank node column are the same blank node.",
         "triple-terms",
         [F(options=O(rdf_version=V12, prefix=8), vars=[("b", 0), ("t", 1)], rows=1, **ABC_FRAME,
            bnode=[bnode_col(["n"])],
            poly=[poly_col([t_triple(triple(s_bnode="n", p_iri=iri(1, 1), o_iri=iri(None, 2)))])],
            trailer="")],
         RS(["b", "t"], row(b=B("n"), t=T(B("n"), I("a"), I("b")))))
from_pos(C, "A triple term in a stream that declares no RDF version (allowed: no version is announced).",
         "rdf-version",
         [F(options=O(prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3)))])],
            trailer="")],
         RS(["t"], row(t=T(I("a"), I("b"), I("c")))))
from_pos(C, "The same triple term in consecutive rows, as a repeat run.", "triple-terms",
         [F(options=O(rdf_version=V12, prefix=8), vars=[("t", 0)], rows=3, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_literal=lit("v")))],
                           rep(0, 3))],
            trailer="")],
         RS(["t"], *[row(t=T(I("a"), I("b"), L("v")))] * 3))
from_pos(C, "Concatenated streams: the first segment declares RDF 1.1, the second declares RDF 1.2 and has a triple term.",
         "repeating-the-stream-options",
         [F(options=O(rdf_version=msgs.RDF_VERSION_1_1, prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            iri=[iri_col([1], [], [1])], trailer=""),
          F(options=O(rdf_version=V12, prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3)))])],
            trailer="")],
         RS(["t"], row(t=I("a")), row(t=T(I("a"), I("b"), I("c")))))
from_pos_encoded(C, "Common usage: an annotation query returning statements as triple terms, with IRIs, literals, and nested triple terms, over several frames.",
                 "triple-terms",
                 RS(["stmt", "source", "confidence"], *[
                     row(stmt=T(I(f"s{i % 5}"), I("knows"), I(f"o{i}")) if i % 4 else
                         T(B(f"r{i}"), I("says"), T(I(f"s{i}"), I("age"), L(str(i), "integer"))),
                         source=I(f"src{i % 3}"), confidence=L(f"0.{i}", "decimal"))
                     for i in range(30)]),
                 Opts(prefix=8, datatype=4, rdf_version=V12), max_rows=8)

from_neg(C, "A triple term in a stream that declares RDF 1.1.", "rdf-version",
         [F(options=O(rdf_version=msgs.RDF_VERSION_1_1, prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3)))])],
            trailer="")],
         "declares RDF 1.1 or RDF 1.2 Basic")
from_neg(C, "A triple term in a stream that declares RDF 1.2 Basic.", "rdf-version",
         [F(options=O(rdf_version=V12B, prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3)))])],
            trailer="")],
         "declares RDF 1.1 or RDF 1.2 Basic")
from_neg(C, "A triple term without a subject.", "triple-terms",
         [F(options=O(rdf_version=V12, prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(p_iri=iri(1, 2), o_iri=iri(None, 3)))])], trailer="")],
         "no subject")
from_neg(C, "A triple term without a predicate.", "triple-terms",
         [F(options=O(rdf_version=V12, prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(s_iri=iri(1, 1), o_iri=iri(None, 3)))])], trailer="")],
         "no predicate")
from_neg(C, "A triple term without an object.", "triple-terms",
         [F(options=O(rdf_version=V12, prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(s_iri=iri(1, 1), p_iri=iri(None, 2)))])], trailer="")],
         "no object")
from_neg(C, "Concatenated streams: the second segment declares RDF 1.1 and has a triple term.",
         "repeating-the-stream-options",
         [F(options=O(rdf_version=V12, prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3)))])],
            trailer=""),
          F(options=O(rdf_version=msgs.RDF_VERSION_1_1, prefix=8), vars=[("t", 0)], rows=1, **ABC_FRAME,
            poly=[poly_col([t_triple(triple(s_iri=iri(1, 1), p_iri=iri(None, 2), o_iri=iri(None, 3)))])],
            trailer="")],
         "declares RDF 1.1 or RDF 1.2 Basic")


# =============================================================================
# To Jelly
# =============================================================================

C = SELECT_1_1

to_pos(C, "IRIs only, prefix lookup enabled.", "iri-columns",
       RS(["s", "p", "o"], *[row(s=I(f"s{i % 3}"), p=Iri(f"https://schema.org/p{i % 2}"), o=I(f"o{i}"))
                              for i in range(12)]),
       Opts(prefix=8))
to_pos(C, "IRIs only, prefix lookup disabled.", "iri-columns",
       RS(["s", "o"], *[row(s=I(f"s{i}"), o=Iri(f"urn:x:{i}")) for i in range(8)]),
       Opts())
to_pos(C, "Simple, typed, and language-tagged literals, including in one variable.", "literal-columns",
       RS(["a", "b", "c"], *[row(a=L(f"text {i}"), b=L(str(i), "integer"),
                                  c=[L("x"), L("1.5", "decimal"), L("y", lang="en"), L("z", lang="pl")][i % 4])
                              for i in range(8)]),
       Opts(datatype=8))
to_pos(C, "Blank nodes, repeated in consecutive rows and across frames.", "blank-node-columns",
       RS(["x", "y"], *[row(x=B(f"b{i // 2}"), y=B("shared")) for i in range(10)]),
       Opts(), max_rows=3)
to_pos(C, "Sparse result with unbound cells and repeated values (OPTIONAL).", "sequence-layout",
       OPTIONAL, Opts(prefix=16))
to_pos(C, "A variable whose values mix IRIs, blank nodes, and literals.", "polymorphic-columns",
       MIXED, Opts(prefix=16), max_rows=5)
to_pos(C, "An empty result set with three variables.", "frames-with-no-rows",
       RS(["s", "p", "o"]), Opts())
to_pos(C, "A zero-variable result set with one empty solution.", "zero-variable-result-sets",
       RS([], {}), Opts())
to_pos(C, "A zero-variable result set with no solutions.", "zero-variable-result-sets",
       RS([]), Opts())
to_pos(C, "1000 rows with over 1000 distinct IRIs and a name lookup of 128 entries. The producer has to evict lookup entries and end frames before their working set overflows the tables.",
       "the-working-set-of-a-frame", MANY, Opts(name=128, prefix=16, datatype=4))
to_pos(C, "One row that needs exactly 128 names, with a name lookup of 128 entries and the prefix lookup disabled. The row fits.",
       "the-working-set-of-a-frame",
       RS([f"v{i}" for i in range(128)], {f"v{i}": I(f"n{i}") for i in range(128)}),
       Opts(name=128))
to_pos(C, "Non-ASCII IRIs and literals, and characters that need escaping in text formats.", "rdf-terms",
       UNICODE, Opts(prefix=16))
to_pos(C, "Duplicate solutions: all of them must be preserved, in order.", "ordering",
       RS(["x"], *[row(x=L("same"))] * 5, row(x=L("other")), *[row(x=L("same"))] * 2),
       Opts())
to_pos(C, "A variable that is never bound, next to one that always is.", "columns",
       RS(["never", "always"], *[row(always=L(str(i))) for i in range(4)]), Opts())
to_pos(C, "Variables in a non-alphabetical projection order, each unbound in some rows. The order of the variables must be kept.",
       "result-set-header",
       RS(["z", "a", "m"], row(a=L("1")), row(m=L("2"), z=L("3")), row(z=L("4"), a=L("5"), m=L("6"))),
       Opts())

to_neg(C, "One row that needs 129 distinct names, with a name lookup of 128 entries and the prefix lookup disabled. The row cannot be encoded even in an empty frame, so the producer must throw an error.",
       "the-working-set-of-a-frame",
       RS([f"v{i}" for i in range(129)], {f"v{i}": I(f"n{i}") for i in range(129)}),
       Opts(name=128), "does not fit")
to_neg(C, "A typed literal, with the datatype lookup disabled.", "stream-options",
       RS(["n"], row(n=L("1", "integer"))), Opts(), "datatype lookup is disabled")
to_neg(C, "One row with two different datatypes, with a datatype lookup of one entry.",
       "the-working-set-of-a-frame",
       RS(["a", "b"], row(a=L("1", "integer"), b=L("1.0", "decimal"))), Opts(datatype=1), "does not fit")

C = ASK
to_pos(C, "Boolean result true.", "boolean-results", AskResult(True), Opts())
to_pos(C, "Boolean result false.", "boolean-results", AskResult(False), Opts())

C = SELECT_1_2_BASIC
DIR_RS = RS(["label"], row(label=L("hello", lang="en", d="ltr")), row(label=L("مرحبا", lang="ar", d="rtl")),
            row(label=L("plain", lang="en")))
to_pos(C, "Directional language-tagged strings, stream options declaring RDF 1.2 Basic.", "base-direction",
       DIR_RS, Opts(rdf_version=V12B))
to_pos(C, "Directional language-tagged strings, stream options declaring no RDF version.", "rdf-version",
       DIR_RS, Opts())
to_pos(C, "One language tag and direction for a whole variable (the lexical form of the literal column).",
       "literal-columns",
       RS(["label"], *[row(label=L(f"שורה {i}", lang="he", d="rtl")) for i in range(5)]),
       Opts(rdf_version=V12B))
to_neg(C, "A directional language-tagged string, stream options declaring RDF 1.1.", "rdf-version",
       DIR_RS, Opts(rdf_version=msgs.RDF_VERSION_1_1), "declares RDF 1.1",
       comment="A producer may instead apply a documented fallback encoding (for example, dropping the direction); such a producer does not pass this test.")

C = SELECT_1_2
TT_RS = RS(["t", "o"],
           row(t=T(I("a"), I("b"), I("c")), o=I("x")),
           row(t=T(B("n"), I("b"), L("v", lang="en", d="ltr")), o=L("y")),
           row(t=T(I("a"), I("b"), T(I("c"), I("d"), L("1", "integer"))), o=B("n")))
to_pos(C, "Triple terms, including nested ones, stream options declaring RDF 1.2.", "triple-terms",
       TT_RS, Opts(prefix=8, datatype=4, rdf_version=V12))
to_pos(C, "Triple terms, stream options declaring no RDF version.", "rdf-version",
       TT_RS, Opts(prefix=8, datatype=4))
to_neg(C, "A triple term, stream options declaring RDF 1.1.", "rdf-version",
       TT_RS, Opts(prefix=8, datatype=4, rdf_version=msgs.RDF_VERSION_1_1), "declares RDF 1.1",
       comment="A producer may instead apply a documented fallback encoding; such a producer does not pass this test.")
to_neg(C, "A triple term, stream options declaring RDF 1.2 Basic.", "rdf-version",
       TT_RS, Opts(prefix=8, datatype=4, rdf_version=V12B), "declares RDF 1.1 or 1.2 Basic",
       comment="A producer may instead apply a documented fallback encoding; such a producer does not pass this test.")
