# Alternative — KJ66 CAD input

Research checked 15 November 2026. This folder records findings and source pointers. It is a separate small model-aircraft turbojet option, not the selected Mechanica turbofan.

## Existing CAD — no reconstruction required

**Repository:** https://github.com/Akash-9070/Turbo3D
**Inspected source commit:** `09d6456ad12819ae72f3c244f1ac672b34cbcca7`
**Declared repository licence:** [MIT](https://github.com/Akash-9070/Turbo3D/blob/09d6456ad12819ae72f3c244f1ac672b34cbcca7/LICENSE). Verify provenance of individual CAD/documents before redistribution; the repository declaration does not prove every asset's authorship.

| Actual file | Size | Original source |
|---|---:|---|
| Full assembly STEP | 24,712,111 bytes | [assembly of kj66 engine .step](https://github.com/Akash-9070/Turbo3D/blob/09d6456ad12819ae72f3c244f1ac672b34cbcca7/assembly%20of%20kj66%20engine%20.step) |
| Compressor STEP | 2,508,523 bytes | [compressor export.step](https://github.com/Akash-9070/Turbo3D/blob/09d6456ad12819ae72f3c244f1ac672b34cbcca7/compressor%20export.step) |
| Impeller STEP | 1,782,217 bytes | [impeller.step](https://github.com/Akash-9070/Turbo3D/blob/09d6456ad12819ae72f3c244f1ac672b34cbcca7/impeller.step) |
| Inner chamber STEP | 11,292,291 bytes | [inner chamber.step](https://github.com/Akash-9070/Turbo3D/blob/09d6456ad12819ae72f3c244f1ac672b34cbcca7/inner%20chamber.step) |

The repository also contains a fuel-chamber STL, four-page overview/proposal PDF and a presentation. Actual tree contents were checked; do not assume the simulation/image folders described in the README exist.

## Supporting reference documents

[JMA Ireland's download index](https://www.jmaireland.com/jmaitech.html) links a [20-page KJ66 assembly manual](https://www.jmaireland.com/kj66%20manual.pdf), [seven-page drawing PDF](https://www.jmaireland.com/kj66%20drawings1.pdf) and further drawings. The manual and drawing PDF links opened; the additional ZIP was not inspected. The manual carries a copyright notice: link to it rather than redistributing it without permission. Match the exact variant/revision/dimensions before treating these documents and the CAD as one coherent package.

## What was checked and what remains

The full STEP was downloaded in memory: ISO-10303-21/AP214 header, Shapr3D export, 50 PRODUCT entities and 49 assembly-usage entities. These are data-structure counts, not a verified physical-part inventory. Many names are generic (`temp_import.SLDPRT`), so semantic identification is required.

The model was **not imported or visually/topologically validated in a CAD application**. To use it: import and inspect the existing STEP, identify components, retain assembly hierarchy, tessellate/export GLB, create persistent mappings and a reviewed component manifest, then supply matching requirements. No need to model it from scratch unless import/geometry issues require repair.

Community discovery lead: [Reddit discussion recommending KJ66 drawings](https://www.reddit.com/r/aerospace/comments/opvxec/jet_engine_3d_modeling/). Use the actual CAD/documents above as evidence; the forum recommendation does not establish their accuracy or rights.

This is the strongest identified STEP-input candidate, not a verified complete aerospace procurement package. No OEM applicability, physical performance, materials, tolerances or government approval is established by these files.
