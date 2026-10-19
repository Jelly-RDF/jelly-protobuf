#!/usr/bin/env python3
"""Generate the Jelly-RDF 1.2 conformance test suite.

Usage (from any directory):

    python3 test/rdf/v1_2/generator/generate.py          # (re)write the test files
    python3 test/rdf/v1_2/generator/generate.py --check  # verify the files are up to date

Before anything is written, every case is checked:

- positive "from Jelly" cases must decode, with the helper decoder, to the
  expected statements;
- negative "from Jelly" cases must fail in the helper decoder, for the
  reason given in the case;
- positive "to Jelly" cases are encoded with the helper encoder, and the
  output must decode back to the input with the requested stream options;
- negative "to Jelly" cases must fail in the helper encoder;
- every frame must be accepted by `protoc --decode` against rdf.proto (if
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
sys.path.insert(1, str(HERE.parents[2]))

import cases  # noqa: E402
import decoder  # noqa: E402
import encoder  # noqa: E402
import msgs  # noqa: E402
from generator_common import pb  # noqa: E402
from model import Iri, Lit, Messages, Triple, equivalent_result, from_nt, to_nt  # noqa: E402

SUITE = HERE.parent
PROTO_DIR = HERE.parents[3] / "proto"
SPEC = "https://w3id.org/jelly/dev/specification/"
BASE = "https://w3id.org/jelly/dev/tests/rdf/v1_2"
FRAME_TYPE = "eu.ostrzyciel.jelly.core.proto.v1.RdfStreamFrame"
ABSOLUTE_IRI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

PHYSICAL_REQUIREMENTS = {
    msgs.TRIPLES: "jellyt:requirementPhysicalTypeTriples",
    msgs.QUADS: "jellyt:requirementPhysicalTypeQuads",
}
VERSION_REQUIREMENTS = {
    "rdf_1_2_basic": "jellyt:requirementRdf12Basic",
    "rdf_1_2": "jellyt:requirementRdf12",
}
TITLES = {
    "from_jelly": "Jelly-RDF 1.2 test cases: from Jelly to RDF",
    "to_jelly": "Jelly-RDF 1.2 test cases: from RDF to Jelly",
}


class CaseError(Exception):
    pass


def check_protoc(frames, label):
    if shutil.which("protoc") is None:
        return
    for i, frame in enumerate(frames):
        data = frame.encode() if isinstance(frame, pb.Msg) else frame
        p = subprocess.run(
            ["protoc", f"-I{PROTO_DIR}", f"--decode={FRAME_TYPE}", str(PROTO_DIR / "rdf.proto")],
            input=data,
            capture_output=True,
        )
        if p.returncode != 0:
            raise CaseError(f"{label}: protoc rejects frame {i}: {p.stderr.decode().strip()}")


def input_bytes(case, label) -> bytes:
    if case.raw is not None:
        return case.raw
    check_protoc(case.frames, label)
    if not case.delimited:
        assert len(case.frames) == 1
        return case.frames[0].encode()
    return pb.delimited(case.frames)


def first_physical_type(data: bytes, delimited: bool):
    """The physical type in the stream options of the first frame, or None."""
    try:
        frames = pb.split_delimited(data) if delimited else [data]
        rows = pb.Fields(frames[0]).msgs(1)
        return rows[0].msg(1).uint32(2)
    except Exception:
        return None


def build_from_jelly(case, label):
    data = input_bytes(case, label)
    files = {"in.jelly": data}
    case.physical = first_physical_type(data, case.delimited)
    try:
        result, physical, stream_type = decoder.decode_stream(data, case.delimited)
    except decoder.DecodeError as e:
        if case.positive:
            raise CaseError(f"{label}: the helper decoder rejects a positive case: {e}")
        if case.error not in str(e):
            raise CaseError(f"{label}: fails for another reason than expected ({case.error!r}): {e}")
        return files
    if not case.positive:
        raise CaseError(f"{label}: the helper decoder accepts a negative case")
    messages = stream_type == msgs.MESSAGES
    if messages != isinstance(case.expected, Messages):
        raise CaseError(f"{label}: the expected result and the stream type do not match")
    diff = equivalent_result(case.expected, result, messages)
    if diff:
        raise CaseError(f"{label}: decoded result differs from the expected one: {diff}")
    for name, statements in result_files("out", case.expected, physical):
        files[name] = nt(statements, label)
    return files


def result_files(stem, result, physical):
    """File names for the statements of a FLAT stream, or of each RDF Message."""
    ext = "nq" if physical == msgs.QUADS else "nt"
    if isinstance(result, Messages):
        return [(f"{stem}_{i:03d}.{ext}", m) for i, m in enumerate(result)]
    return [(f"{stem}.{ext}", result)]


def build_to_jelly(case, label):
    files = {"stream_options.jelly": pb.delimited([msgs.frame(options=case.opts.msg())])}
    if case.opts.messages != isinstance(case.input, Messages):
        raise CaseError(f"{label}: the input and the stream type do not match")
    case.physical = case.opts.physical_type
    for name, statements in result_files("in", case.input, case.opts.physical_type):
        files[name] = nt(statements, label)
    try:
        frames = encoder.encode(case.input, case.opts, case.max_rows)
    except encoder.EncodeError as e:
        if case.positive:
            raise CaseError(f"{label}: the helper encoder rejects a positive case: {e}")
        if case.error not in str(e):
            raise CaseError(f"{label}: fails for another reason than expected ({case.error!r}): {e}")
        return files
    if not case.positive:
        raise CaseError(f"{label}: the helper encoder accepts a negative case")
    check_protoc(frames, label)
    data = pb.delimited(frames)
    diff = equivalent_result(case.input, decoder.decode(data), case.opts.messages)
    if diff:
        raise CaseError(f"{label}: the helper encoder's output does not decode to the input: {diff}")
    non_empty = [f for f in pb.split_delimited(data) if f]
    first = pb.Fields(non_empty[0]).msgs(1) if non_empty else []
    if len(first) != 1 or first[0].bytes(1) != case.opts.msg().encode():
        raise CaseError(f"{label}: the first non-empty frame of the helper encoder's output has other stream options than requested")
    files["out.jelly"] = data
    return files


def check_absolute_iris(statements, label):
    """Every IRI must be absolute: some libraries (e.g. RDF4J) cannot hold relative IRIs."""

    def walk(t):
        if isinstance(t, Iri):
            iris.append(t.value)
        elif isinstance(t, Lit) and t.datatype:
            iris.append(t.datatype)
        elif isinstance(t, Triple):
            walk(t.s), walk(t.p), walk(t.o)

    iris = []
    for st in statements:
        for t in (st.s, st.p, st.o, st.g):
            walk(t)
    relative = sorted({i for i in iris if not ABSOLUTE_IRI.match(i)})
    if relative:
        raise CaseError(f"{label}: relative IRIs in the result: {relative}")


def nt(statements, label) -> bytes:
    check_absolute_iris(statements, label)
    try:
        text = to_nt(statements)
    except Exception as e:
        raise CaseError(f"{label}: {e}")
    if equivalent_result(statements, from_nt(text), False):
        raise CaseError(f"{label}: the N-Triples / N-Quads do not round-trip")
    return text.encode("utf-8")


def ttl_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def requirements(case):
    out = []
    if case.category == cases.MESSAGES:
        out.append("jellyt:requirementMessages")
        physical = case.physical
    else:
        physical = msgs.QUADS if case.category.startswith("quads") else msgs.TRIPLES
    out.append(PHYSICAL_REQUIREMENTS.get(physical, PHYSICAL_REQUIREMENTS[msgs.TRIPLES]))
    for suffix, req in VERSION_REQUIREMENTS.items():
        if case.category.endswith(suffix):
            out.append(req)
            break
    return out


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

    test_class = "jellyt:TestRdf12FromJelly" if direction == "from_jelly" else "jellyt:TestRdf12ToJelly"
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
        page, anchor = case.see.split("#") if "#" in case.see else ("serialization", case.see)
        lines.append(f"    rdfs:seeAlso <{SPEC}{page}/#{anchor}> ;")
        lines.append("    rdft:approval rdft:Proposed ;")
        for req in requirements(case):
            lines.append(f"    mf:requires {req} ;")
        if case.should:
            lines.append("    mf:notable jellyt:featureShouldLevel ;")
        if not case.delimited:
            lines.append("    mf:notable jellyt:featureNonDelimited ;")
        if direction == "from_jelly":
            lines.append(f"    mf:action <{path}/in.jelly>" + (" ;" if case.positive else " ."))
            if case.positive:
                outs = [name for name, _ in result_files("out", case.expected, case.physical)]
                if isinstance(case.expected, Messages):
                    lines.append("    mf:result (")
                    lines += [f"        <{path}/{name}>" for name in outs]
                    lines.append("    ) .")
                else:
                    lines.append(f"    mf:result <{path}/{outs[0]}> .")
        else:
            lines.append("    mf:action (")
            lines.append(f"        <{path}/stream_options.jelly>")
            lines += [f"        <{path}/{name}>"
                      for name, _ in result_files("in", case.input, case.opts.physical_type)]
            lines.append("    )" + (" ;" if case.positive else " ."))
            if case.positive:
                lines.append(f"    mf:result <{path}/out.jelly> .")
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
