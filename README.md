# jelly-protobuf

Protocol Buffers and gRPC specifications for the Jelly RDF serialization format and gRPC streaming protocol.

- `rdf.proto` – the RDF Protocol Buffers serialization only. Use this if you don't plan on using Jelly's gRPC protocol.
- `grpc.proto` – Jelly's gRPC protocol service specifications.

**[See the protocol specification on the website](https://w3id.org/jelly/dev/specification/)**

**[More information about Jelly](https://w3id.org/jelly/)**

## Usage

The `rdf.proto` and `grpc.proto` files define the Jelly RDF serialization and the gRPC pub/sub service, respectively. They use the [proto 3](https://protobuf.dev/programming-guides/proto3/) language and can be used with protoc or any other compatible tool. See the [Protocol Buffers documentation](https://protobuf.dev/) for more details.

## Contributing

See the [contribution guide on the Jelly website](https://w3id.org/jelly/dev/contributing/).

## Versioning

This protocol follows the [Semantic Versioning 2.0 scheme](https://semver.org/). The current major version is 1, and backward compatibility with it will be kept in future 1.x.y versions.

The version of the protocol is embedded into all Jelly files/messages. See the [protocol specification](https://w3id.org/jelly/dev/specification/serialization/#versioning) for more details.

### Releases

The `dev` release tag corresponds to the main branch in the repository and is updated automatically after every push to this branch.

Tagged (versioned) releases are created manually. **Before making a tagged release, be sure to update all mentions of the protocol version in `.proto` files.** To create a new tagged release (example for version 1.2.3):

```shell
git checkout main
git pull
git tag v1.2.3
git push origin v1.2.3
```

The rest (packaging and release creation) will be handled automatically by the CI.

## License

The contents of this repository are licensed under the [Apache 2.0 license](https://www.apache.org/licenses/LICENSE-2.0).
