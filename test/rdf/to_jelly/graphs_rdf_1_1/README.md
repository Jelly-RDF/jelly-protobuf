TODO: replace this with manifests

## Positive cases

- `pos_001` – a set of quads with all possible graph label terms: default graph, IRI, blank node. Stream options are: generalized-statements=false, rdf-star=false, max-name-table-size=8, max-prefix-table-size=0, max-datatype-table-size=4. 
- `pos_002` - a set of quads with all valid RDF 1.1 terms. Stream options from `pos_001`.
- `pos_003` - a set of quads with repeated terms, including graph label (multiple repeated triples in one graph sent in order). Stream options from `pos_001`.
- `pos_004` - a set of quads with repeated terms and graph names spanning multiple frames. Stream options from `pos_001`. 15 rows per frame. 
- `pos_005` - same as `pos_004` but with the prefix table enabled and max size = 4. 15 rows per frame. 
- `pos_006` - one graph per frame (3 frames). Stream options from `pos_001`. 15 rows per frame. 
- `pos_007` - one graph across multiple (3) frames. Stream options from `pos_001`. 15 rows per frame. 
- `pos_008` - 4 graphs over 3 frames in sequence re-using all 3 lookup tables. name-size=8, prefix-size=4, datatype-size=2. 15 rows per frame. 