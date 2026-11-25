# Install and use domain adapters

The native `anarres` binary validates and compares versioned environment
records. Domain adapters are separate tools that translate released robotics,
legal, materials, molecular, finance, formal-verification, or vulnerability
sources and measurements into those records without changing their scientific
meaning.

Homebrew and the standalone installer provide the native binary. They do not
install every domain runtime. Install only the adapters needed for the studies
you intend to inspect.

## Install an adapter

Install only the adapter for the domain you need. Each released adapter can be
installed directly from tagged Anarres source with
[`uv tool install`](https://docs.astral.sh/uv/guides/tools/); cloning the
repository is not required. Install `uv` first using its
[official installation guide](https://docs.astral.sh/uv/getting-started/installation/)
if `uv --version` is unavailable.

```bash
# Example: install the legal adapter from the current CLI release.
uv tool install \
  'git+https://github.com/anarres-organization/anarres.git@anarres-cli-v0.4.1#subdirectory=packages/legal'

anarres adapter list
anarres adapter doctor legal
```

The install source for each maintained adapter is:

| Adapter | Tagged source subdirectory |
| --- | --- |
| `formal` | `data/formal-verification/vero` |
| `robotics` | `experiments/robotics/environment-selection/prospective-cupid-can-v141` |
| `legal` | `packages/legal` |
| `materials` | `experiments/ai-for-science/materials-science/mlip-phonon-environment-selection/adapter` |
| `molecular` | `experiments/ai-for-science/molecular-design/reaction-environment-selection` |
| `finance` | `packages/finance` |
| `vulnerability` | `packages/vulnerability` |

Replace `packages/legal` in the example with the required subdirectory. Keep
the release tag in the URL so the adapter source remains reproducible. Run
`uv tool update-shell` and restart the shell if `uv` reports that its executable
directory is not on `PATH`.

To reproduce released studies as well as use their adapter, clone the same tag
and install from the checkout:

```bash
git clone --branch anarres-cli-v0.4.1 --depth 1 \
  https://github.com/anarres-organization/anarres.git
cd anarres
uv tool install ./packages/legal
```

Confirm what the native CLI can discover:

```bash
anarres adapter list
anarres adapter doctor legal
anarres legal status --repository .
```

The explicit `--repository` argument points the installed adapter to the
released evidence in the checkout. Adapter discovery never searches a checkout
or downloads scientific artifacts implicitly.

## What each adapter can do

Installing an adapter makes a domain command available. It does not imply that
the domain's measurements have predicted a new training outcome.

| Adapter | Start here | Then inspect | Available now |
| --- | --- | --- | --- |
| Formal verification | `anarres formal status --repository .` | `anarres formal evidence --repository .`<br>`anarres formal qualification --repository .`<br>`anarres formal qualify-runtime --help` | Source qualification, model-free runtime qualification, and the released cross-source public evidence are available. Policy probing, containment requalification, and RL remain blocked. |
| Robotics | `anarres robotics status --repository .` | `anarres robotics can-results --repository .`<br>`anarres robotics square-results --repository .` | Can v1.4.1 candidate measurements and the released Can and Square prospective results |
| Legal reasoning | `anarres legal status --repository .` | `anarres legal regressions --repository .` | SylloGym candidate profiles and a separate LAB regression report |
| Materials science | `anarres materials status --repository .` | `anarres materials results --repository .` | Native OMat24 bank qualification, MLIP candidate measurements, and the scored prospective result |
| Molecular design | `anarres molecular status --repository .` | `anarres molecular acquisition-results --repository .` | Qualified Q07820 reaction-bank measurements and separate released acquisition-panel results |
| Agentic finance | `anarres finance status --repository .` | `anarres finance decide <panel.json>` | Starting-policy qualification and released retrospective checks |
| Vulnerability exploitation | `anarres vulnerability status` | [`anarres qualify <source>`](https://github.com/anarres-organization/anarres/tree/main/packages/vulnerability) | Sanitized CyberGym source qualification. Task execution and policy probing remain gated. |

All maintained adapters declare a native source format. After installing one,
use `anarres adapter doctor <name>` to inspect its exact contract, then run
`anarres init`, `anarres inspect`, and `anarres qualify`. These commands route
the native files without flattening their domain-specific structure.

For example, qualify an unchanged Harvey LAB checkout with the legal adapter:

```bash
git clone https://github.com/harveyai/harvey-labs.git /path/to/harvey-labs
anarres init /path/to/harvey-labs \
  --adapter legal \
  --revision git:<full-commit> \
  --license MIT
anarres inspect /path/to/harvey-labs
anarres qualify /path/to/harvey-labs
```

`inspect` confirms that the source is connected to an installed adapter. The
native layout is checked by `qualify`, which reports all invalid LAB task
specifications together rather than stopping at the first task.

Only the molecular adapter currently declares the portable `policy-probe`
capability. Its probe remains dry-run unless execution is requested explicitly.
The other adapters stop at source or runtime qualification in the shared path.
Study-specific execution commands retain their own completeness and safety
gates.

No maintained public native source currently runs from an upstream clone all
the way through `probe`, `measure`, and `design` without additional policy and
domain artifacts. The bundled `anarres demo` is the zero-setup end-to-end path;
the checked-in
[native source example](https://github.com/anarres-organization/anarres/tree/main/examples/environment-source)
exercises real adapter qualification.

Use `status` to inspect the released stage, `profile` to export supported
candidate records, and `verify` to regenerate the adapter's maintained output.
Some adapters expose additional study-specific reports. Run
`anarres <adapter> --help` for their exact commands.

## Add another domain

An unlisted domain needs a versioned native measurement record and a small
adapter. The adapter preserves identifiers, failures, costs, measurement
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
model or system, measurement setup, adapter revision, and coordinate
definitions match. Predictive claims require a separate validation against
later outcomes under the originating study's rules.
