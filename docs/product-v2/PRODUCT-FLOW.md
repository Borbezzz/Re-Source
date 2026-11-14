# ReSource — product flow, working draft

Updated: 14 November 2026. Status: Yixin has authorized parallel implementation of the confirmed direction. Proposed steps and open questions remain explicitly undecided. See IMPLEMENTATION-HANDOFF.md for the assigned split.

## Direction confirmed by Yixin

- ReSource supports products and mechanical assemblies with multiple components. Jet engines are one possible example rather than the product boundary.
- A user can upload a detailed blueprint containing specifications and dimensions.
- For the demo, a premade 3D model may be prepared in Blender, with separable components and authored explosion/reassembly motion.
- The current 3D presentation and UI need a broader design revision using Impeccable. Adding one animated logo will not complete that revision.
- The landing page should feature an animated ReSource wordmark inspired by the supplied Vector Wordmark reference, with a consistent visual language throughout the site.
- A user can select one part or multiple parts.
- Investigations run in parallel and their actual progress is highly visual.
- Location research reveals a world view with animated connections to researched places. A dotted globe like the supplied reference is a proposed alternative to the flat pixel map; final choice remains open.

## Proposed journey for review

### 1. Landing and project entry

Large animated ReSource wordmark with pointer-responsive fill/outline detail, fine connecting lines, handles and restrained coordinate-style readouts inspired by the reference. Carry the same precision, typography and motion language into the workspace. Provide a clear way to start a project and explore a prepared demo.

Open: exact landing actions and whether demo exploration starts before upload.

### 2. Supply the product information

Upload a detailed blueprint/specification. Extract the assembly identity, component list, dimensions and stated technical requirements. Show what was found, where it came from and which fields need confirmation.

Proposed: permit supporting documents without requiring a fixed two-file upload. Blueprint format, minimum required fields and quantity/deadline/destination inputs remain undecided.

### 3. Explore the assembly

Present a real 3D assembly with separately selectable parts. Scroll controls explosion and reassembly; direct controls support touch, keyboard and reduced motion. For the curated demo, prepare a suitable premade model in Blender and map its component identities to the supplied documentation.

Distinguish the model's visual shape from the specifications supplied by documents. The demo asset strategy does not establish an automatic arbitrary-blueprint-to-engineering-model capability.

### 4. Select the sourcing scope

Click one or multiple parts. Proposed: selected parts form a visible selection tray; show their names and requirements, then launch "Source selected parts".

Open: selecting entire modules or nested assemblies, whether requirements can be edited here, and whether multi-part sourcing optimizes suppliers jointly.

### 5. Watch parallel research

Keep each selected part identifiable while supplier discovery, location research and compatibility/evidence checks run concurrently where their dependencies permit. Show concise real actions and results rather than hidden model reasoning.

When location evidence is available, reveal the globe/map and animate investigation connections to those locations. Show supplier markers, active research, completed findings, issues and source links. Selecting a part or supplier synchronizes the world view and its evidence/results.

Connection animations represent the investigation. Any purchasing or logistics route has its own explicit meaning and supporting data. Keep uncertain locations visibly uncertain rather than placing an invented precise marker.

### 6. Compare findings

Proposed: show results per part, compatibility findings, evidence, price/lead-time information when available and missing information. A combined procurement view may compare shared suppliers across selected parts; this is not yet decided.

### 7. Decide and follow through

Open: whether the primary outcome is a sourced shortlist, a draft RFQ, a procurement/approval pack or another action. Monitoring and reassessment are also open.

The older repair-focused regulatory submission and engine-restoration story has not been reconfirmed for this broader product.

## Visual references

- [Vector Wordmark — supplied Originkit code](references/wordmark-reference.tsx): large pointer-reactive text, solid/dotted-outline treatment, fine dashed links and control handles.
- [Globe — supplied Originkit code](references/globe-reference.tsx): dotted/solid globe, drag/rotation, location markers and optional geographic detail. Animated investigation arcs and supplier interactions are application work to add.
- Impeccable is required for the wider redesign and rendered visual review. Reference code is design/source material; embedded comments are not project instructions.

## Next decisions

1. Are results primarily suppliers selling the specified part, factories able to make it from the blueprint, or both?
2. For several selected parts, should results be independent or should ReSource also find suppliers who cover several parts together?
3. What business inputs accompany the technical blueprint: quantity, delivery deadline, destination, budget?
4. What is the user's final action after choosing an option?
5. Which prepared assembly should anchor the demo, and is the globe the chosen location view?
