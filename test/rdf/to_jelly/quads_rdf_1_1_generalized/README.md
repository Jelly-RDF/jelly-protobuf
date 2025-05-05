TODO: replace this with manifests

NOTE: generalized RDF support is OPTIONAL.

## Positive cases

- `pos_001` - a set of quads that features all possible terms in any position. Stream options are generalized-statements=true, rdf-star=false, max-name-table-size=8 max-prefix-table-size=0, max-datatype-table-size=4.
- `pos_002` - a set of quads that features all possible terms in any position and repeated across one frame. Stream options are like `pos_001`.
- `pos_003` - a set of quads with terms repeated across multiple frames. Stream options are like `pos_001`. 10 rows per frame.
- `pos_004` - a set of quads with terms repeated across multiple frames, prefix table enabled (max-prefix-table-size=4). 10 rows per frame.
- `pos_005` - a set of quads with terms repeated across multiple frames, prefix table enabled (max-prefix-table-size=4), focusing on reusing all three lookup tables, max-datatype-table-size=2. 15 rows per frame.