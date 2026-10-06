"""Reference Jelly-SPARQL producer.

Used to build the expected outputs of the "to Jelly" tests, and the inputs of
"from Jelly" tests that exercise common usage patterns. It follows the
producer-side rules of the specification: least-recently-used lookup tables,
frames that end before their working set would overflow the tables, the most
specific column type for each variable in each frame, a header restated only
when the column layout changes, and a trailer in the last frame.
"""

from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

import msgs
from model import AskResult, Bnode, Iri, Lit, Triple


class EncodeError(Exception):
    pass


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


class Table:
    """A lookup table with LRU eviction and per-frame working set tracking."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.ids = {}  # value -> id
        self.values = {}  # id -> value
        self.recency = OrderedDict()  # id -> None, oldest first
        self.last_id = 0
        self.touched = set()
        self.pending = []  # (id, value) assigned in the current frame

    def fits(self, keys) -> bool:
        keys = set(keys)
        new = [k for k in keys if k not in self.ids]
        free = self.capacity - len(self.ids)
        evictable = sum(
            1
            for id in self.recency
            if id not in self.touched and self.values[id] not in keys
        )
        return len(new) <= free + evictable

    def use(self, keys):
        keys = list(dict.fromkeys(keys))
        for k in keys:
            if k in self.ids:
                self._touch(self.ids[k])
        for k in keys:
            if k not in self.ids:
                self._allocate(k)

    def _touch(self, id):
        self.touched.add(id)
        self.recency.move_to_end(id)

    def _allocate(self, value):
        if len(self.ids) < self.capacity:
            id = len(self.ids) + 1
        else:
            id = next(i for i in self.recency if i not in self.touched)
            del self.ids[self.values[id]]
            del self.recency[id]
        self.ids[value] = id
        self.values[id] = value
        self.recency[id] = None
        self.pending.append((id, value))
        self._touch(id)

    def entries(self):
        """The frame's lookup entries, packed into runs of consecutive ids."""
        out = []
        run_start, run = None, []
        for id, value in self.pending:
            if run and id == run_start + len(run):
                run.append(value)
                continue
            if run:
                out.append(self._entry(run_start, run))
            run_start, run = id, [value]
        if run:
            out.append(self._entry(run_start, run))
        return out

    def _entry(self, start, values):
        e = msgs.entry(values, None if start == self.last_id + 1 else start)
        self.last_id = start + len(values) - 1
        return e

    def end_frame(self):
        self.touched.clear()
        self.pending.clear()


def split_iri(iri: str):
    i = max(iri.rfind("/"), iri.rfind("#"))
    return ("", iri) if i < 0 else (iri[: i + 1], iri[i + 1 :])


def term_kind(t) -> str:
    return {Iri: "iri", Bnode: "bnode", Lit: "literal", Triple: "triple"}[type(t)]


def runs(cells):
    """Split cells into run values and a sequence layout."""
    values, layouts = [], []
    skip = 0
    bound = [i for i, c in enumerate(cells) if c is not None]
    last_bound = bound[-1] if bound else -1
    i, n = 0, len(cells)
    while i < n:
        j = i
        if cells[i] is None:
            while j < n and cells[j] is None:
                j += 1
            if j > last_bound:
                break  # trailing unbound cells: rely on padding
            layouts += msgs.unb(skip, j - i)
            skip = 0
        else:
            while j < n and cells[j] == cells[i]:
                j += 1
            values.append(cells[i])
            if j - i == 1:
                skip += 1
            else:
                layouts += msgs.rep(skip, j - i)
                skip = 0
        i = j
    return values, layouts


