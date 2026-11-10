# Measurement conventions

Measurement conventions define the meaning of coordinates exported by domain
adapters. They complement the environment-profile schema, which defines how a
coordinate is transported, validated, and compared.

Each convention records:

- the domain and measurement scope
- the starting subject and required evidence
- the estimator and unit for each coordinate
- validity, missingness, and infrastructure rules
- its stability level and revision

New conventions begin at `development`. A convention becomes stable only after
it has multiple real producers, a demonstrated consumer, conformance tests, and
a documented migration policy. Adding a new convention does not require a Rust
CLI change. Changing the meaning of an existing coordinate requires a new
revision, and profiles with different revisions are incompatible by default.

The domain study remains the source of scientific truth. A profile exposes a
small, typed view of its measurements and references the native records by URI
and digest.

Current conventions:

- [Formal-verification grouped probe v1](formal-verification-grouped-probe-v1.md)
- [Legal policy-response measurement v1](legal-policy-response-v1.md)
- [Robotics episode probe v1](robotics-episode-probe-v1.md)
- [Materials residual audit v1](materials-residual-audit-v1.md)
- [Materials MLIP candidate measurement v1](materials-mlip-candidate-measurement-v1.md)
