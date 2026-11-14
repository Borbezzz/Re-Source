---
name: "ReSource"
description: "A precise product-parts workspace connecting prepared assemblies to source-backed evidence."
colors:
  surface: "#f2f3f5"
  paper: "#fff"
  ink: "#17191d"
  muted: "#5d6470"
  brand: "#2251ef"
  soft: "#e8edf8"
  border: "#d6dbe4"
  warning: "#8a4d17"
  brand-hover: "#173bc0"
  soft-hover: "#dce4fa"
  stage: "#e8ebef"
  selection-fill: "#e9eeff"
  selection-text: "#2144ba"
  selection-border: "#b7c8ff"
  status-good: "#29654a"
  status-bad: "#a13c32"
  status-unknown: "#85521f"
typography:
  display:
    fontFamily: "\"Geist Variable\", sans-serif"
    fontSize: "clamp(55px, 12vw, 190px)"
    fontWeight: 650
    lineHeight: 1
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "\"Geist Variable\", sans-serif"
    fontSize: "32px"
    fontWeight: 560
    lineHeight: 1.25
    letterSpacing: "-0.035em"
  page-heading:
    fontFamily: "\"Geist Variable\", sans-serif"
    fontSize: "clamp(26px, 2.2vw, 36px)"
    fontWeight: 580
    lineHeight: 1.15
    letterSpacing: "-0.035em"
  intake-heading:
    fontFamily: "\"Geist Variable\", sans-serif"
    fontSize: "clamp(32px, 3vw, 44px)"
    fontWeight: 580
    lineHeight: 1.15
    letterSpacing: "-0.035em"
  title:
    fontFamily: "\"Geist Variable\", sans-serif"
    fontSize: "25px"
    fontWeight: 580
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  subheading:
    fontFamily: "\"Geist Variable\", sans-serif"
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.55
    letterSpacing: "-0.015em"
  body:
    fontFamily: "\"Geist Variable\", sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
  body-small:
    fontFamily: "\"Geist Variable\", sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "\"Geist Variable\", sans-serif"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.3
rounded:
  checkbox: "2px"
  selection-chip: "3px"
  control: "4px"
  badge: "5px"
  tab: "6px"
  field: "7px"
spacing:
  space-8: "8px"
  space-12: "12px"
  space-16: "16px"
  space-24: "24px"
  space-32: "32px"
  space-40: "40px"
components:
  button-primary:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-primary-hover:
    backgroundColor: "{colors.brand-hover}"
  button-secondary:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.brand}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-secondary-hover:
    backgroundColor: "{colors.soft-hover}"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.brand}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  button-icon:
    backgroundColor: "transparent"
    textColor: "{colors.brand}"
    rounded: "{rounded.control}"
    padding: "10px"
  badge:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.brand}"
    typography: "{typography.label}"
    rounded: "{rounded.badge}"
    padding: "4px 8px"
  select-field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "9px 32px 9px 12px"
  global-navigation:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.muted}"
    height: "72px"
  draft-panel:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "24px"
  part-selector:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 9px"
  part-selector-selected:
    backgroundColor: "{colors.selection-fill}"
    textColor: "{colors.selection-text}"
  selection-chip:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.brand}"
    rounded: "{rounded.selection-chip}"
    padding: "6px 8px"
---

# Design System: ReSource

## Overview

**Creative North Star: "From Solid to Source"**

ReSource uses charcoal lettering, cool near-white work surfaces, electric cobalt actions and selection, and fine dotted geometry. The supplied wordmark establishes the signature: solid Geist lettering resolves into a dotted outline around the pointer, with a restrained vector rig. The working interface carries that precision through thin dividers, compact controls, and prepared physical geometry.

The assembly has depth; the surrounding interface stays flat and legible. Selection is explicit in the model, the part list, and removable chips. Source requirements and unavailable actions remain written beside the relevant controls. The v2 entry and prepared toy-car selection are implemented; the engine demo retains the working intake, evidence, and sourcing flows. The dotted globe and parallel-research frame remain a Figma concept, not a delivered component.

**Key Characteristics:**
- Charcoal and cool paper with cobalt reserved for actions, focus, and selection.
- Solid-to-dotted ReSource lettering and precise variable Geist typography.
- Prepared geometry paired with a persistent, keyboard-operable part list.
- Reversible separation with direct controls, reduced motion, and explicit source states.

