"""Builders for the Jelly-RDF 1.2 messages (rdf.proto, column layout).

Every argument maps to one field. An argument left as None is not written, so
the builders can produce any frame, valid or not. The builders of the messages
shared with Jelly-SPARQL (lookup entries, RDF terms, columns) are in
generator_common.msgs.
"""

from generator_common.msgs import *  # noqa: F401,F403
from generator_common.pb import Msg

# PhysicalStreamType
PHYSICAL_UNSPECIFIED = 0
TRIPLES = 1
QUADS = 2
GRAPHS = 3

# RdfStreamType
FLAT = 0
MESSAGES = 1

# LogicalStreamType (Jelly-RDF 1.0.x and 1.1.x only)
LOGICAL_FLAT_TRIPLES = 1


def options(
    physical_type=TRIPLES,
    name=128,
    prefix=None,
    datatype=None,
    version=3,
    rdf_version=None,
    stream_type=None,
    stream_name=None,
    generalized=None,
    rdf_star=None,
    logical_type=None,
):
    """RdfStreamOptions."""
    return (
        Msg()
        .string(1, stream_name)
        .uint(2, physical_type)
        .bool(3, generalized)
        .bool(4, rdf_star)
        .uint(5, stream_type)
        .uint(6, rdf_version)
        .uint(9, name)
        .uint(10, prefix)
        .uint(11, datatype)
        .uint(14, logical_type)
        .uint(15, version)
    )


def options_row(opts):
    """An RdfStreamRow with the stream options."""
    return Msg().msg(1, opts)


def namespace(name=None, value=None):
    """RdfNamespaceDeclaration. value is an RdfIri message."""
    return Msg().string(1, name).msg(2, value)


def batch(
    rows=None,
    names=None,
    prefixes=None,
    datatypes=None,
    namespaces=None,
    s=None,
    p=None,
    o=None,
    g=None,
    lengths=None,
):
    """RdfColumnBatch. s, p, o, g are RdfColumn messages; lengths is message_lengths."""
    return (
        Msg()
        .uint(1, rows or None)
        .msgs(2, names)
        .msgs(3, prefixes)
        .msgs(4, datatypes)
        .msgs(5, namespaces)
        .msg(6, s)
        .msg(7, p)
        .msg(8, o)
        .msg(9, g)
        .packed(15, lengths)
    )


def frame(options=None, rows=None, columns=None, metadata=None):
    """RdfStreamFrame.

    options: an RdfStreamOptions message, written as the only row; rows: a
    list of RdfStreamRow messages, written after the options row (for invalid
    frames); columns: an RdfColumnBatch message; metadata: dict of str ->
    bytes.
    """
    m = Msg()
    if options is not None:
        m.msg(1, options_row(options))
    m.msgs(1, rows)
    m.msg(2, columns)
    for k, v in (metadata or {}).items():
        m.msg(15, Msg().string(1, k).bytes(2, v))
    return m
