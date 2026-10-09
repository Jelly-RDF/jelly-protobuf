# Jelly test suite

Machine-readable test manifests are in the `manifest.ttl` file of each subdirectory. The manifests follow the vocabulary in the `vocabulary.ttl` file.

- `rdf` – tests for the [Jelly RDF serialization format specification](https://w3id.org/jelly/dev/specification/serialization/) (Jelly-RDF).
- `sparql` – tests for the [Jelly SPARQL results format specification](https://w3id.org/jelly/dev/specification/sparql/) (Jelly-SPARQL).
- `grpc` – tests for the [Jelly gRPC streaming protocol specification](https://w3id.org/jelly/dev/specification/streaming/) (Jelly-RDF gRPC).

## Manifest validation

The structure of the manifests is described by the LinkML schema in `manifest-schema.yaml`. CI generates SHACL shapes from it and runs `check_manifests.py`, which validates the manifests against the shapes. It also checks that every test case is listed in its manifest and that every referenced file exists. To run it locally, with [linkml-scala](https://github.com/NeverBlink-OSS/linkml-scala) and `pyshacl` installed:

```shell
mkdir -p build
linkml-scala generate shacl --to build/manifest-shapes.ttl test/manifest-schema.yaml
python3 test/check_manifests.py build/manifest-shapes.ttl
```
