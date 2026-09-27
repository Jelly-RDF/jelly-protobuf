# Jelly-SPARQL test suite

This directory contains the conformance tests for the [Jelly SPARQL results format specification](https://w3id.org/jelly/dev/specification/sparql/) (Jelly-SPARQL).

> [!WARNING]
> Jelly-SPARQL is an experimental draft, and so is this test suite. Both may change.

## Structure

- `from_jelly/` – parse tests (`jellyt:TestSparqlFromJelly`). The input is a `.jellys` file. A positive test has the expected result as a `.srj` file; a negative test expects the implementation to report an error.
- `to_jelly/` – serialize tests (`jellyt:TestSparqlToJelly`). The input is a `stream_options.jellys` file (one frame with only the stream options set) and a `.srj` file. A positive test has one valid serialization as `out.jellys`; a negative test expects the implementation to report an error.
- `generator/` – the script that writes all of the above. **Do not edit the test files by hand.**

Each direction has a `manifest.ttl` using the vocabulary in [`../vocabulary.ttl`](../vocabulary.ttl). Every test links the rule of the specification it exercises with `rdfs:seeAlso`.

The tests are grouped into categories:

| Category | What it needs | Requirement |
| --- | --- | --- |
| `select_rdf_1_1` | solution sequences with IRIs, blank nodes, and literals | – |
| `ask` | boolean results | – |
| `select_rdf_1_2_basic` | literals with a base direction | `jellyt:requirementRdf12Basic` |
| `select_rdf_1_2` | triple terms | `jellyt:requirementRdf12` |

If your implementation does not support RDF 1.2, skip the tests with the corresponding `mf:requires`.

## Running the tests

- **From Jelly, positive:** read `in.jellys`. The test passes if reading succeeds and the result is equivalent to `out.srj`.
- **From Jelly, negative:** read `in.jellys`. The test passes if the implementation reports an error.

Tests marked with `mf:notable jellyt:featureShouldLevel` check a rule that the specification states with SHOULD, not MUST – for example, rejecting version tag 0, or rejecting lookup tables larger than the recommended defaults. An implementation may fail them and still conform, but it should document why.
- **To Jelly, positive:** serialize `in.srj` with the options from `stream_options.jellys`. The test passes if the output's first frame carries those options, and reading the output back gives a result equivalent to `in.srj`. Jelly-SPARQL is not byte-level canonical, so do not compare your output with `out.jellys` byte by byte – it is just one valid serialization.
- **To Jelly, negative:** the test passes if the implementation reports an error.

Two results are **equivalent** when:

- both are boolean results with the same value, or
- they have the same variables in the same order, the same number of solutions in the same order, and there is a bijection between their blank node labels under which the solutions are pairwise equal.

A simple literal and an `xsd:string` literal are the same term. Links (`head.link`) are not part of the comparison, but implementations that expose them can check them.

The `.srj` files use the SPARQL 1.2 form of the JSON format: `"its:dir"` for base directions and `{"type": "triple", ...}` for triple terms.

A stream that ends without a trailer is valid. Consumers should report such a stream as possibly truncated, but must not fail the positive tests that have no trailer.

## Regenerating

The generator needs only Python 3.9 or newer. `protoc` is optional; when it is installed, every frame is also checked against `sparql.proto`.

```shell
python3 test/sparql/generator/generate.py          # rewrite the test files
python3 test/sparql/generator/generate.py --check  # check that the files are up to date
```

Before writing anything, the generator checks every case with a reference decoder and encoder written from the specification (`generator/decoder.py`, `generator/encoder.py`):

- a positive parse test must decode to its expected result;
- a negative parse test must fail for the reason given in the case, not for some other one;
- the output of a positive serialize test must decode back to its input.

The cases are defined in [`generator/cases.py`](generator/cases.py). They are numbered in the order they appear there, per direction, category, and polarity, so add new cases at the end of their group.
