# Independent design review — 2026-11-15

Reviewer: independent design_reference_judge agent. Reviewed design flow and generated screens 01, 06, 07, 08 and 10. Verdict at review time: suitable for user direction review. Alvin subsequently approved the screenshots and design direction and authorised this package for implementation reference. This does not constitute functional validation.

The revised intake meets the user's request: no engine, slogan or glowing upload card. Main text is legible; map, shortlist and disruption sequence is coherent.

## Material findings and required interpretation

- Screen 06's global green checks are ambiguous across different sites. Implementation must identify the currently checked candidate and keep every check per candidate; a completed check is not a universal pass. Mandatory checks pending means candidate, not fully qualified supplier.
- Generated pins and summary counts in screen 06 do not agree. Do not copy these pixels as literal data. Pin states, counts and shortlist must derive from the same dataset.
- Generated component shapes and thumbnail layouts drift between screens. Use one actual shared component asset, camera and compact anchor in every map/check/shortlist/disruption state. The visual image assets themselves are illustrative, not authoritative models.
- Keep quantity, required-on-site date and destination available in the expandable component anchor. Show the required date beside a changed arrival estimate.
- Screen 07 route arrows point the wrong way. Implementation routes must run supplier to destination and distinguish schematic connections from supported transport routes. Generated map geometry and coordinates are not authoritative.
- Reviewer identified missing post-disruption outcome. Added screen 08B to show previous recommendation, new recommendation, unchanged requirements and supplier confirmation still pending. Derby remains visible as excluded from on-time shortlist; its numbered marker in the generated image must be replaced by an excluded marker in implementation.
- Screen 10's 'Restored simulation' wording must become 'Reassembly preview'. Show actual engineering acceptance and procurement confirmation states separately; a visual reassembly is not a functional test.

## Status

All findings are recorded as build constraints. Some remain visible in the generated mockups, so the images are provisional composition references and must not be copied literally. Screen 08B was visually inspected by the primary agent; no second independent image review was performed. No website was implemented and no interaction/mobile/accessibility tests were run during mockup creation. Publication of this reference package was subsequently authorised by Alvin.
