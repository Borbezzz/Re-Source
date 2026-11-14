# ReSource — PRD v2, discussion draft

Date: 14 November 2026
Status: Yixin has authorized parallel implementation of the confirmed v2 requirements in issues #10 and #11. This draft supersedes conflicting earlier engine-only/UI directions for that scoped work. Proposals and unresolved business/output choices remain undecided. See IMPLEMENTATION-HANDOFF.md.

## Product direction

ReSource connects component-level product requirements to supplier research through an interactive assembly and a visual investigation workspace. Products and mechanical assemblies with multiple parts are in scope; jet engines are an example.

The specific primary job—source components for a new build, replace an existing component, commission manufacture or a combination—remains to be settled. Do not assume the older failed-engine recovery story is the main use case.

## Confirmed requirements

| ID | Requirement | Source |
| --- | --- | --- |
| P-01 | Support products and mechanical assemblies beyond jet engines. | Yixin, 14 Nov |
| I-01 | Accept detailed blueprint input containing specifications and dimensions. | Yixin, 14 Nov |
| A-01 | Permit a curated demo using premade 3D models prepared and animated in Blender. | Yixin, 14 Nov |
| A-02 | The assembly contains selectable components; permit single-part and multi-part selection. | Yixin, 14 Nov |
| D-01 | Redesign the full UI using Impeccable, addressing the current generic/generated visual quality. | Yixin, 14 Nov |
| D-02 | Use the supplied animated Vector Wordmark as the reference for a ReSource landing treatment and consistent site-wide visual language. | Yixin, 14 Nov |
| R-01 | Make investigation work highly visual and support parallel searches. | Yixin, 14 Nov |
| G-01 | Animate geographic investigation connections to researched locations in a world view. | Yixin, 14 Nov |

## Proposals awaiting agreement

- A dotted, interactive globe using the supplied reference may replace the flat pixel world map. Yixin suggested this as an option, not a final selection.
- One detailed blueprint may be sufficient; supporting specification documents are optional. Input rules remain to be agreed.
- A visible selection tray groups the parts before starting a batch investigation.
- Show supplier discovery, location discovery and compatibility checks as coordinated parallel tasks, grouped by selected part.
- Present per-part results and optionally a joint supplier comparison across several parts.
- End with a chosen shortlist, RFQ or procurement package; the output is undecided.

## Intended screen flow

See [PRODUCT-FLOW.md](PRODUCT-FLOW.md). Landing → product input/review → exploded assembly → one/many part selection → parallel visual investigation → comparison → chosen next action.

## Input and requirements model, proposed

Retain references to the uploaded source when extracting assembly and part identities, units, dimensions, material, tolerance and required certifications. Highlight missing, conflicting or uncertain values for review. Do not derive engineering compliance from visual geometry.

Open: accepted source formats; whether a bill of materials is supplied; minimum useful detail; required quantity, destination, deadline or budget; review/edit experience.

## Assembly and demo preparation, proposed

Use a prepared, segmented asset for the chosen demo assembly. Blender can separate and name components, set pivots and explosion directions, author useful presentation motion and export a web-ready model. Match selectable components to the demo documents and part identities.

The broad product ambition and the curated demo are separate scope decisions. A prepared asset does not prove automatic reconstruction of arbitrary blueprint geometry. An arbitrary-input model-generation feature needs its own agreed scope and capability.

## Selection and investigation, proposed

Maintain a project-level set of selected component identities. Keep results and task states attributable to each selected part. Parallelize independent searches and checks; visibly represent dependencies when later work waits on earlier evidence.

Open: component-versus-module selection, independent versus joint supplier optimization, purchased spare versus manufacture-to-drawing, compatibility rules and required confidence/evidence.

## Visual behavior, proposed

### Brand and interface

Use the wordmark reference's large typography, pointer-responsive fill/outline reveal, fine technical connections and handles to inform a consistent product language. The wider redesign must cover navigation, hierarchy, spacing, controls, panels, evidence and motion. Run Impeccable review on the rendered product at desktop and mobile sizes.

### Geographic investigation

The supplied globe supports rotation, dragging, geographic rendering and location markers. Application-specific supplier information and animated investigation arcs still need to be designed and implemented.

Drive animations from observable task events and real findings. Connect world markers, selected parts, supplier results and evidence. Provide useful pending, complete, uncertain and issue states. Keep motion accessible and the supplier information usable without the 3D presentation.

Open: final globe versus flat-map choice, origin of investigation connections, part/status visual encoding and user controls.

## Outputs and follow-through — undecided

Confirm whether the outcome is a shortlist, quote request, supplier contact package, procurement approval pack or another deliverable. Confirm whether monitoring/reassessment continues after selection.

The previous CAA paperwork, simulated regulatory submission and engine installation/restoration sequence are not automatically requirements for the broader product.

## Existing implementation context

The shared application is on main and publicly hosted on Vercel, with Databricks as its data platform. The current 3D demo is engine-specific and maps three supplier cases. Automatic blueprint-to-segmented-model generation and comprehensive uploaded engineering-field evaluation remain known gaps. Existing behavior is a starting point, not an approval of its scope or design for v2.

Yixin subsequently requested that this work be split between Astra and Bede's agent and implemented in parallel. That explicit authorization supersedes the earlier planning-only hold. Continue the already authorized incremental push/tested-main-merge workflow.

## Acceptance criteria to write after scope decisions

- Source input/review criteria.
- Demo assembly and component-to-document mapping.
- Single/multiple selection behavior.
- Parallel task execution and truthful event-driven presentation.
- Supplier-location evidence and globe/map interactions.
- Compatibility findings and treatment of unknowns.
- Comparison and final user outcome.
- Visual quality, touch/keyboard use and reduced motion.

## References

- [Product flow draft](PRODUCT-FLOW.md)
- [Wordmark source reference](references/wordmark-reference.tsx)
- [Globe source reference](references/globe-reference.tsx)
- https://github.com/pbakaus/impeccable
