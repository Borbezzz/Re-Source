# Verification — 15 November 2026

Package 1.1 update: current machine-readable reports cover 35 sourcing families and regenerated package hashes. See `../../docs/verification/parts-browser-20261115/REPORT.md` for browser, backend and stage-sourcing checks. The original three-case asset review below is historical evidence from package 1.0.

## Observed results

- Exported actual Mechanica-derived geometry to GLB v2: **5,601,448 bytes**.
- Preserved 2,075 mesh occurrences: **1,835 independent pieces + 240 attached surface details**.
- GLTFLoader parsed the exported binary and preserved unique persistent metadata IDs.
- Verified three target mappings, associated requirement records, CSV/manifest consistency, source occurrence counts, file hashes and model-derived bounds after round trip.
- Actual browser loaded the local inspector from `http://127.0.0.1:8768/preview.html`.
- Primary-agent browser drive selected and visually inspected injector, front fan blade and nozzle through the list buttons; inspected the full engine; exercised group explosion, reassembly and casing visibility. The isolated fuel injector is simplified cylinder geometry, motivating the blade as the primary case.
- Adjusted inspector focus distance to reduce crowding; final inspector was reloaded and group explosion/reassembly/casing controls were exercised. No final three-case framing sweep was repeated.
- Independent agent read source, docs, hashes, GLB metadata, CSV and mappings. It found no asset-contract blocker and identified three handover/validation issues; live-vs-fictional clarification, CSV consistency checks and changed-build version guards were added.

## Reports

- `package-validation.json`: automated asset/identity/round-trip checks.
- `piece-inventory.json`: all occurrences, attached-detail relations and pinned upstream/runtime ID correspondence.
- `archive-validation.json`: ZIP root membership, CRC checks, file integrity and distribution checksums (created during final packaging).
- `regression-validation.json`: unchanged rebuild preserves file hashes; changed same-version geometry and contradictory CSV are rejected in a temporary copy.
- `independent-review.md`: findings and resolutions.

## Limits

These checks do not establish physical dimensions, manufacturing suitability, engine performance, approved part applicability or qualified suppliers. The input fixture contains no genuine supplier offers or government approvals. Direct canvas picking code is present; an actual canvas hit was not exercised in this browser pass. Mobile, reduced motion, keyboard interaction, performance benchmarking and the final product's upload/agents/procurement flow remain implementation checks.

No full upstream app build, upstream test suite, real supplier outreach, submission, website deployment or GitHub push was performed. The local inspection server is stopped after verification; restart it using README instructions.
