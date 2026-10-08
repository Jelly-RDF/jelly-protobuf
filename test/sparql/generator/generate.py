#!/usr/bin/env python3
"""Generate the Jelly-SPARQL conformance test suite.

Usage (from any directory):

    python3 test/sparql/generator/generate.py          # (re)write the test files
    python3 test/sparql/generator/generate.py --check  # verify the files are up to date

Before anything is written, every case is checked:

- positive "from Jelly" cases must decode, with the reference decoder, to the
  expected result;
- negative "from Jelly" cases must fail in the reference decoder, for the
  reason given in the case;
- positive "to Jelly" cases are encoded with the reference encoder, and the
  output must decode back to the input with the requested stream options;
- negative "to Jelly" cases must fail in the reference encoder;
- every frame must be accepted by `protoc --decode` against sparql.proto (if
  protoc is installed), to make sure the hand-written wire format matches the
  schema.

Requires only Python 3.9+. protoc is optional.
"""

import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))

import cases  # noqa: E402
import decoder  # noqa: E402
import encoder  # noqa: E402
import msgs  # noqa: E402
import pb  # noqa: E402
from model import AskResult, Iri, Lit, Triple, equivalent, from_srj, to_srj  # noqa: E402

SUITE = HERE.parent
PROTO_DIR = SUITE.parent.parent / "proto"
SPEC = "https://w3id.org/jelly/dev/specification/sparql/"
BASE = "https://w3id.org/jelly/dev/tests/sparql"
FRAME_TYPE = "eu.ostrzyciel.jelly.core.proto.v1.sparql.SparqlResultsFrame"
ABSOLUTE_IRI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

REQUIREMENTS = {
    cases.SELECT_1_2_BASIC: "jellyt:requirementRdf12Basic",
    cases.SELECT_1_2: "jellyt:requirementRdf12",
    cases.PUNCTUATED: "jellyt:requirementPunctuated",
}
TITLES = {
    "from_jelly": "Jelly-SPARQL test cases: from Jelly to SPARQL results",
    "to_jelly": "Jelly-SPARQL test cases: from SPARQL results to Jelly",
}


class CaseError(Exception):
    pass


def check_protoc(frames, label):
    if shutil.which("protoc") is None:
        return
    for i, frame in enumerate(frames):
        data = frame.encode() if isinstance(frame, pb.Msg) else frame
        p = subprocess.run(
            ["protoc", f"-I{PROTO_DIR}", f"--decode={FRAME_TYPE}", str(PROTO_DIR / "sparql.proto")],
            input=data,
            capture_output=True,
        )
        if p.returncode != 0:
            raise CaseError(f"{label}: protoc rejects frame {i}: {p.stderr.decode().strip()}")


def build_from_jelly(case, label):
    if case.raw is not None:
        data = case.raw
    else:
        check_protoc(case.frames, label)
        data = pb.delimited(case.frames)
    files = {"in.jellys": data}
    try:
        result = decoder.decode(data)
    except decoder.SparqlDecodeError as e:
        if case.positive:
            raise CaseError(f"{label}: the reference decoder rejects a positive case: {e}")
        if case.error not in str(e):
            raise CaseError(f"{label}: fails for another reason than expected ({case.error!r}): {e}")
        return files
    if not case.positive:
        raise CaseError(f"{label}: the reference decoder accepts a negative case")
    diff = equivalent_all(case.expected, result)
    if diff:
        raise CaseError(f"{label}: decoded result differs from the expected one: {diff}")
    for name, r in result_files("out", case.expected):
        files[name] = srj(r, label)
    return files


def result_files(stem, result):
    """File names for one result set (FLAT), or for a list of them (PUNCTUATED)."""
    if isinstance(result, list):
        return [(f"{stem}_{i:03d}.srj", r) for i, r in enumerate(result)]
    return [(f"{stem}.srj", result)]


