# AI for Science

The AI for Science program studies how training-environment choice shapes model
improvement on explicitly named scientific objectives. It asks which
environments help a particular starting model improve at a fixed compute budget,
and whether measurements made before post-training can support that choice.

Environment measurement in this domain must account for domain-specific rewards,
uncertainty, provenance, and experimental validity. These properties remain
explicit parts of the training and evaluation contract.

AI for Science is an umbrella rather than a single experimental domain. The
first planned study is [molecular design](molecular-design/README.md), where the
policy constructs molecular graphs through valid reaction actions and the
target objective is measured on a frozen protein-target evaluation. Later
studies may examine scientific tool use, biological sequence models, or other
scientific systems under separate domain-specific contracts.

The shared utility object is

\[
U(E,\pi_0,C,D)=P(\pi_{E,C};D)-P(\pi_0;D),
\]

where \(E\) is a training environment, \(\pi_0\) is the starting policy, \(C\)
is the compute budget, and \(D\) is the target scientific objective. An
environment that is useful for one target, model, or budget need not be useful
for another.
