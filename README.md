# jelly-protobuf

Protocol Buffers and gRPC specifications for the Jelly protocol.

- `rdf.proto` – the RDF Protocol Buffers serialization only. Use this if you don't plan on using Jelly's gRPC protocol.
- `grpc.proto` – Jelly's gRPC protocol service specifications.

**[See the protocol specification on the website](https://jelly-rdf.github.io/latest/specification/)**

**[More information about Jelly](https://jelly-rdf.github.io/latest/)**

## Usage

The protocol is not stable yet and may change before the initial (1.0.0) release. Expect a first stable release in Q4 2023.

The `rdf.proto` and `grpc.proto` files define the Jelly RDF serialization and the gRPC pub/sub service, respectively. They use the [proto 3](https://protobuf.dev/programming-guides/proto3/) language and can be used with protoc or any other compatible tool. See the [Protocol Buffers documentation](https://protobuf.dev/) for more details.

## Versioning

This protocol follows the [Semantic Versioning 2.0 scheme](https://semver.org/). The current major version is 1, and after it stabilizes, backward compatibility with it will be kept in future 1.x.y versions.

### Releases

The `dev` release tag corresponds to the main branch in the repository and is updated automatically.

Tagged (versioned) releases are created manually. To create a new tagged release (example for version 1.2.3):
```sh
git checkout main
git pull
git tag v1.2.3
git push origin v1.2.3
```

The rest (packaging and release creation) will be handled automatically by the CI.
