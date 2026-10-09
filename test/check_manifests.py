#!/usr/bin/env python3
"""Checks the test case manifests (test/*/*/manifest.ttl).

Usage:

    python3 test/check_manifests.py <SHACL shapes file or directory>

The SHACL shapes are generated from test-manifest.yaml with linkml-scala.
They check each test case on its own, and this script runs them with pyshacl.
Then it checks what the shapes cannot:

- the RDF lists in mf:entries, mf:action and mf:result,
- that every test case is in the mf:entries of its manifest, and every test
  case directory has a test case,
- that every file referenced by mf:action or mf:result exists.

Requires pyshacl (pip install pyshacl).
"""

import re
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, BNode, Graph, Namespace, URIRef

TEST_DIR = Path(__file__).resolve().parent
BASE = 'https://w3id.org/jelly/dev/tests/'
MF = Namespace('http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#')
JELLYT = Namespace('https://w3id.org/jelly/dev/tests/vocab#')

# Kind of test -> (whether mf:action is a list, whether mf:result is a list).
# None means that both one file and a list of files are allowed.
KINDS = {
    JELLYT.TestRdfToJelly: (True, False),
    JELLYT.TestRdfFromJelly: (False, True),
    JELLYT.TestSparqlToJelly: (True, False),
    JELLYT.TestSparqlFromJelly: (False, None),
}
OUTCOMES = {JELLYT.TestPositive: 'pos', JELLYT.TestNegative: 'neg'}
CASE_DIR = re.compile(r'(pos|neg)_\d+')


class CheckError(Exception):
    pass


def short(node) -> str:
    """The IRI without the common base, to keep the messages short."""
    return str(node).removeprefix(BASE)


def read_list(g: Graph, node) -> list:
    """The elements of an RDF list. Raises CheckError if it is malformed."""
    items = []
    seen = set()
    while node != RDF.nil:
        if not isinstance(node, BNode):
            raise CheckError(f'expected an RDF list, found {short(node)}')
        if node in seen:
            raise CheckError('the RDF list has a cycle')
        seen.add(node)
        first = list(g.objects(node, RDF.first))
        rest = list(g.objects(node, RDF.rest))
        if len(first) != 1 or len(rest) != 1:
            raise CheckError('malformed RDF list')
        items.append(first[0])
        node = rest[0]
    return items


def read_files(g: Graph, node, is_list: bool | None) -> list:
    """The file IRIs of a mf:action or mf:result value."""
    if isinstance(node, URIRef) and is_list is not True:
        return [node]
    if is_list is False:
        found = 'a list' if isinstance(node, BNode) else node
        raise CheckError(f'expected one file IRI, found {found}')
    files = read_list(g, node)
    if not files:
        raise CheckError('the list of files is empty')
    for f in files:
        if not isinstance(f, URIRef):
            raise CheckError(f'expected a file IRI, found {f}')
    return files


def check_test(g: Graph, test, kind) -> list[str]:
    """Checks the action and result of one test case."""
    errors = []
    action_is_list, result_is_list = KINDS[kind]
    for prop, is_list in ((MF.action, action_is_list),
                          (MF.result, result_is_list)):
        for value in g.objects(test, prop):
            try:
                files = read_files(g, value, is_list)
            except CheckError as e:
                errors.append(f'{prop.fragment}: {e}')
                continue
            if prop == MF.action and is_list and len(files) < 2:
                errors.append('action: the list must have the stream options '
                              'and at least one input file')
            for f in files:
                if not str(f).startswith(BASE):
                    errors.append(f'{prop.fragment}: {f} is not under {BASE}')
                elif not (TEST_DIR / short(f)).is_file():
                    errors.append(f'{prop.fragment}: file not found: '
                                  f'test/{short(f)}')
    return errors


def check_manifest(path: Path) -> list[str]:
    """Checks one manifest, apart from the SHACL shapes."""
    g = Graph().parse(path)
    errors = []

    manifests = list(g.subjects(RDF.type, MF.Manifest))
    if len(manifests) != 1:
        return [f'expected one mf:Manifest, found {len(manifests)}']
    entries = []
    for value in g.objects(manifests[0], MF.entries):
        try:
            entries = read_list(g, value)
        except CheckError as e:
            errors.append(f'mf:entries: {e}')
    entry_set = set(entries)
    if len(entry_set) != len(entries):
        errors.append('mf:entries lists some test cases more than once')

    tests = {t for kind in KINDS for t in g.subjects(RDF.type, kind)}
    tests |= {t for o in OUTCOMES for t in g.subjects(RDF.type, o)}
    for t in sorted(tests - entry_set):
        errors.append(f'{short(t)}: not in mf:entries of the manifest')
    for t in sorted(entry_set - tests):
        errors.append(f'{short(t)}: in mf:entries, but not a test case')

    for t in sorted(tests):
        types = set(g.objects(t, RDF.type))
        kinds = types & KINDS.keys()
        outcomes = types & OUTCOMES.keys()
        if len(kinds) != 1:
            errors.append(f'{short(t)}: must have exactly one test kind '
                          f'({", ".join(k.fragment for k in KINDS)})')
        if len(outcomes) != 1:
            errors.append(f'{short(t)}: must be exactly one of TestPositive '
                          'and TestNegative')
        elif (m := CASE_DIR.fullmatch(t.split('/')[-1])) and \
                m[1] != OUTCOMES[outcomes.pop()]:
            errors.append(f'{short(t)}: the name does not match the class '
                          '(TestPositive or TestNegative)')
        if len(kinds) == 1:
            errors += [f'{short(t)}: {e}'
                       for e in check_test(g, t, kinds.pop())]

    # Every test case directory must have a test case in this manifest.
    for d in sorted(path.parent.glob('*/*')):
        if d.is_dir() and CASE_DIR.fullmatch(d.name):
            iri = URIRef(BASE + d.relative_to(TEST_DIR).as_posix())
            if iri not in tests:
                errors.append(f'{short(iri)}: directory without a test case')
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    shapes_path = Path(sys.argv[1])
    shapes = Graph()
    for f in ([shapes_path] if shapes_path.is_file()
              else sorted(shapes_path.glob('*.ttl'))):
        shapes.parse(f)
    if len(shapes) == 0:
        print(f'No SHACL shapes found in {shapes_path}')
        return 2

    failed = False
    manifests = sorted(TEST_DIR.glob('*/*/manifest.ttl'))
    for path in manifests:
        name = path.relative_to(TEST_DIR.parent)
        conforms, _, report = validate(Graph().parse(path),
                                       shacl_graph=shapes)
        errors = check_manifest(path)
        if conforms and not errors:
            print(f'OK    {name}')
            continue
        failed = True
        print(f'FAIL  {name}')
        if not conforms:
            print(report)
        for e in errors:
            print(f'  {e}')
    print(f'Checked {len(manifests)} manifests.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
