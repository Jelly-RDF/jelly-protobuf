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
  - *TODO... will need to specify the options for the Jelly serializer. Also, there is freedom in how to compress the Jelly files.*
  - *Should this use an oracle to check the correctness of the Jelly files?*
