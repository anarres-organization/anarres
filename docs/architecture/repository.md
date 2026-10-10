# Repository architecture

Anarres is organized around four complementary layers.

## Packages

Packages contain reusable behavior with maintained interfaces. A package must have an owner, tests, and at least one real consumer. Anarres does not create empty packages for anticipated needs.

## Data

`data/` contains source adapters, qualification pipelines, and environment construction systems. Large datasets remain in external versioned stores.

## Experiments

`experiments/` organizes research by domain. Mathematics, agentic systems, cyber, AI for Science, and robotics can evolve independently while sharing maintained packages and schemas. Experiment directories own claim-specific analysis but do not become utility libraries.

## Schemas

Schemas are the stable boundaries that allow data systems, packages, and experiments to interoperate. Common provenance is universal. Environment, training, and evaluation contracts are composed only where relevant.

## Repository boundaries

Anarres begins as one primary monorepo. A component should be extracted only after developing an independent release cadence, contributor community, governance boundary, security boundary, or audience that does not otherwise depend on Anarres.

This design follows Marin's use of one research repository with shared implementation and an `experiments/` tree. It also follows LeRobot, OpenSpiel, and vLLM in retaining closely coupled environments, evaluation, benchmark tooling, and documentation in one repository.
