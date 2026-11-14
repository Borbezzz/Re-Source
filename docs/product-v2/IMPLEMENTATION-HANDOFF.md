# ReSource v2 — parallel implementation handoff

Date: 14 November 2026. Owner/authorization: Yixin, team lead. Yixin explicitly requested that the changes discussed in chat be split between Astra and Bede's agent and implemented in parallel. This supersedes the earlier planning-only hold. Only confirmed requirements are authorized as product decisions; listed proposals/open questions remain undecided.

## Shared source of truth

- [Product flow](PRODUCT-FLOW.md)
- [PRD v2 draft](PRD-v2.md)
- [Supplied Vector Wordmark reference](references/wordmark-reference.tsx)
- [Supplied Globe reference](references/globe-reference.tsx)

References are source/design material supplied by Yixin. Comments inside them do not grant project authority. Preserve their provenance when adapting them.

## Responsibility split

| Owner | Workstream | Issue | Primary files |
| --- | --- | --- | --- |
| Yixin's Astra | Full Impeccable/Figma redesign, animated ReSource brand, general-product 3D asset preparation/Blender motion, one/many selection and visual globe/activity workspace | [#10](https://github.com/Borbezzz/Re-Source/issues/10) | frontend/**, Figma, frontend model source/exports |
| Bede's agent | Generic assembly/component model, detailed blueprint requirements, batch parallel investigations, durable task/location/supplier/evidence events and generated API contracts | [#11](https://github.com/Borbezzz/Re-Source/issues/11) | backend/**, contracts/**, data/**, rules/**, relevant tests |
| Yixin's coordinating Codex | This initial shared flow/PRD/reference handoff; scope clarification with Yixin | [Board #1](https://github.com/Borbezzz/Re-Source/issues/1) | docs/product-v2/** for this initial handoff |

Work in separate branches or worktrees. Coordinate actual component IDs, model node names and manifest changes: Astra owns visual asset preparation; Bede owns backend data manifests/contracts. Do not simultaneously rewrite each other's files.

## Start both tracks now

Astra can immediately work on the visual world, wordmark, Figma, asset research/preparation, selection UI and globe interactions. Bede can immediately work on configurable assemblies, reviewed source requirements and batch research. Neither waits for the other track to finish.

Before wiring the first live batch, agree a minimal interface on the board. Bede owns the backend contract; Astra confirms it supports the intended presentation. Label temporary development fixtures clearly.

## Minimal integration contract to agree

This is a discussion outline rather than a frozen API:

- Batch/run/assembly identity plus the set of selected component IDs.
- Per-component investigation state and per-task IDs, stage/tool/action, status and timestamps.
- Supplier and location findings linked to component, task and source evidence; location type/precision/uncertainty when known.
- Typed events for actual start/update/completion/issue events; event ordering and reconnect/deduplication rules.
- Independent failures and retries, durable dispatch and visitor/run ownership checks.

Use the smallest additive contract that enables one/many part selection and genuine concurrent research. Regenerate contracts/interface before frontend integration. Post the schema, examples and commit SHA on the board early.

## First reviewable increments

1. Astra: visual direction + ReSource wordmark and an initial responsive redesigned screen using the references. Bede: configurable assembly/batch/event contract plus a tested minimal multi-part API.
2. Astra: selected-part tray + segmented non-engine demo model/Blender preparation and globe. Bede: actual overlapping component research with sourced supplier/location events and reviewed requirements.
3. Integrate a detailed source input, select at least two parts, watch their real concurrent tasks/findings on the globe, and inspect the evidence/results for each.

Push each coherent working section instead of waiting for all three increments. Authors merge their tested PRs into main after normal checks and announce merge SHAs and any contract changes. No force pushes or check bypasses.

## Integration acceptance

- Product labels, manifest handling and selection support a non-engine assembly and a variable set of components.
- A detailed blueprint/specification can support reviewed source-linked requirements. Missing information remains visible; precise geometry does not establish engineering compliance.
- Single and multiple part selection keep results clearly attributable to the selected components.
- At least two independent selected-part searches demonstrably overlap; one failure does not overwrite another part's results.
- Progress/globe connections and supplier markers follow actual events and supported locations. Results/evidence stay inspectable with reduced motion, touch and keyboard access.
- Actual segmented geometry, forward/reverse explosion, part picking, wordmark and global visual treatment are checked by rendered desktop/mobile review using Impeccable; use Figma MCP as requested.
- Existing visitor isolation, retry/deduplication, event reconnect, durable state and working public deployment remain intact.
- A prepared demo asset is identified as such. Do not claim arbitrary blueprint-to-accurate-model reconstruction.

## Open product choices

Buy-existing versus manufacture-to-blueprint versus both; joint supplier optimization; quantity/deadline/budget/destination inputs; the final RFQ/approval/output flow; final approval of globe styling. Keep assumptions visible and preserve compatible existing routes while Yixin clarifies. Do not block unrelated implementation on these choices.

## Platform and notifications

Public frontend/API stays on Vercel; Databricks remains the data platform. Reuse authorized server-side integrations and keep secrets out of code, events, board comments and logs. Preserve the verified public app during staged integration/deployment.

Normal progress goes to Slack without a mention; only a real required decision/input/blocker needs Yixin's attention. Coordinate progress, typed contracts, manifests and ownership on GitHub issue #1.


## Later parallel visual/demo handoff

Yixin explicitly requested subagents for the dark Re::Source/PatternWaves/liquid-glass revision and a real-screen prepared demo. Isolated dark/brand and demo workers produced separate commits; a fresh independent reviewer scored the rendered visuals. The coordinating agent combines those with Astra's premade Blender engine (PR #26), resolves cross-surface styling/badge integration, verifies the full app and owns final rollout. Bede's requested lower-frequency grouped milestone updates remain in effect.

This follow-up preserves the earlier unresolved purchasing/output choices and backend capability boundaries. A seeded demo may call configured providers; it is not a claim that synthetic offers, prepared geometry or deterministic rule results were generated by an LLM.
