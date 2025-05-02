TODO: replace this with manifests

NOTE: generalized RDF support is OPTIONAL.

## Positive cases

- `pos_001` - a set of quads that features all possible terms in any position. Stream options are generalized-statements=true, rdf-star=false, max-name-table-size=8 max-prefix-table-size=0, max-datatype-table-size=4.
- `pos_002` - a set of quads that features all possible terms in any position and repeated across one frame. Stream options are like `pos_001`. [TODO] 
- `pos_003` - a set of quads that features all possible terms in any position and repeated across multiple frames. Stream options are like `pos_001`. [TODO]
- `pos_004` - a set of quads that features all possible terms in any position and repeated across multiple frames, prefix table enabled (max-prefix-table-size=4). [TODO]