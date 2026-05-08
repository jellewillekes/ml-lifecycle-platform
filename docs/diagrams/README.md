# Architecture diagrams

SVG-rendered architecture views for the ML Lifecycle Platform.  The Python
sources live next to the rendered output so the diagrams stay versionable and
reviewable in PRs.

The diagrams target the **M4 complete** state (multi-source platform on real
data) for the main views, plus a separate **M6 hosted** view for the
low-latency crypto path.  AWS (M5/M7) is intentionally excluded until those
adapters land.

## The set

| File | View | Audience question it answers |
|---|---|---|
| [context_local.svg](context_local.svg) | Context, local | Who interacts with the platform locally, and what crosses its boundary |
| [context_hosted.svg](context_hosted.svg) | Context, GCP staging | Same, with CI and external alerting in scope |
| [container_local.svg](container_local.svg) | Container, local | Every service + every port, with OSS adapters |
| [container_hosted.svg](container_hosted.svg) | Container, GCP staging | Every service + every port, with GCP adapters |
| [deployment_local.svg](deployment_local.svg) | Deployment, local | Compose project — networks, volumes, host ports |
| [deployment_hosted_runtime.svg](deployment_hosted_runtime.svg) | Deployment, GCP runtime | Cloud Run + Cloud Run Jobs + BigQuery event plane + observability VM |
| [deployment_hosted_governance.svg](deployment_hosted_governance.svg) | Deployment, GCP governance | GitHub Environments + WIF + service accounts + Secret Manager + Artifact Registry |
| [deployment_crypto_hosted.svg](deployment_crypto_hosted.svg) | Deployment, M6 hosted | Tick path topology + UP-60 latency budget annotations |

## How to render

Prerequisite: the `graphviz` binary must be on `PATH`.

```sh
brew install graphviz       # macOS
sudo apt install graphviz   # Debian / Ubuntu
```

Then:

```sh
uv sync                     # picks up the `diagrams` dev dep
make diagrams               # renders all 7 SVGs
```

`make diagrams` fails fast with a clear message if `dot` is missing.  Each
source file is also runnable on its own:

```sh
uv run python docs/diagrams/context_hosted.py
```

## Brand logos

PNGs in [assets/](assets/) are fetched by [assets/fetch.sh](assets/fetch.sh).
Sources and licensing are documented in [assets/README.md](assets/README.md).
Built-in icons (Cloud Run, BigQuery, MLflow, Grafana, GitHub Actions, …) come
from `mingrammer/diagrams` and are not duplicated here.

If a logo download fails, the helper in [_common.py](_common.py) falls back
to a labelled box, so the diagram still renders.

## Conventions

- **One file, one diagram, one SVG.**  Filenames match: `context_hosted.py`
  → `context_hosted.svg`.
- **Cluster colours by domain.**  Defined in [_common.py](_common.py):
  data sources (orange), pipeline (blue), registry (green), serving (purple),
  event plane (red), observability (gray), CI/CD (yellow).
- **Edge labels.**  Edges that cross a port boundary carry the contract name
  (`PredictionEvent`, `LabelEvent`, `RuntimeEvent`, `release_manifest.json`,
  `RetrainTrigger`, `DriftBaseline`, `model_card.md`, alias mutation).
  Wire-level signals that are not contracts (HTTP request, OTLP traces,
  alert webhook) use a dashed style.  Internal edges are unlabelled.
- **Local vs hosted.**  Each port has at least two adapters; the local
  diagram shows the OSS equivalent named in the M4 portability rule, the
  hosted diagram shows the GCP service it targets.

## Adding a new service

1. Decide which view(s) the service belongs in (context, container, deployment).
2. Pick the smallest existing cluster that covers it, or add a new cluster
   with a colour from `CLUSTER_COLORS` in [_common.py](_common.py).
3. Use a built-in icon if `mingrammer/diagrams` ships one; otherwise add a
   PNG to [assets/](assets/), an entry to [assets/fetch.sh](assets/fetch.sh)
   and [assets/README.md](assets/README.md), and call `brand("Label", "name.png")`.
4. Run `make diagrams`, eyeball the SVG, commit both source and SVG.

## Drift gate

`make diagrams-check` re-renders and fails if any SVG would change.  It is
not wired into `make docs-check` because it requires `graphviz`; run it
explicitly when changing the diagram sources, or wire it into a dedicated
CI workflow.
