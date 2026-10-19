# Qualification power analysis

The initial utility pilot is designed to detect large environment contrasts, not
to validate a general forecasting law.

For a paired binary trained-versus-warm-start outcome, the planning
approximation is

\[
n \approx \frac{(z_{1-\alpha/2}+z_{1-\beta})^2 q}{\delta^2},
\]

where \(q\) is the fraction of task pairs with discordant outcomes and
\(\delta\) is the paired utility difference. With two-sided \(\alpha=0.05\),
80% power, and conservative planning value \(q=0.20\):

| Detectable difference | Independent target tasks required |
| ---: | ---: |
| 5 pp | 628 |
| 6 pp | 437 |
| 7 pp | 321 |
| 8 pp | 246 |
| 9 pp | 194 |
| 10 pp | 157 |

A 256-task target resolves approximately an 7.83-point paired difference under
these assumptions. The pilot therefore uses 8 points as its minimum meaningful
environment contrast. A later study intended to resolve 6 points requires at
least 437 independent target tasks under the same approximation.

Repeated responses from the same task do not count as additional independent
tasks. They can reduce response-level noise, but uncertainty remains clustered
by task. Two training seeds also do not characterize the population distribution
of training outcomes. Expansion consequently requires the contrast to have the
same sign in both seeds, exceed twice the observed median within-environment seed
gap, and have a paired task-cluster interval excluding zero.

The calculation is reproducible with `power_analysis.py`. The final analysis
uses the frozen paired task-cluster procedure rather than treating this normal
approximation as an inferential result.
