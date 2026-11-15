# Parallel investigation workspace

Issue #10 follow-up to the prepared product explorer. Frontend-only integration with the existing schema 1.5 batch, task and supplier-event contract.

## Delivered

- Select one or several enabled engine components, start an idempotent batch and retain its URL across reload.
- Read durable task states and actual latest-tool/evidence summaries. Per-case SSE owns reconnect; no interval polling or invented percentage is used.
- Keep raw run/case history for replay, then display only this batch's generation. Lifecycle events use exact generation IDs; decision events require a decision ID proven by that generation's completion event. Later case activity is a separate notice, not batch evidence.
- Dotted, rotatable globe and accessible finding list display discovered supplier locations. Coordinates require a source and valid bounds. Unknown coordinates remain unplotted; synthetic locations are explicitly representative. Connections terminate at a non-geographic investigation node and are not transport routes.
- Filter by component, inspect candidate evidence and location provenance, and open the existing component decision workflow. Historical runs cannot issue current-run actions.
- Clear unavailable/retry state, duplicate-investigation explanation, mobile direct controls and reduced-motion support.

## Verification

Production build and 13 client/mesh/event invariants pass. The connected local browser scenario starts two component investigations, receives eight supplier findings, observes completion, filters findings, opens evidence, retains the batch when its navigation tab is clicked and after reload, verifies the 390px layout and opens a component decision. A separate missing-batch scenario verifies a terminal error and full retry. Existing intro/product checks passed during integration.

Fresh desktop, mobile, start and unavailable captures are in ignored `.impeccable/review/batch/`. The finish review identified batch attribution, reload continuity and small visual corrections. Those were fixed; a second pass identified lifecycle events carrying generation identity in their payload instead of invocation_id. Exact lifecycle/decision association is now covered by a regression invariant and the connected completion assertion. No timestamp-based evidence attribution remains. Figma research layout 13:34 is the editable design reference, with actual data/geometry verified in the browser.

## Limits

Only the enabled engine profile can start research. The curated product's source review and supplier research remain unavailable. The globe is an investigation view, not logistics simulation; candidate evidence does not prove coordinates or supplier eligibility. Generic rules, full uploaded engineering-field evaluation, arbitrary blueprint reconstruction and joint batch optimization are not implemented. Public verification is a separate deployment step.
