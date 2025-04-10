TODO: replace this with manifests

## Positive cases

- `pos_001` – single frame (delimited), a few basic triples. Prefix table enabled.
- `pos_002` – single frame (delimited), a few basic triples (same content as `pos_001`). Prefix table disabled.
- `pos_003` – single frame (non-delimited), a few basic triples (same content as `pos_001`). Prefix table enabled.
- `pos_004` – single frame (delimited), a few basic triples. Prefix table enabled (max size 4) and updated to re-use prefix ids.
- `pos_005` – single frame (delimited), a few basic triples. Prefix table disabled, name table size 16 and updated to re-use name ids.

## Negative cases

TODO: include info in the manifest on why and how should the consumer fail

- `neg_001` – single frame (delimited), overly large name table (320_000).
- `neg_002` – single frame (delimited), overly large prefix table (320_000).
- `neg_003` – single frame (delimited), overly large datatype table (320_000).
- `neg_004` – single frame (delimited), unsupported version (3).
- `neg_005` – single frame (delimited), RdfPrefixEntry rows exist when Prefix table disabled.
- `neg_006` – single frame (delimited), add prefix entries outside max prefix table size (content based on `pos_004`). 
- `neg_007` – single frame (delimited), reference prefix entries outside max prefix table size (content based on `pos_004`). 
- `neg_008` – single frame (delimited), add name entry outside max name table size (prefix table disabled, content based on `pos_005`).