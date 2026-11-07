# Cyber environment utility

Anarres studies how the training environment changes a model's improvement on
a specified target at a fixed interaction budget. In cyber, that question has
two workstreams with different tasks, verifiers, and outcomes.

| Workstream | Training experience and target | Current stage |
| --- | --- | --- |
| [Formal verification](formal-verification/README.md) | Executable proof development and verified software, with machine-checked outcomes and held-out proof or specification targets | Source and harness qualification |
| [Vulnerability exploitation](qualification/README.md) | Authorized exploit-generation tasks, with strict proof-of-concept verification on isolated targets | Benchmark and warm-start qualification |

Both workstreams measure candidate environments under a fixed starting policy,
then test whether those measurements predict held-out improvement after
training. Task identity, agent-visible context, tools, verifier behavior,
generated cost, and infrastructure validity belong to each environment
contract. Native proof-checker outcomes and exploit-verifier outcomes remain
separate.

## Formal verification

The [experiment plan](formal-verification/EXPERIMENT_PLAN.md) compares
environment distributions for Lean proof completion, repository-context
verification, and specification construction. It includes a cryptographic
software slice and uses production-scale verification as a frontier reference.
Source pinning, chronology-correct tasks, checker-integrity tests, and a
frozen-policy measurement pass precede any downstream training. The
[source landscape](formal-verification/SOURCE_LANDSCAPE.md) records each public
artifact's proposed role and remaining qualification work.

## Vulnerability exploitation

The [qualification protocol](qualification/README.md) defines the first
CyberGym study, including task partitioning, containment, fixture checks, and
the warm-start measurement gate. A
[development summary](qualification/CYBER_QUALIFICATION_SUMMARY.md) records
earlier CyberGym probes. Under one compatible agent scaffold, Feyospace
completed 6 of 50 single-attempt tasks; a separate 50-task, eight-attempt
sweep found mixed outcomes on 13 tasks. Those measurements show that the
scaffold and repeated policy responses matter. They do not measure downstream
RL utility or qualify a different starting model by themselves.

The [earlier research plan](HISTORICAL_VULNERABILITY_PLAN.md) describes
additional benchmark families and possible external targets. The current
qualification protocol determines which source and target can enter the first
controlled training comparison.
