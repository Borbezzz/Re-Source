# Re::Source — presentation design proposal v1

Date: 2026-11-15. Status: screenshots and design direction approved by Alvin on 2026-11-15; publication authorised. Implementation must apply the corrections in REVIEW.md. Screens are generated concept mockups, not captures of a working website. This document is standalone and has no dependency on team assignments or a starting guide.

## Product and visual direction

Manufacturer uploads a prepared jet-engine design package, explores its matching component-selectable model, and sources a replacement. Quiet premium industrial software: charcoal canvas, precise offwhite typography, subtle warm-gray secondary text, hairline dividers and generous negative space. Neutral controls; restrained colour only for meaningful selection/status. Retain Re::Source branding. No global dashboard tabs. Use one persistent spatial workspace with contextual overlays. The user rejected the first oversized-slogan/engine-render intake concept as generic AI design. Screen 1 must contain no engine, product render, marketing slogan, glowing upload card or HUD decoration. It is a restrained task-entry screen. Reveal the engine only after package processing. Later spatial screens retain the same typographic restraint.

All names, part identifiers, metrics, quotations and events in the mockups are fictional demo fixtures. Design matching and a restored-engine animation do not establish engineering approval or airworthiness. Document-backed applicability and the appropriate human acceptance remain separate recorded states.

## Screen sequence and transitions

1. **Add design package.** One prominent upload area, supported contents in small secondary copy, prepared demo package shortcut. Package contains assembly geometry/matching prepared model, part manifest with identifiers/revisions, controlled technical requirements and applicability evidence. Ask about missing essentials only.
2. **Process package.** Large evolving wireframe engine with concise real processing stages: identify assembly, map parts, link requirements, prepare scene. Actual job events drive progress; no invented percentages or implied arbitrary blueprint reconstruction. Confirm extracted identity/revision before continuing.
3. **Explore assembly.** Fullscreen metallic engine with selectable component hotspots and collapsible parts list. Main oil-pump case plus two other selectable component cases; final component choice depends on suitable assets. Selection isolates/highlights the component. Context action: replace faulty part or change supplier.
4. **Confirm sourcing need.** Keep selected component in scene. Compact contextual form: reason, quantity (default 1), required on-site date and prefilled delivery site. Default exact same approved part/revision. Manufacture-to-specification and substitutions require their applicable evidence/acceptance paths. Budget optional. No initial buyer-profile form.
5. **Discover supplier sites.** Transition from engine to fullscreen map, preserving selected part as top-left thumbnail/name/part/revision card. Expand card for request summary and return to engine. Pin actual factory/stock/dispatch sites rather than company headquarters. Show discovery coverage and source time.
6. **Qualify visibly.** Map stays present. A temporary check panel explains part match, site qualification, document evidence, availability, arrival feasibility and commercial/operational risk. Candidate discovery precedes per-candidate checks; independent checks may overlap. Highlight affected pins as results arrive. Hard failures exclude; missing mandatory evidence awaits verification; preferences rerank. Excluded pins dim with reasons. Show evidence and tool outcomes, not private model reasoning. Accessible list and reduced-motion equivalent preserve all information.
7. **Compare shortlist.** Reframe map around up to three suitable sites and destination. Right drawer opens with recommended candidate selected and ranked alternatives accessible. Pin selection updates drawer; drawer never hides selected location. Lead with recommendation, part/site qualification, evidence, price/availability/delivery confirmation states, trade-offs, unresolved requirements and next action. Mark estimates until comparable supplier quotes are received. Fewer than three qualified results is valid. AI suggestions are separate from verified facts and supplier claims.
8. **Respond to disruption.** Persistent alert identifies source, timestamp, affected route/site and changed constraint. Highlight affected route; display checks being rerun; update shortlist. Preserve earlier comparison and unaffected evidence. Candidates remain visible without resurrecting unresolved failures. Show before/after and changed ranking reasons. Never silently relax technical or delivery requirements. If an order is already committed, propose a change/cancellation workflow rather than silently replacing it.
9. **Prepare fulfilment.** User chooses supplier, reviews RFQ recipient, exact revision, requirements and requested dates. Show supplier engagement, quote confirmation, order preparation, quality-document requests and delivery arrangements. States: prepared, approved, sent, acknowledged, confirmed. Demo external messages/submissions are simulated and visibly labelled. Do not fabricate supplier-issued certificates. Applicable approval forms are discovered per transaction. Buyer identity/contact/commercial profile is confirmed here. Delivery plan prepared is distinct from dispatch confirmed.
10. **Return to engine.** Match replacement identity/evidence to selected component, animate insertion and reassembly, show reassembly preview. Separately show evidence/acceptance state and procurement readiness. A generated animation cannot prove physical function or compatibility. Return to the same assembly and preserve the case history.

## Reference register

References support individual patterns, not a claim that another product implements the combined experience.

| Reference | Role in our design | Source |
|---|---|---|
| NASA Eyes | Cinematic spatial scene, focus/zoom, object context | https://www.jpl.nasa.gov/edu/resources/lesson-plan/presenting-with-nasas-eyes/ |
| Shapr3D | Selected-component context and relevant actions | https://support.shapr3d.com/hc/en-us/articles/7873882619548-Adaptive-user-interface |
| Vizcom Workbench/Studio | Input → operation → result, contextual detailed workspace | https://docs.vizcom.com/creative-interface |
| Esri ArcGIS Sidebar | Map remains primary beside feature detail panel | https://www.esri.com/arcgis-blog/products/instant-apps/mapping/whats-new-in-instant-apps-september-2021-introducing-sidebar |
| Esri ArcGIS feature effects | Emphasise matching locations and dim excluded features | https://doc.arcgis.com/en/instant-apps/latest/customize/interactivity-settings.htm |
| Celonis Process Sphere | Objects/processes/problems with visible cause and effect; historical 2022 pattern | https://www.celonis.com/blog/celosphere-2022-celonis-brings-perspective-to-process-mining |
| Palantir AIP supply-chain example | Operational constraints → revised recommendations → user action | https://aip.palantir.com/workflow/2b7b3993-9ab8-4695-8b2f-910d282b32be |
| Zip product guide | Procurement sequence, onboarding, approvals and purchasing states; method reference | https://lp.ziphq.com/rs/195-QFD-187/images/eBook___Zip_spend_control_made_easy.pdf?version=0 |
| Xometry | Design package plus specifications, quantities and delivery inputs | https://www.xometry.com/how-xometry-works/ |

The shrinking component card, animated agent qualification sequence and transitions connecting these references are original proposed interactions.

## Review criteria

Approve visual language, scene hierarchy, selected-part continuity, readability, checks and elimination clarity, shortlist decision detail, disruption causality and completion state. These images are desktop direction proposals, not responsive/accessibility validation. Implementation must preserve keyboard selection, accessible results, meaningful statuses, loading/error states and reduced motion.

## Publication boundary

Alvin approved the screenshots and authorised publishing this package to the new `frontend improve` folder on 2026-11-15. This change publishes the specification and references only. Implementation work is a subsequent task; no agents were dispatched to build or deploy the website by this publication task.
