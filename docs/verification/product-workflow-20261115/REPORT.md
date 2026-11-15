# Product workflow verification — 15 November 2026

Story: choose a prepared product or upload a specification, review its parts,
select a sourcing scope, investigate concurrently, compare sources and prepare
an explicitly reviewed RFQ package with a simulation-only receipt.

Tested implementation: `67b917d9ffd268e38237e86c4932467b5695148b`.
Connected staging URL: https://resource-8l52a07c4-borbez2s-projects.vercel.app
This production-environment deployment was created with `--skip-domain`, so the
canonical live domain remained on the prior release throughout verification.

## Automated validation

- Full backend suite: **226 passed, 4 skipped**, in 32.59 seconds. The four skips
  are optional connected Databricks tests in the deliberately offline suite.
- Frontend production build/typecheck and **18 tests passed**.
- New backend modules pass Ruff. Canonical export produced 105 model schemas,
  OpenAPI and TypeScript; exported files match the committed implementation.
- All 14 profile parts resolve to actual GLB mesh nodes. Every prepared requirement
  quote appears in its profile's explicitly synthetic source document.
- Independent regressions cover source ownership, source bytes and PDF page bounds,
  confirmation rollback/retry, after-commit dispatch, identity grounding, value and
  unit boundaries, no-op revisions, stale results and exact-package approval.

## Browser checks

Using the actual browser against local API and production frontend builds:

- Gallery opens all three profiles; lamp, toy-car and engine geometry renders in the
  generic viewer. Assemble/explode and multi-part selection work without a reset
  button appearing.
- Lamp review → three research jobs → evidence comparison → three supplier choices
  → RFQ download → approval → simulated receipt completed. The RFQ download is
  2,712 bytes and includes the selected requirements and outstanding evidence.
- A custom text specification uploaded through the actual file chooser produced
  Mounting bracket (quantity 4) and Drive shaft (quantity 1). A quantity edit to 5
  survived tab navigation and was confirmed. The project continues without a 3D
  model and accurately states that automatic generation is unavailable.
- Reload restores the owned project and appropriate workflow step.
- At 390 × 844, the header is 108px, document width is 390px and no horizontal page
  overflow or reset control appears. Model controls and part selection remain
  usable. Workflow navigation scrolls within its own row.
- Fresh production-build assembly → research transition has no browser errors.
  A React nested-root cleanup warning appeared during development/HMR; it did not
  reproduce in the fresh production build.
- The connected staged deployment renders the gallery from its real API.

## Connected backend and sponsor integrations

See [deployed-product.json](deployed-product.json) for sanitized observations.

| Boundary | Observed result |
| --- | --- |
| Project persistence | Lakebase/Postgres, visitor owned |
| Parallel execution | Two per-part jobs observed running together through the durable queue |
| Demo comparison | Two completed investigations with labeled fictional sample offers |
| RFQ workflow | Two-item package, exact-package approval and persistent simulated receipt |
| Ownership isolation | A second visitor received 404 for the first visitor's project |
| Document upload | Original bytes stored through configured durable storage |
| Part extraction | Uploaded structured specification produced two independent product parts |
| OpenAI | Used for actual live supplier query planning |
| Linkup | Returned six source-linked supplier leads for the reviewed shaft specification |
| Databricks | AI Functions extracted literal supplier claims from retrieved snippets |
| Evidence semantics | All live candidates remained public, cited and unverified; no sample offers mixed in |

A real archival blueprint was also tested. Databricks `ai_parse_document` read the
NASA blade-section fixture, and OpenAI proposed one named part with three cited
requirements for review. The drawing identifier was **not** promoted to an OEM
part number. The model correctly remained missing. Nothing was confirmed or
procured from that drawing. See [nasa-blueprint.json](nasa-blueprint.json) and the
[fixture provenance](../../../data/fixtures/intake/README.md).

## Deployment configuration and limits

The GitHub preview build succeeds, but its API cannot start because this project's
Lakebase/provider environment variables are scoped to Production only. Runtime
logs identify the deliberate guard against SQLite on Vercel. Connected verification
therefore used the existing Production settings in an unaliased deployment; no
credentials were copied into Preview and no runtime guard was disabled.

Prepared geometry is visual context, not engineering verification. Automatic
blueprint-to-CAD generation still requires a real provider. Public source claims
remain unverified leads. RFQ approval and receipts authorize simulation only;
no email, purchase order or payment was sent. Connected checks demonstrate these
specific executions, not general extraction accuracy across arbitrary drawings.
