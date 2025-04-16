TODO: replace this with manifests

## Positive cases

- `pos_001` – a set of three triples with only IRIs as terms. Stream options are: generalized-statements=false, rdf-star=false, max-name-table-size=8, max-prefix-table-size=0, max-datatype-table-size=0.
- `pos_002` - a triple with a simple literal (no langtag, no datatype). Stream options are the same as `pos_001`
- `pos_003` - a triple with a literal and a datatype tag. Stream options are: generalized-statements=false, rdf-star=false, max-name-table-size=8, max-prefix-table-size=0, max-datatype-table-size=4.
- `pos_004` - a triple with a literal and a lang tag. Stream options are the same as `pos_001`
- `pos_005` - a triple with a blank node in subject. Stream options are the same as `pos_001`
- `pos_006` - a triple with a blank node in object. Stream options are the same as `pos_001`
- `pos_007` - a triple with an integer with a string datatype. Stream options are the same as `pos_001`

## Negative cases

TODO: include info in the manifest on why and how should the producer fail
