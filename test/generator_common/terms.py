"""RDF terms, shared by the Jelly-RDF and Jelly-SPARQL test generators."""

from dataclasses import dataclass
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


class BnodeMap:
    """A bijection between the blank node labels of two results, built while comparing."""

    def __init__(self):
        self.fwd, self.back = {}, {}

    def same(self, x, y) -> bool:
        """Whether two terms are equal under the bijection, extending it if needed."""
        if type(x) is not type(y):
            return False
        if isinstance(x, Bnode):
            if self.fwd.setdefault(x.label, y.label) != y.label:
                return False
            return self.back.setdefault(y.label, x.label) == x.label
        if isinstance(x, Triple):
            return self.same(x.s, y.s) and self.same(x.p, y.p) and self.same(x.o, y.o)
        return x == y
