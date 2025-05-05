TODO: replace this with manifests

## Positive cases

- `pos_001` – a set of three triples with only IRIs as terms. Stream options are: generalized-statements=false, rdf-star=false, max-name-table-size=8, max-prefix-table-size=0, max-datatype-table-size=0.
- `pos_002` - a triple with a simple literal (no langtag, no datatype). Stream options are the same as `pos_001`
- `pos_003` - a triple with a literal and a datatype tag. Stream options are: generalized-statements=false, rdf-star=false, max-name-table-size=8, max-prefix-table-size=0, max-datatype-table-size=4.
- `pos_004` - a triple with a literal and a lang tag. Stream options are the same as `pos_001`
- `pos_005` - a triple with a blank node in subject. Stream options are the same as `pos_001`
- `pos_006` - a triple with a blank node in object. Stream options are the same as `pos_001`
- `pos_007` - a triple with an integer with a string datatype. Stream options are the same as `pos_001`
- `pos_008` - a set of triples with extended Latin, Greek, Cyrillic, and other Unicode codepoints (covering 2, 3, and 4 bytes encoding). Stream options are the same as `pos_001`
- `pos_009` - a set of triples to test literal term equality (same values but different terms, no changes should be done to lexical forms or datatypes). Stream options are the same as `pos_001`
- `pos_010` - explicitly set logical type to LOGICAL_STREAM_TYPE_FLAT_TRIPLES. Stream options generalized-statements=false, rdf-star=false, max-name-table-size=8, max-prefix-table-size=0, max-datatype-table-size=0, opt.logical-type=FLAT_TRIPLES.
- `pos_011` - use three .nt files as three frames for serialization, triples contain terms referenced across frames. Stream options are the same as `pos_003`. Input files should be in order specified by the index in the file name, with each file being a separate stream frame.
- `pos_012` - set of triples with repeating IRIs, blank nodes and literals (including/excluding repeating datatype) (in s, p, and o with accordance to RDF 1.1). 
- `pos_013` - set of fully (!) repeating triples (same s, p, o). Stream options are the same as `pos_003`


## Negative cases

TODO: include info in the manifest on why and how should the producer fail
- `neg_001` - datatype lookup is disabled, but input data has typed literals. Stream options are: generalized-statements=false, rdf-star=false, max-name-table-size=8, max-prefix-table-size=0, max-datatype-table-size=0. 
- `neg_002` - name lookup maximum size set to 7 (less than the minimal requirement). Stream options are: generalized-statements=false, rdf-star=false, max-name-table-size=7, max-prefix-table-size=0, max-datatype-table-size=0.