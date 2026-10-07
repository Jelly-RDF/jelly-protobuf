"""Builders for the Jelly-SPARQL messages (sparql.proto and rdf2.proto).

Every argument maps to one field. An argument left as None is not written, so
the builders can produce any frame, valid or not.
"""

from pb import Msg

# RdfVersion
STREAM_TYPE_FLAT = 0
STREAM_TYPE_PUNCTUATED = 1

RDF_VERSION_UNSPECIFIED = 0
RDF_VERSION_1_1 = 1
RDF_VERSION_1_2_BASIC = 2
RDF_VERSION_1_2 = 3

# RdfBaseDirection
DIR_UNSPECIFIED = 0
DIR_LTR = 1
DIR_RTL = 2


def options(
    name=128,
    prefix=None,
    datatype=None,
    version=1,
    rdf_version=None,
    stream_name=None,
    stream_type=None,
):
    return (
        Msg()
        .string(1, stream_name)
        .uint(2, stream_type)
        .uint(5, rdf_version)
        .uint(9, name)
        .uint(10, prefix)
        .uint(11, datatype)
        .uint(15, version)
    )


def var(name, column_index):
    return Msg().string(1, name).uint(2, column_index or None)


def entry(values, id=None):
    """RdfLookupEntryPacked. id=None writes the default 0 (previous + 1)."""
    return Msg().uint(1, id).strings(2, values)


def iri(prefix_id=None, name_id=None):
    """RdfIri."""
    return Msg().uint(1, prefix_id).uint(2, name_id)


def lit(lex, langtag=None, datatype=None, direction=None):
    """RdfLiteral2. datatype=0 is written explicitly (it is in a oneof)."""
    return Msg().string(1, lex).string(2, langtag).uint(3, datatype).uint(4, direction)


def triple(s_iri=None, s_bnode=None, p_iri=None, o_iri=None, o_bnode=None,
           o_literal=None, o_triple=None):
    """RdfTripleTerm."""
    return (
        Msg()
        .msg(1, s_iri)
        .string(2, s_bnode)
        .msg(5, p_iri)
        .msg(9, o_iri)
        .string(10, o_bnode)
        .msg(11, o_literal)
        .msg(12, o_triple)
    )


# Literal kinds (SparqlLiteralColumn.literal_kinds)
K_SIMPLE = 0


def k_dt(datatype_id):
    """The literal kind of a literal with this datatype lookup id."""
    return 2 * datatype_id - 1


def k_lang(index):
    """The literal kind of a language-tagged string with langtags[index]."""
    return 2 * index + 2


# Term kinds (SparqlPolyColumn.kinds)
P_IRI, P_LIT, P_BNODE, P_TRIPLE = 0, 1, 2, 3


def pack_kinds(kinds):
    """Pack term kinds, 2 bits each, four per byte, least significant first."""
    out = bytearray((len(kinds) + 3) // 4)
    for i, k in enumerate(kinds):
        out[i // 4] |= k << (2 * (i % 4))
    return bytes(out)


# Columns
def iri_col(name_ids=None, layouts=None, prefix_ids=None):
    return Msg().packed(1, name_ids).packed(2, layouts).packed(3, prefix_ids)


def bnode_col(values=None, layouts=None):
    return Msg().strings(1, values).packed(2, layouts)


def lit_col(lex=None, layouts=None, kinds=None, langtags=None, dirs=None):
    """SparqlLiteralColumn: lex_values, literal_kinds, langtags, langtag_directions."""
    return (
        Msg()
        .strings(1, lex)
        .packed(2, layouts)
        .packed(3, kinds)
        .strings(4, langtags)
        .packed(5, dirs)
    )


def poly_col(kinds=None, layouts=None, iris=None, literals=None, bnodes=None, triples=None):
    """SparqlPolyColumn. kinds: a list of term kinds (packed here) or raw bytes."""
    if isinstance(kinds, list):
        kinds = pack_kinds(kinds) if kinds else None
    return (
        Msg()
        .bytes(1, kinds)
        .packed(2, layouts)
        .msg(3, iris)
        .msg(4, literals)
        .msg(5, bnodes)
        .msgs(6, triples)
    )


def trailer(error=None):
    return Msg().string(1, error)


def frame(
    options=None,
    vars=None,
    rows=None,
    names=None,
    prefixes=None,
    datatypes=None,
    iri=None,
    bnode=None,
    literal=None,
    poly=None,
    ask=None,
    trailer=None,
    metadata=None,
):
    """SparqlResultsFrame.

    vars: list of (name, column_index); ask: True/False for a boolean result;
    trailer: a string (the error, "" for a clean end); metadata: dict of
    str -> bytes.
    """
    m = Msg().msg(1, options)
    for name, idx in vars or []:
        m.msg(2, var(name, idx))
    m.uint(3, rows or None)
    m.msgs(4, names).msgs(5, prefixes).msgs(6, datatypes)
    m.msgs(7, iri).msgs(8, bnode).msgs(9, literal).msgs(10, poly)
    if ask is not None:
        m.msg(11, Msg().bool(1, ask or None))
    if trailer is not None:
        m.msg(12, Msg().string(1, trailer or None))
    for k, v in (metadata or {}).items():
        m.msg(15, Msg().string(1, k).bytes(2, v))
    return m


def token(skip, kind, length):
    """One sequence layout exception, as a list of 1 or 2 varints.

    kind: 0 = repeat run, 1 = unbound run. length is the offset run length
    code (repeat: cells - 2, unbound: cells - 1).
    """
    if length <= 14:
        return [(skip << 5) | (kind << 4) | length]
    return [(skip << 5) | (kind << 4) | 15, length - 15]


def rep(skip, cells):
    """A repeat run: the value at the current position fills `cells` cells."""
    return token(skip, 0, cells - 2)


def unb(skip, cells):
    """An unbound run of `cells` cells."""
    return token(skip, 1, cells - 1)
