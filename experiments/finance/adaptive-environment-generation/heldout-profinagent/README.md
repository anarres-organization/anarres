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

Table 5 and Figure 4 were extracted only after the freeze commit. Three of five
prediction families are correct. The full system exceeds DAG-only and CBM-only
variants in all nine reported model-by-complexity cells, and DAG execution is
faster than the sequential comparison. These three families contain 19 of 19
correct atomic directional checks.

Two predictions fail. Tool access produces its largest average gain on L1
retrieval rather than L2 or L3 work, and the complete system is best in every
reported accuracy cell. These misses narrow the representation: executable
support can dominate at the retrieval boundary, and resource-interaction
penalties cannot be assumed without a measured cost or accuracy tradeoff.

Accuracy and latency remain separate, and no prediction is revised after
result extraction. [`SCORE.json`](SCORE.json) contains the complete scoring
record.
