# Schemas

Schemas are versioned contracts between data systems, packages, experiments, and external artifacts.

Schema identifiers are immutable. Backward-compatible clarification may update documentation, while a structural or semantic change creates a new schema version. Claim-bearing artifacts must record the exact schema identifier they use.

The first release uses JSON Schema for portability. High-volume records may use Parquet or Arrow while retaining equivalent metadata contracts.
