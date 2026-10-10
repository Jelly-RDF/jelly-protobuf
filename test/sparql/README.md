# Jelly-SPARQL test suite

This directory contains the conformance tests for the [Jelly SPARQL results format specification](https://w3id.org/jelly/dev/specification/sparql/) (Jelly-SPARQL).

The test categories and instructions for running the tests are on the [Jelly-SPARQL test cases](https://w3id.org/jelly/dev/conformance/sparql-test-cases/) page.

> [!WARNING]
> Jelly-SPARQL is an experimental draft, and so is this test suite. Both may change.

## Structure

- `from_jelly/` – parse tests (`jellyt:TestSparqlFromJelly`), with a `manifest.ttl`.
- `to_jelly/` – serialize tests (`jellyt:TestSparqlToJelly`), with a `manifest.ttl`.
- `generator/` – the script that writes all of the above. **Do not edit the test files by hand.**

The manifests use the vocabulary in [`../test-manifest.yaml`](../test-manifest.yaml). Every test links the rule of the specification it exercises with `rdfs:seeAlso`.

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
