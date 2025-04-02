TODO: replace this with manifests

## Positive cases

- `pos_001` – single frame (delimited), a few basic triples. Prefix table enabled.
- `pos_002` – single frame (delimited), a few basic triples (same content as `pos_001`). Prefix table disabled.
- `pos_003` – single frame (non-delimited), a few basic triples (same content as `pos_001`). Prefix table enabled.

## Negative cases

TODO: include info in the manifest on why and how should the consumer fail

- `neg_001` – single frame (delimited), overly large name table (320_000).
- `neg_002` – single frame (delimited), overly large prefix table (320_000).
- `neg_003` – single frame (delimited), overly large datatype table (320_000).
- `neg_004` – single frame (delimited), unsupported version (3).
