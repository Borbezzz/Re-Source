# Build-agent handover — Mechanica input package

Alvin approved Mechanica as the visual foundation for Re::Source. Use the attached prepared package; do not rebuild the engine from scratch or substitute a different engine during the journey.

## Read first

1. Repository `AGENTS.md`, current ownership/coordination records and current main.
2. This package's README.md and PACKAGE-CONTRACT.md, including validation results.
3. The approved design references in the team repository's `frontend improve/` folder: README.md, HANDOVER-PROMPT.md, DESIGN-FLOW.md, REVIEW.md and all screenshot PNGs.

This handover defines assets and integration. It assigns no teammate ownership and does not itself authorise deployment. The screenshot oil-pump is superseded by the real mapped geometry here: **main fan-blade case**, secondary injector and nozzle cases. Preserve the approved screen composition and flow.

## Implement the journey

**Upload ZIP → Validate/extract → Confirm assembly and requirements → Reveal model → Select component → Enter sourcing need → Discover suppliers on map → Show checks/exclusions → Compare shortlist → Select supplier → Prepare procurement → Reassembly preview.**

During monitoring: **disruption → affected route/site → recheck affected criteria → changed ranking → user reviews revised recommendation**. Retain valid evidence and invalidate affected approvals.

Use `mechanica-input-package.zip` as the actual uploaded package. Parse its manifest, verify file hashes and link the GLB to requirements and component records. The filename alone must not trigger a hard-coded engine reveal. Show processing status from actual parsing/linking steps. Reveal the prepared model only after validation and review of essential missing/conflicting fields. This is not arbitrary CAD generation.

Use quiet premium industrial design: charcoal background, offwhite typography, fine dividers, generous space and sparse contextual controls. No engine render on the intake page, oversized marketing slogan or generic dashboard tabs. The map and model provide visual impact within the workflow. Existing styling in the utility inspector is not a final-site design reference.

## Geometry and selection

- Load `input-package/assembly.glb` with the existing Three.js/React Three Fiber environment. Keep one model identity throughout the case.
- Package 1.1 maps 35 sourcing families across all seven sections. `RS-TF-FAN-BLADE` explicitly maps all 24 fan blades and `RS-TF-FUEL-INJECTOR` all 18 injectors; `RS-TF-CORE-NOZZLE` maps the nozzle group. The expanded browser keeps family sourcing identity separate from the inspected occurrence, with group/individual hover, keyboard focus and direct selection. See the manifest for per-stage compressor/turbine identities.
- Follow PACKAGE-CONTRACT.md for metadata-based lookup and nearest-ancestor case resolution. GLTFLoader sanitises names, so use `userData.stableId`/`componentId`.
- Save home transforms and implement intentional focus, explode, fault, removal and insertion animations. The export has no baked animation. Keep component and requirement IDs stable while objects move.
- The fuel injector is a simplified cylindrical original reference shape. Do not present it as a detailed manufactured nozzle or relabel unrelated meshes. The front blade is the stronger close-up. Physical geometry, materials and dimensions are educational and unvalidated.
- The GLB flattens instanced pieces for reliable selection. Measure loading/render performance before choosing production batching/LOD; preserve the persistent IDs if optimising.

## Backend and evidence

The input package provides geometry, identities and buyer-defined requirement fixtures only. Connect the actual supplier discovery, qualification, ranking, disruption and procurement workflow to existing typed commands/events and versioned persisted state. Add a dedicated package/component profile; do not reuse old engine rules under new names.

Preserve the approved Databricks data/document services and current hosting/provider setup. Use existing application architecture rather than importing Mechanica's complete application stack. No MongoDB runtime is required by this asset package.

Use source-supported site locations; distinguish estimated and confirmed stock/price/delivery. Display per-candidate evidence and failed/unknown/passed checks. Map pins, totals and ranking must share one state. After shortlist selection, prepare reviewable enquiry/quotation/order/document/approval/delivery stages. Retain explicit simulation for external messages/submissions and separate engineering acceptance from reassembly animation.

**Real suppliers cannot be expected to sell fictional `RS-DEMO-*` part numbers.** For a successful exact-match shortlist, prepare clearly synthetic supplier offers and evidence tied to these fixtures. In live research mode, capability/category discovery may find real leads, but exact identity/applicability stays unresolved unless genuine supporting evidence exists. Never attach an invented stock claim or quote to a real company.

## Provenance and rebuilding

Upstream: https://github.com/PouyanJay/mechanica at **a1d52be81b5e9ea125df337a3b30039ff996edc8**, MIT. Keep LICENSE-Mechanica.txt and attribution. Original source snapshots and a pure-geometry adapter are included under tools/vendor. No original build scripts or full application dependency stack are needed.

The full unchanged source is also preserved under `original/Mechanica/`, including all seven original engine families and the original interactions. Use `original/README.md` to navigate it and `original/Mechanica-SOURCE.json` to verify it. Teammates can make a new engine/package from this source instead of using our prepared turbofan. Alternative research is under `alternative/Jet Engine/` and `alternative/KJ66/`.

Node 24 is the tested rebuild environment. Install only the locked tooling dependency using `npm ci --prefix tools --ignore-scripts --no-audit --no-fund`; then run `node tools/export-package.ts` and `node tools/validate-package.mjs`. Recreate the upload ZIP from the **contents** of input-package, with the manifest at the archive root. Recompute distribution checksums. A changed source build must get a new package version in `tools/package-config.json` and reviewed mappings. The exporter guards its geometry/exporter/tool-version fingerprint and refuses changed file bytes under the same existing version.

## Finish with evidence

Drive the real upload-to-reassembly journey in the browser. Verify all three cases, direct/list selection, evidence states, shortlist drawer, disruption rerank, approval invalidation and simulated procurement receipt. Check keyboard/reduced-motion/mobile behaviour and actual console/network failures. Run repository gates relevant to your changes. This package's structural/preview checks are not end-to-end product verification; report any remaining integration gaps honestly.
