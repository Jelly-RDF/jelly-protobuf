"""Builders for the Jelly-SPARQL messages (sparql.proto).

Every argument maps to one field. An argument left as None is not written, so
the builders can produce any frame, valid or not. The builders of the messages
shared with Jelly-RDF (rdf.proto) are in generator_common.msgs.
"""

from generator_common.msgs import *  # noqa: F401,F403
from generator_common.pb import Msg

# SparqlStreamType
STREAM_TYPE_FLAT = 0
STREAM_TYPE_PUNCTUATED = 1


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