def equivalent_all(expected, actual):
    """Like model.equivalent, for one result set or a list of them, also comparing links."""
    if isinstance(expected, list) != isinstance(actual, list):
        return "one is a sequence of result sets, the other is a single result set"
    if not isinstance(expected, list):
        expected, actual = [expected], [actual]
    if len(expected) != len(actual):
        return f"{len(expected)} result sets != {len(actual)} result sets"
    for i, (e, a) in enumerate(zip(expected, actual)):
        diff = equivalent(e, a)
        if diff:
            return f"result set {i}: {diff}"
        if not isinstance(e, AskResult) and e.links != a.links:
            return f"result set {i}: links {e.links} != {a.links}"
    return None


def build_to_jelly(case, label):
    files = {"stream_options.jellys": pb.delimited([msgs.frame(options=case.opts.msg())])}
    for name, r in result_files("in", case.input):
        files[name] = srj(r, label)
    try:
        frames = encoder.encode(case.input, case.opts, case.max_rows)
    except encoder.EncodeError as e:
        if case.positive:
            raise CaseError(f"{label}: the reference encoder rejects a positive case: {e}")
        if case.error not in str(e):
            raise CaseError(f"{label}: fails for another reason than expected ({case.error!r}): {e}")
        return files
    if not case.positive:
        raise CaseError(f"{label}: the reference encoder accepts a negative case")
    check_protoc(frames, label)
    data = pb.delimited(frames)
    diff = equivalent_all(case.input, decoder.decode(data))
    if diff:
        raise CaseError(f"{label}: the reference output does not decode to the input: {diff}")
    last = pb.Fields(pb.split_delimited(data)[-1]).msg(9)
    if last is None or last.string(1):
        raise CaseError(f"{label}: the last frame of the reference output has no trailer, or an error trailer")
    first_options = pb.Fields(pb.split_delimited(data)[0]).bytes(1)
    if first_options != case.opts.msg().encode():
        raise CaseError(f"{label}: the reference output has other stream options than requested")
    files["out.jellys"] = data
    return files


def check_absolute_iris(result, label):
    """Every IRI must be absolute: some libraries (e.g. RDF4J) cannot hold relative IRIs."""
    if isinstance(result, list):
        for r in result:
            check_absolute_iris(r, label)
        return
    if isinstance(result, AskResult):
        return

    def walk(t):
        if isinstance(t, Iri):
            iris.append(t.value)
        elif isinstance(t, Lit) and t.datatype:
            iris.append(t.datatype)
        elif isinstance(t, Triple):
            walk(t.s), walk(t.p), walk(t.o)

    iris = list(result.links)
    for row in result.rows:
        for t in row.values():
            walk(t)
    relative = sorted({i for i in iris if not ABSOLUTE_IRI.match(i)})
    if relative:
        raise CaseError(f"{label}: relative IRIs in the result: {relative}")


def srj(result, label) -> bytes:
    check_absolute_iris(result, label)
    text = to_srj(result)
    if equivalent(result, from_srj(text)):
        raise CaseError(f"{label}: the SPARQL JSON results do not round-trip")
    return text.encode("utf-8")


