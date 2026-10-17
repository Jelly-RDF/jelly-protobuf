# Jelly-RDF test suite

This directory contains the tests for the [Jelly RDF serialization format specification](https://w3id.org/jelly/dev/specification/serialization/) (Jelly-RDF), in two test suites:

- `v1_2/` – tests for Jelly-RDF 1.2 streams (version tag 3, the column layout). See the [Jelly-RDF test cases page](https://w3id.org/jelly/dev/conformance/rdf-test-cases/).
- `v1_1/` – tests for Jelly-RDF 1.0 and 1.1 streams (version tags 1 and 2, the row layout). See the [Jelly-RDF 1.1 test cases page](https://w3id.org/jelly/dev/conformance/rdf-1-1-test-cases/).

A Jelly-RDF 1.2 consumer must also read Jelly-RDF 1.0 and 1.1 streams, so the "from Jelly" tests of both suites apply to it.

## Jelly-RDF 1.2 suite

- `v1_2/from_jelly/` – parse tests (`jellyt:TestRdf12FromJelly`), with a `manifest.ttl`.
- `v1_2/to_jelly/` – serialize tests (`jellyt:TestRdf12ToJelly`), with a `manifest.ttl`.
- `v1_2/generator/` – the script that writes all of the above. **Do not edit the test files by hand.**

Every test links the rule of the specification it exercises with `rdfs:seeAlso`.

The generator needs only Python 3.9 or newer. `protoc` is optional – when it is installed, every frame is also checked against `rdf.proto`.

```shell
python3 test/rdf/v1_2/generator/generate.py          # rewrite the test files
python3 test/rdf/v1_2/generator/generate.py --check  # check that the files are up to date
```

Before writing anything, the generator checks every case with a reference decoder and encoder written from the specification (`v1_2/generator/decoder.py`, `v1_2/generator/encoder.py`, and the column code they share with the Jelly-SPARQL generator in [`../generator_common`](../generator_common)):

- A positive parse test must decode to its expected statements.
- A negative parse test must fail for the reason given in the case, not for some other one.
- The output of a positive serialize test must decode back to its input.

The cases are defined in [`v1_2/generator/cases.py`](v1_2/generator/cases.py). They are numbered in the order they appear there, per direction, category, and polarity, so add new cases at the end of their group.

## Jelly-RDF 1.1 suite

The tests in `v1_1/` were written by hand. Each of `v1_1/from_jelly/` and `v1_1/to_jelly/` has a `manifest.ttl`.
