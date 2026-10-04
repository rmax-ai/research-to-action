# governed-clinical-actions

**Governed Clinical Actions** POC: a natural-language biomedical research intent must
become a **correct, authorized, reproducible, and actionable transaction** across
heterogeneous/federated clinical data.

> **Status: E1 foundation.** This repository contains the versioned contracts,
> provenance/audit primitives, typed resumable workflow shell, deterministic mock
> provider, and offline parity/CI checks. Later epics add synthetic site adapters,
> feasibility, governance, and procurement behavior.

## POC invariant

A natural-language biomedical research intent must become a correct, authorized,
reproducible, and actionable transaction across heterogeneous/federated clinical data.

## Canonical scenario (working proposal)

Find 200 metastatic NSCLC patients with KRAS G12C, pretreatment H&E, NGS, treatment
history, and >=12 months of outcomes for commercial AI model development; determine
feasibility, governance, provenance, supplier mix, and mock procurement.

## Layout

| Path | Purpose |
| --- | --- |
| `src/governed_clinical_actions/models/` | Strict Pydantic v2 boundary contracts |
| `src/governed_clinical_actions/provenance/` | Request, plan, run, claim, and evidence identity |
| `src/governed_clinical_actions/audit/` | Append-only event log |
| `src/governed_clinical_actions/workflow/` | Typed tool gate and pause/resume state machine |
| `src/governed_clinical_actions/llm/` | Provider protocol and deterministic mock |
| `tests/` | Python test suite (pytest) |
| `fixtures/parity/` | Shared Python/TypeScript JSON boundary fixtures |
| `ts/` | TypeScript Zod parity schemas and tests |

Boundary objects carry `schema_version: 1` and use `extra="forbid"`. Unknown
versions and unknown fields fail closed. Adding a compatible schema version
requires an explicit model/dispatch entry; validation remains separate from
authorization and workflow policy.

## Development

Python 3.12+ with [uv](https://docs.astral.sh/uv/):

```bash
uv sync --dev
uv run pytest -q
uv run ruff check .
```

TypeScript (Node 20+):

```bash
npm install
npm run typecheck
npm run test:ts
```

Run the complete offline-friendly local CI checks (tests use only synthetic
fixtures and do not call external providers):

```bash
./scripts/ci-local.sh
```

## License

MIT — see [`LICENSE`](LICENSE).
