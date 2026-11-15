# Copyable implementation handover

You are implementing the approved Re::Source presentation redesign in https://github.com/Borbezzz/Re-Source. Alvin approved the screenshots and design direction on 15 November 2026. Read the repository AGENTS.md and current coordination records before changing files. Respect active ownership and the team lead's assignments; this handover does not assign teammate folders or authorise deployment by itself.

Read `frontend improve/README.md`, `frontend improve/DESIGN-FLOW.md`, `frontend improve/REVIEW.md`, then inspect all eleven linked PNGs in order. Open the actual images; text alone is insufficient. `frontend improve/index.html` is a local review gallery. No team starting guide is required to understand this specification.

## What to build

Re::Source helps a manufacturer recover a jet-engine component supply problem. The presentation is one continuous spatial journey: prepared design-package intake → processing → matching interactive assembly → selected component and sourcing need → supplier-site map → visible agent checks and elimination → ranked shortlist and supplier drawer → disruption and selective recheck → revised recommendation → supplier selection and procurement preparation → return to assembly and reassembly preview. The main demo has one deep component case plus two nearby clickable component cases using the same workflow.

### Design language

Use quiet, premium industrial-software design. Flat charcoal near #151515; offwhite primary typography; warm-gray secondary text; generous deliberate whitespace; fine dividers; restrained neutral buttons; sparse contextual panels. Colour has meaning: subtle mint for selection/passed state, amber for disruption/pending. Support the existing brand with a crisp Re::Source wordmark. Typography and actual content carry the interface. The engine/model and geography become the visual centre only once the workflow reaches them.

The first page must follow `01-design-package-v2.png`: one calm task-entry composition and one obvious upload action. No jet-engine render on the first page. No oversized slogan, glowing upload card, decorative dashboard, tiled metrics, global navigation tabs, science-fiction HUD or hover-box spectacle. Do not restore the rejected intake concept. Apple professional-app/Linear-like restraint describes the styling; it is not a claim that their exact layouts were researched or copied.

Use the approved screenshots as references for composition, hierarchy and panel behaviour, not as bitmap backgrounds or literal engineering/data truth. Implement real selectable 3D meshes, interactive map pins, forms, evidence panels and application states. Reuse and refactor working code/assets where suitable. Desktop presentation is the leading composition, with responsive and keyboard-accessible equivalents.

### Required interaction flow

1. **Intake:** one design-package upload; prepared demo-package shortcut. Extract and confirm the assembly and essential requirements instead of asking for a long form. The prepared package maps to a prepared model; this is not arbitrary blueprint-to-engine CAD generation.
2. **Processing:** show actual events such as assembly identification, parts mapping, requirements linking and scene preparation. Do not manufacture progress percentages or task results. Reveal the engine after processing.
3. **Assembly:** fullscreen model, clickable components, collapsible parts list; part selection isolates/highlights the correct mesh. Three component cases, one main deep case. The oil-pump shown in the mockups is illustrative: verify actual model support and existing component/evidence mapping before finalising the case; do not relabel unrelated geometry.
4. **Sourcing need:** reason (faulty part/change supplier), quantity, required-on-site date and prefilled delivery site. Default same approved part and revision. Technical requirements come from reviewed evidence, not visual inference. Other sourcing routes expose their additional requirements only when selected.
5. **Map:** transition to a fullscreen supplier-site map. Keep one compact, recognisable component thumbnail/name/part/revision anchor at top left; expand for quantity, deadline, destination and return to model. Reuse the SAME model asset and thumbnail camera across all states.
6. **Agents:** keep the map present while checks explain what is happening. Discovery precedes per-candidate qualification; use actual events and source-linked results. Mandatory failed requirement excludes; missing evidence stays awaiting verification; preference changes rerank. Identify the candidate being checked. Do not use global green checks to imply every supplier passed.
7. **Shortlist:** show up to three suitable sites with ranked pins. Open the right drawer with recommendation, exact part/site, evidence, price/stock/delivery confirmation status, risk, trade-offs, unresolved needs and next action. Map clicks change the drawer. Keep selected pin visible. Awaiting mandatory evidence is not qualified; estimates are not confirmed offers. Fewer than three results is valid.
8. **Disruption:** persistent sourced/timestamped alert, affected path highlight, changed arrival compared with required date, selective rechecking, retained unaffected evidence, visible before/after recommendation (08B). Keep exclusions intact. Never silently relax requirements. If an order is already committed, propose a change workflow rather than replacing it invisibly.
9. **Procurement:** selecting a supplier leads to reviewable RFQ content/recipient and automatic document preparation, followed by quote confirmation, order preparation, quality-document requests and delivery arrangements. Display prepared/approved/sent/acknowledged/confirmed distinctly. Retain explicit demo simulation for external actions. Buyer/contact/commercial information is confirmed here rather than burdening intake. Regulatory forms depend on the actual transaction; discover applicable UK CAA requirements and actual forms during implementation. Do not invent a universal new-supplier government application or fabricate supplier-issued certificates.
10. **Return:** animate the matched replacement entering the same assembly. Label this a reassembly preview; separately display engineering acceptance and procurement readiness. A model fitting on screen does not prove physical function or airworthiness.

