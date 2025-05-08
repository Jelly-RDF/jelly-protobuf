TODO: replace this with manifests

## Positive cases

- `pos_001` – single frame (delimited), a set of quads with all possible graph label terms: default graph, IRI, blank node.
- `pos_002` - single frame (delimited), a set of quads with all valid RDF 1.1 terms. 
- `pos_003` - single frame (delimited), a set of quads with repeated terms, including graph label (multiple repeated triples in one graph sent in order). 
- `pos_004` - 3 frames, a set of quads with repeated terms and graph names spanning multiple frames.
- `pos_005` - 3 frames, same as `pos_004` but with the prefix table enabled. 
- `pos_006` - one graph per frame (3 frames)
- `pos_007` - one graph across multiple (3) frames
- `pos_008` - 4 graphs over 3 frames in sequence re-using all 3 lookup tables.

## Negative cases

- `neg_001` - 3 frames, a quad row is present (data from `pos_006`)