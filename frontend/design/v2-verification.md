# Prepared product explorer — first v2 milestone

Branch: `10-product-workspace-v2`, PR #23. Based on main through backend schema 1.5. This milestone changes only `frontend/**`; it does not enable generic supplier research.

## Ready to test

- Entry uses the supplied ReSource wordmark; reduced motion uses static accessible text.
- Toy Car is a curated CC0 asset, segmented/animated in Blender and exported as actual GLB geometry. Attribution and reproducible preparation are in `../models/README.md`.
- Eight component/node mappings match the backend `toy-car-demo` preview. Click geometry or use keyboard-accessible part buttons to select one or several groups.
- Scroll 0 → 0.5 → 1 → 0 separates and reassembles the geometry. Direct controls and a reduced-motion alternative remain available.
- Blue geometry highlights mirror the list selection independently of the asset texture. Original emission is restored on deselection.
- Failed GLB loading ends the loading state and retains the usable part list.
- Engine demo is reachable through the explorer and `/#engine`. Source intake resumes at `/#sources`.
- Structured stale reasons render their summary; backend gating is unchanged.

## Verification performed

Production build and ten client/mesh invariants passed. Eight browser scenarios passed: two intake/resume, one engine intro, two prepared-product interaction/failure, and three existing engine recovery workflows. Checks cover viewport resize to 390px, no horizontal overflow, reduced motion, API-unavailable presentation, direct geometry picking, source edit/confirm/reload, event-driven sourcing, comparison, evidence and document/repair gates.

Rendered evidence is local under `frontend/.impeccable/review/v2/`: entry desktop/mobile, assembled/mid/exploded/reverse, single/multiple selected geometry, and failed asset. These files are deliberately ignored rather than shipped in the application bundle.

Impeccable finish review scored both requested fixes resolved: visible geometry selection and a terminal failed-load state. Its `ship` verdict is scoped to those fixes in this increment. Figma editable entry/selection layouts are listed in `figma-ledger.json`; the research frame is still a concept.

## Remaining work

The batch/globe frontend is not delivered by this milestone. Toy-car uploads/review/research remain unavailable pending run-scoped catalog/rule isolation and source-reviewed requirements. The existing engine intake/sourcing path is explicitly labelled. A curated asset does not establish arbitrary blueprint reconstruction. Engineering material/dimension/tolerance/certification checks remain manual-review unknowns. Public deployment verification must be recorded after merge; local tests are not proof of live deployment.
