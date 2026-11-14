# ReSource

Jet-engine supplier recovery for a UK aerospace procurement/maintenance buyer.
Confirmed flow: blueprint plus part-requirement specification → source-linked
extraction review → generated, segmented, labelled 3D → select a mesh → supplier
investigation → compare requirements/evidence/cost → review a draft approval pack.

The factory specification contains part dimensions, material, tolerance and
certification requirements. Geometry never proves those properties. Each mesh
needs a document-backed identity; uncertain mapping requires confirmation.

The backend handoff currently supports a labelled representative engine and three
synthetic component cases. Intake v1.1 is integrated: uploads, cited requirement drafts, review and mesh validation. Blueprint generation returns provider_required until an actual server adapter is connected; never represent fixture loading as document-to-3D generation. OpenAI is the
application model provider (D-001 confirmed by Yixin).

The product must distinguish seeded/live/replay mode, synthetic offers, public
leads, scenario signals, fixture reliability and SIMULATED receipts. Selection,
document approval, install and restore remain backend-authoritative.

Design in Figma using Impeccable Operate guidance. A reversible Anime.js scroll
timeline controls explosion presentation; actual geometry uses Three.js/R3F.
Support keyboard component selection, direct explosion controls, reduced motion,
source citations, case isolation, stale evidence and reconnecting event streams.