Ground truth: `src/tokens.css`, the cascade from `src/styles.css` into `src/product.css`, `src/main.tsx`, `src/brand/VectorWordmark.tsx`, `src/product/*.tsx`, and retained shared primitives. `PRODUCT.md` owns product scope. The direction contract is in `.impeccable/surfaces/src-product-producthome-tsx.md`. `design/figma-ledger.json` maps the [v2 entry and selection frames](https://www.figma.com/design/o4G1HFAyQybcPuBG1nV2lL?node-id=13-24) and the unimplemented research concept; source code determines this record.

## Colors

Cool neutrals support an electric action color; the legacy workflow retains distinct semantic status colors.

### Primary

- **Electric cobalt** (`brand`): primary actions, links, focus outlines, range accents, checked selections, and selected mesh emission. `brand-hover` is the deeper button hover state.
- **Cobalt wash** (`soft`): secondary actions, provenance badges, and removable selection chips. `soft-hover` is the secondary hover state.
- **Selected-part wash, text, and border** (`selection-fill`, `selection-text`, `selection-border`): the pressed-state part row. The checkmark and `aria-pressed` carry the same state independently of color.

### Secondary

- **Warning amber** (`warning`): written warnings and warning badges.
- **Status green, red, and amber** (`status-good`, `status-bad`, `status-unknown`): existing engine results with a check, circled cross, or question icon and written status. Unknown remains distinct from failure.

### Neutral

- **Cool paper** (`surface`): page and global header.
- **White** (`paper`): inspector, forms, and evidence surfaces.
- **Charcoal** (`ink`): primary text and wordmark.
- **Slate** (`muted`): supporting text and metadata.
- **Separator** (`border`): fine panel edges and row boundaries.
- **Assembly grey** (`stage`): the prepared model’s working ground.

**The Explicit State Rule.** Pair color with a written state, checked selection, or status icon; cobalt selection never means that a requirement is verified.

## Typography

**Display Font:** Geist Variable, with sans-serif fallback.
**Body Font:** Geist Variable, self-hosted through the application font import.

One variable sans-serif supplies expressive identity and dense operational text. The entry wordmark uses the reference’s canvas-based solid/dotted treatment, with a local monospace coordinate overlay. The static fallback supplies the display role recorded above. Canvas lettering uses a reference-width scale rather than that CSS clamp, so it is not an interchangeable heading component.

### Hierarchy

- **Display:** static ReSource wordmark fallback. The animated instance uses weight 650 and a 235px font reference at a 1200px host width.
- **Headline:** prepared assembly title; it reduces to 28px below the assembly stacking breakpoint.
- **Page-heading / intake-heading:** retained workflow page headings and the larger source intake heading.
- **Title / subheading:** general section and panel headings. The parts-list heading has a local 22px override.
- **Body:** ordinary copy, with a maximum paragraph measure of 75 characters.
- **Body-small:** supporting details and source-state explanations.
- **Label:** compact badges, not a general body-text size.

**The One Family Rule.** Use Geist for headings, prose, controls, and aligned working data. Keep the wordmark’s coordinate readouts local to its vector treatment.

Local asset credits, coordinate labels, citations, and engine metadata include smaller text. These are recorded as implementation limits, not a reusable minimum-size recommendation. Dense numeric tables retain tabular figures where the source defines them.

## Layout

The product entry is centered within an 1800px maximum width. Desktop uses a fluid wordmark column and a 280px action column, a 42px gap, and 28px 40px 44px padding. The global header is sticky, with a thin bottom separator. At 900px the entry uses 24px padding, a 230px action column, and a 24px gap. At 600px it stacks with 20px side gutters; the header becomes 68px high. The wordmark host steps from 255px to 300px above 1600px, to 200px below 900px, and to 145px below 600px.

The prepared assembly has a 230vh scroll track and a sticky working area below the 72px header. Its height is `calc(100vh - 72px)` with a 690px minimum. A fluid scene sits beside a 340px white inspector; the inspector becomes 290px below 1050px. Title and controls use 32px horizontal gutters, reduced to 20px at that breakpoint. The inspector scrolls independently on desktop.

At 700px and narrower, the assembly becomes normal-flow content with a 370px scene row and the parts inspector below it. The part buttons form two columns. Direct-control and reduced-motion modes remove the long scroll track. The current scroll observer retains its 72px offset; do not generalize it as a responsive rule.

Compatible engine-workflow layouts remain: centered content pages with a 1680px maximum width, fluid research and source-review columns, document action rails, and horizontally scrollable comparison tables. These flows stack at their existing 800px breakpoint; outer content gutters reduce at 480px. The reusable spacing scale above supplies shared gaps and padding, with local optical adjustments documented by the source.

## Elevation & Depth

The product workspace is flat: tone, whitespace, and borders separate its controls. The toy-car model receives scene lighting and a soft contact shadow (opacity 0.24, blur 2.6, scale 15, far 4). These are renderer settings, not CSS elevation values. Prepared selected meshes add cobalt emission at intensity 0.85; this is selection feedback rather than a material claim.

The existing engine workflow still uses floating mesh-pin, evidence-drawer, and mobile-inspector shadows. The sidecar records their exact values as compatibility extensions; their older green tint is not the v2 elevation palette.

**The Flat Work Surface Rule.** Use tone, whitespace, and fine borders for ordinary panels; keep physical lighting and contact shadows within the assembly scene.

## Shapes

The v2 control and primary working-panel silhouette is a restrained rounded rectangle using the control radius. Part checkboxes use small square corners; removable chips are slightly softer, and legacy badges, tabs, and form fields retain their recorded radii. Borders are normally 1px. The selected part row adds its explicit border, wash, and checked square rather than changing size.

The wordmark’s dotted outlines, fine dashed lines, and three square handles supply the identity’s vector geometry. Keep those details attached to the reference treatment; ordinary labels remain plain text. Existing engine mesh pins remain circular and numbered.

## Components

### Buttons

Compact and direct. Primary, secondary, text, and icon buttons share the control radius, a 42px minimum height, medium weight, and the documented padding. Icon buttons have a 42px minimum width. Compact actions use a 34px minimum height with 7px 12px padding. The entry upload action has a 48px minimum height, reduced to 46px below 600px.

Primary and secondary hover fills are tokenized above. Text and icon buttons gain the cobalt wash on hover. Background and color transitions last 160ms with CSS’s default ease; no separate pressed animation is defined. Disabled buttons use opacity 0.5 and a not-allowed cursor.

Interactive elements share a 2px solid cobalt focus outline with a 4px offset. The upload field’s focus-within treatment follows the same brand token. Preserve these visible keyboard states.

### Chips and statuses

Neutral provenance badges use the cobalt wash and cobalt text. Selected parts appear as removable chips with an inline close SVG and an accessible removal label. Badge warning and good variants retain their semantic engine-workflow fills. Inline compatibility and review results remain icon-plus-text statuses rather than selection chips.

### Cards / Containers

White drafts, upload slots, requirement panels, and candidate details use the control radius after the v2 override. Draft padding is 24px on desktop, 22px below 800px, and 20px 16px below 480px. Native summaries retain an explicit status and keyboard interaction. Other retained engine containers may still use their original radius; those exceptions do not change the v2 default.

### Inputs / Fields

Select fields use a white fill, separator border, field radius, and the frontmatter padding. Retained draft and requirement textareas stay full-width and vertically resizable; their existing local fills and radii remain compatibility details. All retain visible focus. This implementation has no reusable error-border variant.

### Navigation

The global header uses cool paper, charcoal identity, and muted navigation labels. The active item has charcoal text and a 2px cobalt underline. The compact header mark also uses cobalt. Header navigation remains in a horizontal row on small screens with reduced gaps and hidden nonessential mark detail.

Engine workspace tabs remain a distinct white toolbar with a cobalt-wash selected state. Their existing wrapping behavior and accessible selected state remain intact.

### Prepared assembly and selection

The eight prepared visual groups share stable component and node IDs. Clicking the model or pressing a part-list button toggles one member of the selection; Select all and Clear selection manage the whole set. The list’s checkmark, pressed state, selection count, and removable chips mirror the mesh highlight. The active part’s detail remains distinct from the set of selected parts.

Reversible Anime.js scroll progress drives prepared separation. Ordinary scene movement damps toward that progress; reduced motion applies direct values. Assemble, Explode, and a labelled range input from 0 to 1 with 0.01 steps are always available. Direct input disables scroll separation, and a restore control re-enables it. Reduced motion uses a static wordmark and removes the extended scroll track. Model loading and failure text keep the part list usable when rendering is unavailable.

The geometry label and source-required dimensions/material text stay beside the object. The toy-car source review and supplier research are explicitly unavailable; the working engine-demo action is separate. The future dotted-globe research concept is not a component in this record.

### Wordmark

The ReSource canvas treatment follows the user-supplied reference: pointer-responsive solid and dotted lettering, three square vector handles, and coordinate readouts. The visual treatment is hidden from assistive technology while the page carries a real ReSource heading. The static wordmark appears for reduced motion and when the canvas is not ready. Rendering pauses when its host is out of view or the document is hidden.

### Citations and evidence

The working engine flow retains source-link buttons with inline document icons, long-identifier wrapping, and an independently scrollable evidence drawer in a native modal dialog. The drawer is 540px wide, capped at the viewport width, with a separate close control and dismissible backdrop. Keep provenance and source status visible. Legacy citation and excerpt tints are compatibility details awaiting full palette alignment.

## Do's and Don'ts

### Do:

- **Do** use cobalt for interactive selection and visible focus while keeping source status written in text.
- **Do** retain the source-required dimensions and material labels beside prepared geometry.
- **Do** keep the model, pressed-state part list, selection count, and removable chips synchronized.
- **Do** provide Assemble, Explode, and the separation slider alongside reversible scroll motion.
- **Do** preserve the engine workflow’s evidence links, provenance labels, status icons, and SIMULATED receipts.
- **Do** use the supplied wordmark as the identity reference and provide its static reduced-motion fallback.

### Don't:

- **Don’t** treat curated geometry or a visual group as proof of an engineering requirement.
- **Don’t** present the globe/research concept, toy-car source review, or toy-car supplier research as implemented.
- **Don’t** use cobalt alone to convey selection, compatibility, or approval.
- **Don’t** add decorative card shadows to the flat product workspace.
- **Don’t** turn residual forest-tinted engine styles or 8–10px metadata into v2 defaults.