def ttl_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def manifest(direction, entries) -> str:
    out = [
        "PREFIX jellyt: <https://w3id.org/jelly/dev/tests/vocab#>",
        "PREFIX mf:     <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#>",
        "PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>",
        "PREFIX rdft:   <http://www.w3.org/ns/rdftest#>",
        "",
        f"BASE           <{BASE}/{direction}/>",
        "",
        "# Generated by ../generator/generate.py – do not edit by hand.",
        "",
        "<manifest> a mf:Manifest ;",
        f"    rdfs:label {ttl_string(TITLES[direction])} ;",
        "    mf:entries (",
    ]
    category = None
    for case, path in entries:
        if case.category != category:
            if category is not None:
                out.append("")
            out.append(f"        # {case.category}")
            category = case.category
        out.append(f"        <{path}>")
    out += ["    ) .", ""]

    test_class = "jellyt:TestSparqlFromJelly" if direction == "from_jelly" else "jellyt:TestSparqlToJelly"
    for case, path in entries:
        polarity = "jellyt:TestPositive" if case.positive else "jellyt:TestNegative"
        lines = [f"<{path}> a {polarity}, {test_class} ;", f"    mf:name {ttl_string(case.name)} ;"]
        comments = []
        if direction == "to_jelly":
            comments.append(f"Stream options are: {case.opts.describe()}.")
        if case.comment:
            comments.append(case.comment)
        if comments:
            lines.append(f"    rdfs:comment {ttl_string(' '.join(comments))} ;")
        lines.append(f"    rdfs:seeAlso <{SPEC}#{case.see}> ;")
        lines.append("    rdft:approval rdft:Proposed ;")
        if case.category in REQUIREMENTS:
            lines.append(f"    mf:requires {REQUIREMENTS[case.category]} ;")
        if case.should:
            lines.append("    mf:notable jellyt:featureShouldLevel ;")
        if direction == "from_jelly":
            lines.append(f"    mf:action <{path}/in.jellys>" + (" ;" if case.positive else " ."))
            if case.positive:
                outs = [name for name, _ in result_files("out", case.expected)]
                if isinstance(case.expected, list):
                    lines.append("    mf:result (")
                    lines += [f"        <{path}/{name}>" for name in outs]
                    lines.append("    ) .")
                else:
                    lines.append(f"    mf:result <{path}/{outs[0]}> .")
        else:
            lines.append("    mf:action (")
            lines.append(f"        <{path}/stream_options.jellys>")
            lines += [f"        <{path}/{name}>" for name, _ in result_files("in", case.input)]
            lines.append("    )" + (" ;" if case.positive else " ."))
            if case.positive:
                lines.append(f"    mf:result <{path}/out.jellys> .")
        out += lines + [""]
    return "\n".join(out)


def build():
    """Build every file of the suite in memory: relative path -> bytes."""
    files = {}
    errors = []
    counters = defaultdict(int)
    entries = defaultdict(list)
    for direction in ("from_jelly", "to_jelly"):
        group = [c for c in cases.CASES if c.direction == direction]
        group.sort(key=lambda c: (cases.CATEGORIES.index(c.category), not c.positive))
        for case in group:
            key = (direction, case.category, case.positive)
            counters[key] += 1
            path = f"{case.category}/{'pos' if case.positive else 'neg'}_{counters[key]:03d}"
            label = f"{direction}/{path}"
            try:
                built = (build_from_jelly if direction == "from_jelly" else build_to_jelly)(case, label)
            except CaseError as e:
                errors.append(str(e))
                continue
            for name, data in built.items():
                files[f"{direction}/{path}/{name}"] = data
            entries[direction].append((case, path))
        files[f"{direction}/manifest.ttl"] = manifest(direction, entries[direction]).encode()
    return files, errors, entries


def main():
    check = "--check" in sys.argv[1:]
    files, errors, entries = build()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        print(f"\n{len(errors)} case(s) failed verification.", file=sys.stderr)
        sys.exit(1)

    on_disk = {
        str(p.relative_to(SUITE)): p
        for d in ("from_jelly", "to_jelly")
        for p in (SUITE / d).rglob("*")
        if p.is_file()
    }
    if check:
        stale = [p for p, data in files.items() if p not in on_disk or on_disk[p].read_bytes() != data]
        extra = [p for p in on_disk if p not in files]
        for p in stale:
            print(f"out of date: {p}", file=sys.stderr)
        for p in extra:
            print(f"not generated: {p}", file=sys.stderr)
        if stale or extra:
            sys.exit(1)
    else:
        for d in ("from_jelly", "to_jelly"):
            shutil.rmtree(SUITE / d, ignore_errors=True)
        for p, data in files.items():
            target = SUITE / p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    for direction, items in entries.items():
        pos = sum(1 for c, _ in items if c.positive)
        print(f"{direction}: {len(items)} cases ({pos} positive, {len(items) - pos} negative)")
    if shutil.which("protoc") is None:
        print("note: protoc not found, the wire format was not checked against the schema")


if __name__ == "__main__":
    main()
