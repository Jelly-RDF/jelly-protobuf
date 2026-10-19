"""Helper script for the test generator: encodes Jelly-SPARQL streams.

Used to build the expected outputs of the "to Jelly" tests, and the inputs of
"from Jelly" tests that exercise common usage patterns. It follows the
producer-side rules of the specification: least-recently-used lookup tables,
frames that end before their working set would overflow the tables, columns
with no term types when all their values are of one type, and a trailer in
the last frame. The lookup tables and columns are encoded by
generator_common.colenc.
"""

from dataclasses import dataclass
from typing import Optional

import msgs
from generator_common.colenc import ColumnWriter, EncodeError, runs  # noqa: F401
from model import AskResult


@dataclass
class Opts:
    name: int = 128
    prefix: int = 0
    datatype: int = 0
    rdf_version: Optional[int] = None
    version: int = 1
    stream_name: Optional[str] = None
    stream_type: Optional[int] = None

    def msg(self):
        return msgs.options(
            stream_type=self.stream_type,
            name=self.name,
            prefix=self.prefix or None,
            datatype=self.datatype or None,
            version=self.version,
            rdf_version=self.rdf_version or None,
            stream_name=self.stream_name,
        )

    def describe(self) -> str:
        parts = [
            f"max-name-table-size={self.name}",
            f"max-prefix-table-size={self.prefix}",
            f"max-datatype-table-size={self.datatype}",
            f"rdf-version={RDF_VERSION_LABELS[self.rdf_version or 0]}",
        ]
        if self.stream_type is not None:
            parts.insert(0, f"stream-type={STREAM_TYPE_LABELS[self.stream_type]}")
        if self.stream_name is not None:
            parts.append(f"stream-name={self.stream_name!r}")
        return ", ".join(parts)


RDF_VERSION_LABELS = {0: "unspecified", 1: "1.1", 2: "1.2-basic", 3: "1.2"}
STREAM_TYPE_LABELS = {0: "flat", 1: "punctuated"}


class Encoder(ColumnWriter):
    def __init__(self, opts: Opts, max_rows: int = 64):
        super().__init__(opts)
        self.max_rows = max_rows

    # --- stream ----------------------------------------------------------------

    def encode(self, result):
        """Encode one result set, or a list of result sets (PUNCTUATED stream)."""
        self.frames = []
        for r in result if isinstance(result, list) else [result]:
            self.result_set(r)
        return [msgs.frame(**f) for f in self.frames]

    def result_set(self, result):
        start = len(self.frames)
        if isinstance(result, AskResult):
            f = {"ask": result.value, "trailer": ""}
            if not self.frames:
                f["options"] = self.opts.msg()
            self.frames.append(f)
            return
        if "" in result.vars:
            raise EncodeError("a variable with an empty name")
        self.vars = result.vars
        self.start = start
        rows = []
        for row in result.rows:
            needed = []
            for t in row.values():
                self.keys(t, needed)
            if len(rows) >= self.max_rows or not self.fits(needed):
                if rows:
                    self.flush(rows)
                    rows = []
                if not self.fits(needed):
                    raise EncodeError("a single row does not fit in the lookup tables")
            self.use(needed)
            rows.append(row)
        if rows or len(self.frames) == start:
            self.flush(rows)
        self.frames[-1]["trailer"] = ""
        if result.links:
            self.frames[start]["metadata"] = {"link": "\n".join(result.links).encode()}

    def flush(self, rows):
        f = {"rows": len(rows), **self.lookup_entries()}
        if not self.frames:
            f["options"] = self.opts.msg()
        if len(self.frames) == self.start:  # the first frame of the result set
            f["vars"] = self.vars
        if rows and self.vars:
            f["cols"] = [self.column(*runs([row.get(v) for row in rows])) for v in self.vars]
        self.frames.append(f)


def encode(result, opts: Opts, max_rows: int = 64):
    return Encoder(opts, max_rows).encode(result)
