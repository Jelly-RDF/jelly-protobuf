# Jelly-RDF test suite

This directory contains the tests for the [Jelly RDF serialization format specification](https://w3id.org/jelly/dev/specification/serialization/) (Jelly-RDF).

- `from_jelly` – converting Jelly files into N-Triples/N-Quads.
  - Test cases beginning with `pos_` are positive tests, and those beginning with `neg_` are negative tests.
  - Jelly files in the suite by default use the delimited format (`in.jelly`). Non-delimited Jelly files have names equal to `in_nd.jelly`.
  - TRIPLES stream type:
    - `triples_rdf_1_1` – RDF 1.1 standard conformant.
    - `triples_rdf_1_1_generalized` – RDF 1.1 with generalized statements.
    - `triples_rdf_star` – RDF-star conformant.
    - `triples_rdf_star_generalized` – RDF-star with generalized statements.
  - QUADS stream type:
    - `quads_rdf_1_1` – RDF 1.1 standard conformant.
    - `quads_rdf_1_1_generalized` – RDF 1.1 with generalized statements.
    - `quads_rdf_star` – RDF-star conformant.
    - `quads_rdf_star_generalized` – RDF-star with generalized statements.

- `to_jelly` – converting N-Triples/N-Quads into Jelly files.
  - expected stream options for producer are provided for each test case in the stream_options.jelly file
  - tests use jelly-cli rdf validate (oracle) together with original file to encode and expected stream options

  - TRIPLES stream type:
    - `triples_rdf_1_1` – RDF 1.1 standard conformant.
  
[NOTES]: 
1. Generalized RDF test cases (`*_generalized`) require a generalized parser. If the library does not implement generalized RDF, then the generalized RDF tests should be skipped
2. All tests must be run with --compare-to-rdf-file=true option in jelly-cli rdf validate
