"""Reference Jelly-RDF 1.2 producer.

Used to build the expected outputs of the "to Jelly" tests, and the inputs of
"from Jelly" tests that exercise common usage patterns. It follows the
producer-side rules of the specification: least-recently-used lookup tables,
batches that end before their working set would overflow the tables, columns
with no term types when all their values are of one type, and a message
boundary at the end of every RDF Message. The lookup tables and columns are
encoded by generator_common.colenc.
"""

from dataclasses import dataclass
from typing import Optional

import msgs
from generator_common.colenc import ColumnWriter, EncodeError, runs  # noqa: F401
from model import Iri, Lit, Triple


@dataclass
class Opts:
    physical_type: int = msgs.TRIPLES
    name: int = 128
    prefix: int = 0
    datatype: int = 0
    rdf_version: Optional[int] = None
    stream_type: Optional[int] = None
    stream_name: Optional[str] = None

    def msg(self):
        return msgs.options(
            physical_type=self.physical_type,
            stream_type=self.stream_type,
            name=self.name,
            prefix=self.prefix or None,
            datatype=self.datatype or None,
            rdf_version=self.rdf_version or None,
            stream_name=self.stream_name,
        )

    @property
    def messages(self) -> bool:
        return self.stream_type == msgs.MESSAGES

    def describe(self) -> str:
        parts = [
            f"physical-type={PHYSICAL_TYPE_LABELS[self.physical_type]}",
            f"max-name-table-size={self.name}",
            f"max-prefix-table-size={self.prefix}",
            f"max-datatype-table-size={self.datatype}",
            f"rdf-version={RDF_VERSION_LABELS[self.rdf_version or 0]}",
        ]
        if self.stream_type is not None:
            parts.insert(1, f"stream-type={STREAM_TYPE_LABELS[self.stream_type]}")
        if self.stream_name is not None:
            parts.append(f"stream-name={self.stream_name!r}")
        return ", ".join(parts)


PHYSICAL_TYPE_LABELS = {msgs.TRIPLES: "triples", msgs.QUADS: "quads"}
RDF_VERSION_LABELS = {0: "unspecified", 1: "1.1", 2: "1.2-basic", 3: "1.2"}
STREAM_TYPE_LABELS = {msgs.FLAT: "flat", msgs.MESSAGES: "messages"}


class Encoder(ColumnWriter):
    def __init__(self, opts: Opts, max_rows: int = 64):
        super().__init__(opts)
        self.max_rows = max_rows

    def encode(self, data):
        """Encode a list of statements (FLAT), or a list of messages (MESSAGES)."""
        self.frames = []
        self.rows = []
        self.lengths = []  # message_lengths of the current batch
        self.open = 0  # statements of the current batch not yet in a finished message
        for message in data if self.opts.messages else [data]:
            for st in message:
                self.statement(st)
            if self.opts.messages:
                self.lengths.append(self.open)
                self.open = 0
        if self.rows or self.lengths or not self.frames:
            self.flush()
        return self.frames

    def statement(self, st):
        if st.g is not None and self.opts.physical_type == msgs.TRIPLES:
            raise EncodeError("a statement in a named graph, but the physical type is TRIPLES")
        if isinstance(st.s, (Lit, Triple)) or not isinstance(st.p, Iri) or isinstance(st.g, (Lit, Triple)):
            raise EncodeError("a statement that is not valid RDF (generalized RDF)")
        needed = []
        for t in (st.s, st.p, st.o, st.g):
            if t is not None:
                self.keys(t, needed)
        if len(self.rows) >= self.max_rows or not self.fits(needed):
            if self.rows:
                self.flush()
            if not self.fits(needed):
                raise EncodeError("a single statement does not fit in the lookup tables")
        self.use(needed)
        self.rows.append(st)
        self.open += 1

    def flush(self):
        rows = self.rows
        b = {"rows": len(rows), **self.lookup_entries()}
        if rows:
            b["s"] = self.column(*runs([st.s for st in rows]))
            b["p"] = self.column(*runs([st.p for st in rows]))
            b["o"] = self.column(*runs([st.o for st in rows]))
            if any(st.g is not None for st in rows):
                b["g"] = self.column(*runs([st.g for st in rows]))
        if self.lengths:
            b["lengths"] = self.lengths
        f = {}
        if not self.frames:
            f["options"] = self.opts.msg()
        if rows or self.lengths or any(b[k] for k in ("names", "prefixes", "datatypes")):
            f["columns"] = msgs.batch(**b)
        self.frames.append(msgs.frame(**f))
        self.rows = []
        self.lengths = []
        self.open = 0


def encode(data, opts: Opts, max_rows: int = 64):
    return Encoder(opts, max_rows).encode(data)

