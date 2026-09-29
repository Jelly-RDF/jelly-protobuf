"""RDF terms and SPARQL result sets, and their SPARQL Query Results JSON form.

The JSON form follows SPARQL 1.2 Query Results JSON: `its:dir` for the base
direction and `{"type": "triple", ...}` for triple terms.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, Union

XSD = "http://www.w3.org/2001/XMLSchema#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XSD_STRING = XSD + "string"
RDF_LANG_STRING = RDF + "langString"
RDF_DIR_LANG_STRING = RDF + "dirLangString"


@dataclass(frozen=True)
class Iri:
    value: str


@dataclass(frozen=True)
class Bnode:
    label: str


@dataclass(frozen=True)
class Lit:
    lex: str
    datatype: Optional[str] = None  # None = simple literal (xsd:string)
    lang: Optional[str] = None
    direction: Optional[str] = None  # "ltr", "rtl", or None

    def __post_init__(self):
        if self.datatype == XSD_STRING:
            object.__setattr__(self, "datatype", None)
        assert not (self.datatype and self.lang)
        assert self.direction is None or self.lang


@dataclass(frozen=True)
class Triple:
    s: "Term"
    p: "Term"
    o: "Term"


Term = Union[Iri, Bnode, Lit, Triple]


@dataclass
class ResultSet:
    vars: list
    rows: list  # list of dicts: variable name -> Term (unbound = missing)
    links: list = field(default_factory=list)


@dataclass
class AskResult:
    value: bool


# --- SPARQL Query Results JSON ----------------------------------------------


def term_to_json(t: Term) -> dict:
    if isinstance(t, Iri):
        return {"type": "uri", "value": t.value}
    if isinstance(t, Bnode):
        return {"type": "bnode", "value": t.label}
    if isinstance(t, Lit):
        out = {"type": "literal", "value": t.lex}
        if t.lang is not None:
            out["xml:lang"] = t.lang
        if t.direction is not None:
            out["its:dir"] = t.direction
        if t.datatype is not None:
            out["datatype"] = t.datatype
        return out
    if isinstance(t, Triple):
        return {
            "type": "triple",
            "value": {
                "subject": term_to_json(t.s),
                "predicate": term_to_json(t.p),
                "object": term_to_json(t.o),
            },
        }
    raise TypeError(t)


def term_from_json(j: dict) -> Term:
    kind = j["type"]
    if kind == "uri":
        return Iri(j["value"])
    if kind == "bnode":
        return Bnode(j["value"])
    if kind in ("literal", "typed-literal"):
        return Lit(j["value"], j.get("datatype"), j.get("xml:lang"), j.get("its:dir"))
    if kind == "triple":
        v = j["value"]
        return Triple(
            term_from_json(v["subject"]),
            term_from_json(v["predicate"]),
            term_from_json(v["object"]),
        )
    raise ValueError(kind)


def to_srj(result) -> str:
    if isinstance(result, AskResult):
        doc = {"head": {}, "boolean": result.value}
    else:
        head = {"vars": list(result.vars)}
        if result.links:
            head["link"] = list(result.links)
        bindings = []
        for row in result.rows:
            bindings.append({v: term_to_json(row[v]) for v in result.vars if v in row})
        doc = {"head": head, "results": {"bindings": bindings}}
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def from_srj(text: str):
    doc = json.loads(text)
    if "boolean" in doc:
        return AskResult(doc["boolean"])
    rows = [
        {v: term_from_json(t) for v, t in b.items()} for b in doc["results"]["bindings"]
    ]
    return ResultSet(doc["head"].get("vars", []), rows, doc["head"].get("link", []))


# --- equivalence --------------------------------------------------------------


def equivalent(a, b) -> Optional[str]:
    """Compare two results as the spec's test suite section defines it.

    Returns None if equivalent, or a description of the first difference.
    Links are not part of the comparison.
    """
    if isinstance(a, AskResult) or isinstance(b, AskResult):
        if type(a) is not type(b):
            return "one result is boolean, the other is not"
        return None if a.value == b.value else f"boolean {a.value} != {b.value}"
    if a.vars != b.vars:
        return f"variables {a.vars} != {b.vars}"
    if len(a.rows) != len(b.rows):
        return f"{len(a.rows)} rows != {len(b.rows)} rows"
    fwd, back = {}, {}

    def same(x, y) -> bool:
        if type(x) is not type(y):
            return False
        if isinstance(x, Bnode):
            if fwd.setdefault(x.label, y.label) != y.label:
                return False
            return back.setdefault(y.label, x.label) == x.label
        if isinstance(x, Triple):
            return same(x.s, y.s) and same(x.p, y.p) and same(x.o, y.o)
        return x == y

    for i, (ra, rb) in enumerate(zip(a.rows, b.rows)):
        if set(ra) != set(rb):
            return f"row {i}: bound variables {sorted(ra)} != {sorted(rb)}"
        for v in a.vars:
            if v in ra and not same(ra[v], rb[v]):
                return f"row {i}, ?{v}: {ra[v]} != {rb[v]}"
    return None
