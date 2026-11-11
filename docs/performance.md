# Performance

Anarres measures the paths users invoke rather than isolated implementation
details. The performance suite covers native startup, qualification and
validation, adapter discovery, protocol inspection, descriptor startup, direct
adapter execution, and Rust-dispatched status commands for all maintained
domain adapters. The report derives the median dispatch overhead from the direct
and routed measurements.

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

The default limits are broad regression guards, not cross-machine performance
claims. Native paths use a p95 guard. Adapter paths spawn another process and
use a median guard because isolated scheduler delays can dominate their p95 on
shared runners; their p95 remains in the report for diagnosis. Operating
systems, filesystems, power states, and background work can materially affect
short-process measurements. Compare changes on the same quiet machine with the
same release build and benchmark parameters. Use a profiler after a
representative command shows a repeatable regression.

The release-binary guard is 2.25 MB so the same stripped source-runtime build
fits across supported object formats while still detecting material growth.

The native binary owns startup-sensitive shared operations such as routing,
hashing, validation, and deterministic serialization. Domain adapters remain in
their native scientific ecosystems until profiling shows that a stable shared
hot path would benefit from a native implementation. Any migration must retain
cross-language conformance tests and the versioned record boundary described in
[RFC 0001](rfcs/0001-native-cli.md).