class Encoder:
    def __init__(self, opts: Opts, max_rows: int = 64):
        self.opts = opts
        self.max_rows = max_rows
        self.names = Table(opts.name)
        self.prefixes = Table(opts.prefix)
        self.datatypes = Table(opts.datatype)

    # --- terms -> lookup keys --------------------------------------------------

    def iri_parts(self, value: str):
        if self.opts.prefix == 0:
            return None, value
        return split_iri(value)

    def keys(self, t, out):
        """Collect (table, key) pairs needed by a term."""
        if isinstance(t, Iri):
            prefix, name = self.iri_parts(t.value)
            if prefix is not None:
                out.append((self.prefixes, prefix))
            out.append((self.names, name))
        elif isinstance(t, Lit):
            if t.datatype is not None:
                if self.opts.datatype == 0:
                    raise EncodeError("a typed literal, but the datatype lookup is disabled")
                out.append((self.datatypes, t.datatype))
            if t.direction is not None and self.opts.rdf_version == msgs.RDF_VERSION_1_1:
                raise EncodeError("a base direction, but the stream declares RDF 1.1")
        elif isinstance(t, Triple):
            if self.opts.rdf_version in (msgs.RDF_VERSION_1_1, msgs.RDF_VERSION_1_2_BASIC):
                raise EncodeError("a triple term, but the stream declares RDF 1.1 or 1.2 Basic")
            for x in (t.s, t.p, t.o):
                self.keys(x, out)

    def iri_ids(self, value: str):
        prefix, name = self.iri_parts(value)
        pid = 0 if prefix is None else self.prefixes.ids[prefix]
        return pid, self.names.ids[name]

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
        self.mapping = None
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
            for table in (self.names, self.prefixes, self.datatypes):
                table.use([k for tb, k in needed if tb is table])
            rows.append(row)
        if rows or len(self.frames) == start:
            self.flush(rows)
        self.frames[-1]["trailer"] = ""
        if result.links:
            self.frames[start]["metadata"] = {"link": "\n".join(result.links).encode()}

    def fits(self, needed) -> bool:
        return all(
            table.fits([k for tb, k in needed if tb is table])
            for table in (self.names, self.prefixes, self.datatypes)
        )

    def flush(self, rows):
        f = {
            "rows": len(rows),
            "names": self.names.entries(),
            "prefixes": self.prefixes.entries(),
            "datatypes": self.datatypes.entries(),
        }
        if not self.frames:
            f["options"] = self.opts.msg()
        first = len(self.frames) == self.start  # the first frame of the result set
        columns = {"iri": [], "bnode": [], "literal": [], "poly": []}
        placement = []
        if rows and self.vars:
            for v in self.vars:
                cells = [row.get(v) for row in rows]
                kinds = {term_kind(c) for c in cells if c is not None}
                kind = kinds.pop() if len(kinds) == 1 else ("poly" if kinds else "iri")
                if kind == "triple":
                    kind = "poly"
                values, layouts = runs(cells)
                placement.append((kind, len(columns[kind])))
                columns[kind].append(getattr(self, "col_" + kind)(values, layouts))
            offsets = {}
            offset = 0
            for kind in ("iri", "bnode", "literal", "poly"):
                offsets[kind] = offset
                offset += len(columns[kind])
            mapping = [offsets[kind] + pos for kind, pos in placement]
            f.update(columns)
            need_header = first or mapping != self.mapping
        elif first:
            # No columns: an empty or a zero-variable result set.
            mapping = list(range(len(self.vars)))
            need_header = True
        else:
            need_header = False
        if need_header:
            f["vars"] = list(zip(self.vars, mapping))
            self.mapping = mapping
        self.frames.append(f)
        for table in (self.names, self.prefixes, self.datatypes):
            table.end_frame()

    # --- columns -----------------------------------------------------------

    def col_iri(self, values, layouts):
        ids = [self.iri_ids(t.value) for t in values]
        name_ids, prev = [], 0
        for _, nid in ids:
            name_ids.append(0 if nid == prev + 1 else nid)
            prev = nid
        pids = [p for p, _ in ids]
        if self.opts.prefix == 0 or not pids:
            prefix_ids = []
        elif len(set(pids)) == 1:
            prefix_ids = [pids[0]]
        else:
            prefix_ids, prev = [], 0
            for p in pids:
                prefix_ids.append(0 if p == prev else p)
                prev = p
        return msgs.iri_col(name_ids, layouts, prefix_ids)

    def col_bnode(self, values, layouts):
        return msgs.bnode_col([t.label for t in values], layouts)

    def col_literal(self, values, layouts):
        langtags = []  # (tag, direction), in the order of first use
        kinds = []
        for t in values:
            if t.lang is not None:
                key = (t.lang, t.direction)
                if key not in langtags:
                    langtags.append(key)
                kinds.append(msgs.k_lang(langtags.index(key)))
            elif t.datatype is not None:
                kinds.append(msgs.k_dt(self.datatypes.ids[t.datatype]))
            else:
                kinds.append(msgs.K_SIMPLE)
        if set(kinds) == {msgs.K_SIMPLE}:
            kinds = []
        elif len(set(kinds)) == 1:
            kinds = kinds[:1]
        dirs = [self.direction(d) for _, d in langtags]
        return msgs.lit_col(
            lex=[t.lex for t in values],
            layouts=layouts,
            kinds=kinds,
            langtags=[tag for tag, _ in langtags],
            dirs=dirs if any(dirs) else None,
        )

    def col_poly(self, values, layouts):
        kind_of = {Iri: msgs.P_IRI, Lit: msgs.P_LIT, Bnode: msgs.P_BNODE, Triple: msgs.P_TRIPLE}
        kinds = [kind_of[type(t)] for t in values]
        split = [[t for t, k in zip(values, kinds) if k == want] for want in range(4)]
        iris, lits, bnodes, triples = split
        state = [0, 0]
        return msgs.poly_col(
            kinds=kinds,
            layouts=layouts,
            iris=self.col_iri(iris, None) if iris else None,
            literals=self.col_literal(lits, None) if lits else None,
            bnodes=self.col_bnode(bnodes, None) if bnodes else None,
            triples=[self.triple_term(t, state) for t in triples],
        )

    def direction(self, d):
        return {None: 0, "ltr": msgs.DIR_LTR, "rtl": msgs.DIR_RTL}[d]

    def lit(self, t: Lit):
        return msgs.lit(
            t.lex,
            langtag=t.lang,
            datatype=self.datatypes.ids[t.datatype] if t.datatype else None,
            direction=self.direction(t.direction) or None,
        )

    def rdf_iri(self, t: Iri, state):
        pid, nid = self.iri_ids(t.value)
        assert pid != 0 or state[0] == 0, "cannot go back to no prefix"
        m = msgs.iri(None if pid == state[0] else pid, None if nid == state[1] + 1 else nid)
        state[0], state[1] = pid, nid
        return m

    def triple_term(self, t: Triple, state):
        kw = {}
        if isinstance(t.s, Iri):
            kw["s_iri"] = self.rdf_iri(t.s, state)
        else:
            kw["s_bnode"] = t.s.label
        kw["p_iri"] = self.rdf_iri(t.p, state)
        o = t.o
        if isinstance(o, Iri):
            kw["o_iri"] = self.rdf_iri(o, state)
        elif isinstance(o, Bnode):
            kw["o_bnode"] = o.label
        elif isinstance(o, Lit):
            kw["o_literal"] = self.lit(o)
        else:
            kw["o_triple"] = self.triple_term(o, state)
        return msgs.triple(**kw)


def encode(result, opts: Opts, max_rows: int = 64):
    return Encoder(opts, max_rows).encode(result)
