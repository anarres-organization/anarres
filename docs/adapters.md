# Install and use domain adapters

The native `anarres` binary validates and compares versioned environment
records. Domain adapters are separate tools that translate released robotics,
legal, materials, molecular, finance, or formal-verification measurements into
those records without changing their scientific meaning.

Homebrew and the standalone installer provide the native binary. They do not
install every domain runtime. Install only the adapters needed for the studies
you intend to inspect.

## Install from a checkout

Clone the repository and install an adapter with
[`uv tool install`](https://docs.astral.sh/uv/guides/tools/). The repository's
workspace metadata resolves the shared Anarres packages from the checkout.

```bash
git clone https://github.com/anarres-organization/anarres.git
cd anarres

# Choose one or more adapters.
uv tool install ./data/formal-verification/vero
uv tool install ./experiments/robotics/environment-selection/prospective-cupid-can-v141
uv tool install ./packages/legal
uv tool install ./experiments/ai-for-science/materials-science/mlip-phonon-environment-selection/adapter
uv tool install ./experiments/ai-for-science/molecular-design/reaction-environment-selection
uv tool install ./packages/finance
```

If `uv` reports that its executable directory is not on `PATH`, run
`uv tool update-shell` and restart the shell.

Confirm what the native CLI can discover:

```bash
anarres adapter list
anarres adapter doctor legal
anarres legal status --repository .
```

The explicit `--repository` argument points the installed adapter to the
released evidence in the checkout. Adapter discovery never searches a checkout
or downloads scientific artifacts implicitly.

## What installation means

Installing an adapter makes a domain command available. It does not imply that
the domain has passed every scientific gate or that its measurements predict a
new training outcome.

| Adapter | Start here | Then inspect | Current released boundary |
| --- | --- | --- | --- |
| Formal verification | `anarres formal status --repository .` | `anarres formal qualification --repository .` | Negative grouped measurement plus a separate one-attempt support pass; containment requalification and RL remain blocked |
| Robotics | `anarres robotics status --repository .` | `anarres robotics can-results --repository .` | Can v1.4.1 candidate measurements and prospective result |
| Legal reasoning | `anarres legal status --repository .` | `anarres legal regressions --repository .` | SylloGym candidate profiles and a separate LAB regression report |
| Materials science | `anarres materials status --repository .` | `anarres materials results --repository .` | MLIP candidate measurements, frozen protocol, and scored prospective result |
| Molecular design | `anarres molecular status --repository .` | `anarres molecular verify --repository .` | Qualified Q07820 reaction-bank measurements; training outcomes remain sealed |
| Agentic finance | `anarres finance status --repository .` | `anarres finance decide <panel.json>` | Starting-policy qualification and released retrospective checks |

Use `status` to inspect the released stage, `profile` to export supported
candidate records, and `verify` to regenerate the adapter's maintained output.
Some adapters expose additional study-specific reports. Run
`anarres <adapter> --help` for their exact commands.

## Add another domain

An unlisted domain needs a versioned native measurement record and a small
adapter. The adapter preserves identifiers, failures, costs, coordinate
definitions, units, estimators, and artifact digests. It does not need to
reimplement the domain's science in Rust.

Start with the [adapter authoring guide](architecture/adapter-authoring.md) and
the [scientific preservation guide](architecture/scientific-preservation.md).
The native conformance path is:

```bash
anarres qualify candidate.profile-input.json
anarres measure candidate.profile-input.json --output candidate.profile.json
anarres validate candidate.profile-input.json candidate.profile.json
```

Two candidates can enter `anarres design` only when their domain, starting
subject, measurement contract, adapter revision, and coordinate definitions
match. Predictive claims require a separate outcome-bearing validation under
the originating study's contract.
