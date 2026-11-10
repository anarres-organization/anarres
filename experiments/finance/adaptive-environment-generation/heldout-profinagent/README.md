# Frozen ProFinAgent component test

This holdout tests whether the adaptive finance representation transfers to a
professional finance agent assembled independently of the development bridge.
ProFinAgent combines a 53-tool Financial Tool Universe, directed-acyclic-graph
planning, and case-based memory on 528 expert-designed questions across four
financial task families.

The paper abstract and method summary identify the components and report an
aggregate comparison with prior systems. The detailed component ablations,
per-task tables, and repository result artifacts had not been opened when
[`PREDICTIONS.json`](PREDICTIONS.json) was serialized. The freeze therefore
tests component-level directions rather than the aggregate claim already
stated in the abstract.

Predictions remain unscored when the paper does not report the corresponding
matched comparison. Accuracy and latency are scored separately, and no
prediction is revised after result extraction.
