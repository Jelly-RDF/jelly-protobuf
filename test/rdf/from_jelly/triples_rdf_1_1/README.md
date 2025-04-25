TODO: replace this with manifests

## Positive cases

- `pos_001` – single frame (delimited), a few basic triples. Prefix table enabled.
- `pos_002` – single frame (delimited), a few basic triples (same content as `pos_001`). Prefix table disabled.
- `pos_003` – single frame (non-delimited), a few basic triples (same content as `pos_001`). Prefix table enabled.
- `pos_004` – single frame (delimited), a few basic triples. Prefix table enabled (max size 4) and updated to re-use prefix ids.
- `pos_005` – single frame (delimited), a few basic triples. Prefix table disabled, name table size 16 and updated to re-use name ids.
- `pos_006` – single frame (delimited), a few basic triples (same content as `pos_005`). Prefix table disabled. Stream options are repeated 3 times in the stream (no differences)
- `pos_007` - single frame (delimited) with repeated terms, including multiple subsequent usages of the same term. Prefix table disabled.
- `pos_008` - multiple frames, repeated terms (whole triple) occur as the first row in the second frame. Prefix table disabled. NOTE: multiple frames tests assume reading frames strictly in order. Each frame has a separate .nt file to compare to.
- `pos_009` - multiple frames, datatypes and names defined in one frame and referenced in the subsequent frames, also requiring name table updates across frames. Prefix table disabled.

## Negative cases

TODO: include info in the manifest on why and how should the consumer fail

- `neg_001` – single frame (delimited), overly large name table (320_000).
- `neg_002` – single frame (delimited), overly large prefix table (320_000).
- `neg_003` – single frame (delimited), overly large datatype table (320_000).
- `neg_004` – single frame (delimited), unsupported version (3).
- `neg_005` – single frame (delimited), RdfPrefixEntry rows exist when prefix table is disabled.
- `neg_006` – single frame (delimited), prefix entries being added with IDs outside max prefix table size (content based on `pos_004`). 
- `neg_007` – single frame (delimited), prefix entries referenced with IDs outside max prefix table size (content based on `pos_004`). 
- `neg_008` – single frame (delimited), name entry being added with ID outside max name table size (prefix table disabled, content based on `pos_005`).
- `neg_009` – single frame (delimited), physical stream type is set to PHYSICAL_STREAM_TYPE_UNSPECIFIED (prefix table disabled, datatype table enabled (size 4), content based on `pos_001`).
- `neg_010` – single frame (delimited), physical stream type is set to PHYSICAL_STREAM_TYPE_TRIPLES, but a quad row is in the stream (prefix table disabled, datatype table enabled (size 4), content based on `pos_001`).
- `neg_011` – single frame (delimited), multiple stream options rows are in stream, max name table size changes from 8 to 10 to 20 (prefix table disabled, datatype table enabled (size 4), content based on `pos_005`).
- `neg_012` - single frame (delimited) repeated terms appear in the first term occurence, content based in `pos_007`.
- `neg_013` - single frame (delimited). Literal has datatype index set to 0. Datatype table enabled (size 4). 
