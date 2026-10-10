"""Builders for the Jelly-SPARQL messages (sparql.proto and rdf.proto).

Every argument maps to one field. An argument left as None is not written, so
the builders can produce any frame, valid or not.
"""

from pb import Msg

# SparqlStreamType
STREAM_TYPE_FLAT = 0
STREAM_TYPE_PUNCTUATED = 1

# RdfVersion
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


def entry(values, id=None):
    """RdfLookupEntryPacked. id=None writes the default 0 (previous + 1)."""
    return Msg().uint(1, id).strings(2, values)


def iri(prefix_id=None, name_id=None):
    """RdfIri."""
    return Msg().uint(1, prefix_id).uint(2, name_id)


def lit(lex, langtag=None, datatype=None, direction=None):
    """RdfLiteral. datatype=0 is written explicitly (it is in a oneof)."""
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


# Literal kinds (RdfColumn.literal_kinds)
K_SIMPLE = 0


def k_dt(datatype_id):
    """The literal kind of a literal with this datatype lookup id."""
    return 2 * datatype_id - 1


def k_lang(index):
    """The literal kind of a language-tagged string with langtags[index]."""
    return 2 * index + 2


# Term types (RdfColumn.kinds)
T_IRI, T_LIT, T_BNODE, T_TRIPLE = 0, 1, 2, 3


def pack_kinds(kinds):
    """Pack term types, 2 bits each, four per byte, least significant first."""
    out = bytearray((len(kinds) + 3) // 4)
    for i, k in enumerate(kinds):
        out[i // 4] |= k << (2 * (i % 4))
    return bytes(out)


# Columns
def col(kinds=None, layouts=None, name_ids=None, prefix_ids=None, lex=None, lit_kinds=None,
        langtags=None, dirs=None, bnodes=None, triples=None):
    """RdfColumn. kinds: a list of term types (packed here) or raw bytes."""
    if isinstance(kinds, list):
        kinds = pack_kinds(kinds) if kinds else None
    return (
        Msg()
        .bytes(1, kinds)
        .packed(2, layouts)
        .packed(3, name_ids)
        .packed(4, prefix_ids)
        .strings(5, lex)
        .packed(6, lit_kinds)
        .strings(7, langtags)
        .packed(8, dirs)
        .strings(9, bnodes)
        .msgs(10, triples)
    )


def iri_col(name_ids=None, layouts=None, prefix_ids=None):
    """An RdfColumn of IRIs only."""
    return col(layouts=layouts, name_ids=name_ids, prefix_ids=prefix_ids)


def bnode_col(labels=None, layouts=None):
    """An RdfColumn of blank nodes only."""
    return col(layouts=layouts, bnodes=labels)


def lit_col(lex=None, layouts=None, kinds=None, langtags=None, dirs=None):
    """An RdfColumn of literals only. kinds are the literal kinds."""
    return col(layouts=layouts, lex=lex, lit_kinds=kinds, langtags=langtags, dirs=dirs)


def trailer(error=None):
    return Msg().string(1, error)


def frame(
    options=None,
    vars=None,
    rows=None,
    names=None,
    prefixes=None,
    datatypes=None,
    cols=None,
    ask=None,
    trailer=None,
    metadata=None,
):
    """SparqlResultsFrame.

    vars: list of variable names; cols: list of RdfColumn messages; ask:
    True/False for a boolean result; trailer: a string (the error, "" for a
    clean end); metadata: dict of str -> bytes.
    """
    m = Msg().msg(1, options)
    m.strings(2, vars)
    m.uint(3, rows or None)
    m.msgs(4, names).msgs(5, prefixes).msgs(6, datatypes)
    m.msgs(7, cols)
    if ask is not None:
        m.msg(8, Msg().bool(1, ask or None))
    if trailer is not None:
        m.msg(9, Msg().string(1, trailer or None))
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
