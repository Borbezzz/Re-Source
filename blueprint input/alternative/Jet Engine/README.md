# Alternative — Jet Engine Lab

Research checked 15 November 2026. This folder records findings and original-source pointers; this alternative is not the selected Mechanica package.

**Source:** https://github.com/AungMyoKyaw/jet-engine-lab
**Inspected commit:** `07dc2651814ae4736f1ee2cbfd7f12c89d3b8b85`
**Live turbofan:** https://aungmyokyaw.github.io/jet-engine-lab/#/engines/turbofan

## Available inputs

- [Original editable SolidCraft geometry and JSON timelines](https://github.com/AungMyoKyaw/jet-engine-lab/tree/07dc2651814ae4736f1ee2cbfd7f12c89d3b8b85/assets/solidcraft).
- [Browser GLB meshes](https://github.com/AungMyoKyaw/jet-engine-lab/tree/07dc2651814ae4736f1ee2cbfd7f12c89d3b8b85/public/assets/solidcraft).
- [Part hierarchy](https://github.com/AungMyoKyaw/jet-engine-lab/blob/07dc2651814ae4736f1ee2cbfd7f12c89d3b8b85/src/app/data/parts.ts).
- [Model integration and design inventory](https://github.com/AungMyoKyaw/jet-engine-lab/blob/07dc2651814ae4736f1ee2cbfd7f12c89d3b8b85/docs/solidcraft-cad/README.md).
- [Asset provenance](https://github.com/AungMyoKyaw/jet-engine-lab/blob/07dc2651814ae4736f1ee2cbfd7f12c89d3b8b85/docs/ASSET_PROVENANCE.md) and [MIT licence](https://github.com/AungMyoKyaw/jet-engine-lab/blob/07dc2651814ae4736f1ee2cbfd7f12c89d3b8b85/LICENSE). External assets retain their own terms.

The repository documents 40 original geometry families across five engine architectures. The high-bypass turbofan has a selectable assembly hierarchy; current click handlers select the enclosing assembly group. Smaller sourcing targets require explicit subcomponent mapping.

## What was checked

The public turbofan loaded in the browser and its exploded-view control worked. Source and hierarchy were read. The bearing-cartridge GLB was downloaded in memory and parsed: glTF 2.0, 1,359,892 bytes, four named meshes (fastener, seal, shell and steel). This establishes useful visual segmentation, not certified bearing specifications.

## How to use it instead

Choose a single architecture and pinned source version. Preserve source-to-GLB correspondence; define three actual geometry targets, persistent IDs and a component manifest. Prepare source-labelled buyer requirement fixtures, then connect the same Re::Source supplier workflow. Styling, lighting and materials can be redesigned independently of the geometry.

This option has editable source geometry but no verified complete manufacturing/sourcing package. Physical dimensions, material grades, tolerances, supplier applicability and approvals remain unestablished. Do not assume `.sc` files are STEP files. Full upstream build/test and physical validation were not performed.
