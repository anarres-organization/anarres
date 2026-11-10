# Performance

Anarres measures the paths users invoke rather than isolated implementation
details. The performance suite covers native startup, qualification and
validation, adapter discovery, protocol inspection, and status commands for all
maintained domain adapters.

Run the suite against a release build:

```console
$ make setup
$ cargo build --release --locked -p anarres-cli
$ make benchmark
```

The benchmark performs warmup runs, collects repeated wall-clock samples, and
writes a versioned JSON report to `target/benchmarks/cli.json`. Every scenario
must produce byte-identical output across samples. The report records the Git
revision, binary size, platform, architecture, Python version, sample count,
median latency, p95 latency, and minimum latency.

The default p95 limits are broad regression guards, not cross-machine
performance claims. Shared CI runners, operating systems, filesystems, power
states, and background work can materially affect short-process measurements.
Compare changes on the same quiet machine with the same release build and
benchmark parameters. Use a profiler after a representative command shows a
repeatable regression.

The native binary owns startup-sensitive shared operations such as routing,
hashing, validation, and deterministic serialization. Domain adapters remain in
their native scientific ecosystems until profiling shows that a stable shared
hot path would benefit from a native implementation. Any migration must retain
cross-language conformance tests and the versioned record boundary described in
[RFC 0001](rfcs/0001-native-cli.md).
