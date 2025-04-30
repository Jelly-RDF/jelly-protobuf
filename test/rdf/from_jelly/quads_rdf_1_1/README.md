TODO: replace this with manifests

## Positive cases

- `pos_001` – single frame, a few basic triples in the default graph. Prefix table enabled.
- `pos_002` - single frame, a few triples in the default graph, and graph nodes as a BN and IRI. Prefix table disabled.
- `pos_003` - single frame, diverse quads with repeated terms in s, p, o, g. Prefix table disabled.
- `pos_004` - multiple frames (3), repeated terms across frames. Prefix table disabled.
- `pos_005` - multiple frames (3), repeated terms across frames. Prefix table enabled.

-`neg_001` - single frame, a "triple" row is in the stream.
-`neg_002` - single frame, a "graph_start" row is in the stream.
-`neg_003` - single frame, a "graph_end" row is in the stream.
