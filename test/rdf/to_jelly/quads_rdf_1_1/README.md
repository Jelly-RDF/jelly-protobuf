TODO: replace this with manifests

## Positive cases

- `pos_001` – a set of quads with all possible graph label terms: default graph, IRI, blank node. Stream options are: generalized-statements=false, rdf-star=false, max-name-table-size=8, max-prefix-table-size=0, max-datatype-table-size=0.
- `pos_002` - a set of quads with all valid RDF 1.1 terms. Stream options from `pos_001`.
- `pos_003` - a set of quads with repeated terms, including graph label. Stream options from `pos_001`.
- `pos_004` - a set of quads with repeated terms and graph names spanning multiple frames. Stream options from `pos_001`. 10 rows per frame. 
- `pos_005` - same as `pos_004` but with the prefix table enabled and max size = 4. 15 rows per frame. 

## Negative cases

TODO: include info in the manifest on why and how should the producer fail


