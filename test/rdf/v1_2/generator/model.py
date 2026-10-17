"""RDF statements, and their N-Triples and N-Quads (RDF 1.2) form.

A FLAT stream decodes to a list of statements. A stream of RDF Messages
decodes to a list of messages, each a list of statements.
"""

import re
from dataclasses import dataclass
from typing import Optional

from generator_common.terms import (  # noqa: F401
    RDF,
    RDF_DIR_LANG_STRING,
    RDF_LANG_STRING,
    XSD,
    XSD_STRING,
    Bnode,
    BnodeMap,
    Iri,
    Lit,
    Term,
    Triple,
)


@dataclass(frozen=True)
class St:
    """A statement: a triple, or a quad when g is set. g = None is the default graph."""

    s: Term
    p: Term
    o: Term
    g: Optional[Term] = None


class Messages(list):
    """The statements of a stream of RDF Messages: a list of messages, each a list
    of statements. A FLAT stream is a plain list of statements."""


# --- N-Triples / N-Quads -------------------------------------------------------

# Characters that IRIREF does not allow (RDF 1.2 N-Triples).
BAD_IRI_CHARS = re.compile(r'[\x00-\x20<>"{}|^`\\]')
BNODE_LABEL = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*(?<!\.)")
LANGTAG = re.compile(r"[a-zA-Z]+(-[a-zA-Z0-9]+)*")


class SyntaxProblem(Exception):
    pass


def term_nt(t: Term) -> str:
    if isinstance(t, Iri):
        if BAD_IRI_CHARS.search(t.value):
            raise SyntaxProblem(f"IRI cannot be written in N-Triples: {t.value!r}")
        return f"<{t.value}>"
    if isinstance(t, Bnode):
        if not BNODE_LABEL.fullmatch(t.label):
            raise SyntaxProblem(f"blank node label cannot be written in N-Triples: {t.label!r}")
        return f"_:{t.label}"
    if isinstance(t, Lit):
        lex = (t.lex.replace("\\", "\\\\").replace('"', '\\"')
               .replace("\n", "\\n").replace("\r", "\\r"))
        out = f'"{lex}"'
        if t.lang is not None:
            if not LANGTAG.fullmatch(t.lang):
                raise SyntaxProblem(f"language tag cannot be written in N-Triples: {t.lang!r}")
            out += f"@{t.lang}"
            if t.direction is not None:
                out += f"--{t.direction}"
        elif t.datatype is not None:
            out += "^^" + term_nt(Iri(t.datatype))
        return out
    if isinstance(t, Triple):
        return f"<<( {term_nt(t.s)} {term_nt(t.p)} {term_nt(t.o)} )>>"
    raise TypeError(t)


def to_nt(statements) -> str:
    """N-Triples, or N-Quads if any statement is in a named graph."""
    lines = []
    for st in statements:
        parts = [term_nt(st.s), term_nt(st.p), term_nt(st.o)]
        if st.g is not None:
            parts.append(term_nt(st.g))
        lines.append(" ".join(parts) + " .\n")
    return "".join(lines)


TOKEN = re.compile(
    r"""\s*(?:
      (?P<open><<\()
    | (?P<close>\)>>)
    | (?P<iri><[^<>\s]*>)
    | (?P<bnode>_:[A-Za-z0-9_.-]+)
    | (?P<lit>"(?:[^"\\]|\\.)*")(?:@(?P<lang>[a-zA-Z]+(?:-[a-zA-Z0-9]+)*)(?:--(?P<dir>ltr|rtl))?|\^\^(?P<dt><[^>]*>))?
    | (?P<dot>\.)
    )""",
    re.X,
)


def unescape(s: str) -> str:
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "r": "\r"}.get(m[1], m[1]), s)


def from_nt(text: str):
    """Parse the N-Triples or N-Quads written by to_nt (not a general parser)."""
    out = []
    for line in text.splitlines():
        tokens = []
        pos = 0
        while pos < len(line):
            m = TOKEN.match(line, pos)
            if not m or m.end() == pos:
                raise SyntaxProblem(f"cannot parse: {line[pos:]!r}")
            tokens.append(m)
            pos = m.end()
        it = iter(tokens)

        def term(m):
            if m["iri"]:
                return Iri(m["iri"][1:-1])
            if m["bnode"]:
                return Bnode(m["bnode"][2:])
            if m["lit"]:
                lex = unescape(m["lit"][1:-1])
                return Lit(lex, m["dt"][1:-1] if m["dt"] else None, m["lang"], m["dir"])
            if m["open"]:
                s, p, o = term(next(it)), term(next(it)), term(next(it))
                if not next(it)["close"]:
                    raise SyntaxProblem("triple term not closed")
                return Triple(s, p, o)
            raise SyntaxProblem(f"unexpected token {m[0]!r}")

        terms = []
        for m in it:
            if m["dot"]:
                break
            terms.append(term(m))
        out.append(St(*terms))
    return out


# --- equivalence ---------------------------------------------------------------


def equivalent(a, b) -> Optional[str]:
    """Compare two lists of statements: same statements, in the same order, with a
    bijection between their blank node labels.

    Returns None if equivalent, or a description of the first difference.
    """
    if len(a) != len(b):
        return f"{len(a)} statements != {len(b)} statements"
    same = BnodeMap().same
    for i, (x, y) in enumerate(zip(a, b)):
        if (x.g is None) != (y.g is None):
            return f"statement {i}: {x} != {y}"
        terms = [(x.s, y.s), (x.p, y.p), (x.o, y.o)]
        if x.g is not None:
            terms.append((x.g, y.g))
        if not all(same(u, v) for u, v in terms):
            return f"statement {i}: {x} != {y}"
    return None


def equivalent_result(a, b, messages: bool) -> Optional[str]:
    """Like equivalent, for a whole stream. In a stream of RDF Messages, the blank
    node labels are scoped to one message, so each message has its own bijection."""
    if not messages:
        return equivalent(a, b)
    if len(a) != len(b):
        return f"{len(a)} messages != {len(b)} messages"
    for i, (x, y) in enumerate(zip(a, b)):
        diff = equivalent(x, y)
        if diff:
            return f"message {i}: {diff}"
    return None
