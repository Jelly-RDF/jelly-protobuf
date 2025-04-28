TODO: replace this with manifests

## Positive cases

- `pos_001` – a set of quads with all possible graph label terms: default graph, IRI, blank node. Stream options are: generalized-statements=false, rdf-star=false, max-name-table-size=8, max-prefix-table-size=0, max-datatype-table-size=0.
- `pos_002` - a set of quads with all valid RDF 1.1 terms. Stream options from `pos_001`.
- `pos_003` - a set of quads with repeated terms, including graph label. Stream options from `pos_001`.


## Negative cases

TODO: include info in the manifest on why and how should the producer fail
- `neg_001` – a set of quads with RDF 1.1 non-conformant terms for s, p, o, g. Stream options from `pos_001`.