### Reference companies: what to borrow

- NASA Eyes: cinematic spatial focus and exploration.
- Shapr3D: component selection and contextual actions.
- Vizcom Workbench/Studio: input → operation → result and contextual detailed work.
- Esri ArcGIS Sidebar/feature effects: map plus selected-location detail, visual filtering and dimmed exclusions.
- Celonis Process Sphere: visible relationships between objects, processes and problems (historical reference).
- Palantir AIP supply-chain example: disruption constraints → revised recommendation → user action.
- Zip: supplier onboarding, procurement stages, approvals and purchasing states.
- Xometry: manufacturing package, requirements, quantity and delivery inputs.

Use the specific URLs and limits in DESIGN-FLOW.md. The shrinking component card, agent-check animation and connecting transitions are our proposed synthesis; do not claim these companies have this exact combined flow.

### Integration and correctness

Inspect current main before designing adapters. The existing app is React/TypeScript/Vite with React Three Fiber and prepared assets; current repository product docs describe Vercel frontend/API with Databricks data/document services and configured OpenAI/Linkup research. Preserve that working architecture; this redesign does not migrate hosting, introduce MongoDB technology or rewrite existing providers. Reference the original supply-chain implementation only where already authorised and useful.

Bind screens to current typed commands/events and persisted case state. Extend missing contracts explicitly rather than faking completions. Use one source of truth for candidates, pin states, check results, counts, ranks, selected site and request version. Preserve stale-decision/approval invalidation, evidence provenance, visitor isolation and truthful fixture/live distinctions. Public research leads are not verified aerospace approvals.

Use source-supported coordinates; when only country-level location is known, mark it representative rather than inventing a street-level pin. Draw delivery direction supplier → destination; schematic arcs are not validated transport routes. Every requirement and status needs readable text/symbols as well as colour. Support keyboard selection, accessible results lists, reduced motion, loading/error/empty states and a responsive detail drawer.

The generated screenshots contain known inconsistencies. REVIEW.md is mandatory: resolve changing pump shapes/header layouts, inconsistent map totals, premature eligible labels, arrow direction, hidden deadline and 'Restored simulation' wording. These errors are not part of the approved implementation behaviour.

### Completion evidence

Demonstrate the full journey in the browser, including component selection, real progress updates, exclusions and unknowns, map-to-drawer selection, disruption → changed ranking, reviewable procurement simulation and reassembly preview. Verify relevant desktop/mobile, keyboard and reduced-motion states, and run the repository checks appropriate to the changes. Do not report provider/runtime success from source inspection or old test logs. Report what is implemented, what is simulated, actual checks and any remaining gap. Coordinate implementation ownership rather than dispatching overlapping work.
