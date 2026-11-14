---
name: ReSource
description: An assembly-centered workspace for source-backed supplier recovery.
colors:
  surface: "#f7f8f5"
  paper: "#fff"
  ink: "#172c28"
  muted: "#566960"
  brand: "#194f45"
  soft: "#e6eee8"
  border: "#d9e0d9"
  warning: "#8a4d17"
  brand-hover: "#123c34"
  soft-hover: "#d8e6db"
  focus: "#277762"
  status-good: "#29654a"
  status-bad: "#a13c32"
  status-unknown: "#85521f"
typography:
  display:
    fontFamily: '"Geist Variable", sans-serif'
    fontSize: "clamp(32px, 3vw, 44px)"
    fontWeight: 580
    lineHeight: 1.15
    letterSpacing: "-0.035em"
  headline:
    fontFamily: '"Geist Variable", sans-serif'
    fontSize: "clamp(24px, 2.05vw, 32px)"
    fontWeight: 580
    lineHeight: 1.15
    letterSpacing: "-0.035em"
  title:
    fontFamily: '"Geist Variable", sans-serif'
    fontSize: "25px"
    fontWeight: 580
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  subheading:
    fontFamily: '"Geist Variable", sans-serif'
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.55
    letterSpacing: "-0.015em"
  body:
    fontFamily: '"Geist Variable", sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
  body-small:
    fontFamily: '"Geist Variable", sans-serif'
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: '"Geist Variable", sans-serif'
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.3
rounded:
  citation: "4px"
  badge: "5px"
  tab: "6px"
  field: "7px"
  control: "8px"
  panel: "12px"
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
  draft-field:
    backgroundColor: "#fcfdfa"
    textColor: "{colors.ink}"
    rounded: "{rounded.tab}"
    padding: "9px 12px"
  workspace-tab:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.tab}"
    padding: "9px 14px"
  workspace-tab-selected:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.brand}"
  draft-panel:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "24px"
  citation:
    backgroundColor: "#edf2eb"
    textColor: "#32634c"
    rounded: "{rounded.citation}"
    padding: "4px 6px"
  assembly-segment:
    backgroundColor: "transparent"
    textColor: "{colors.brand}"
    rounded: "{rounded.badge}"
    padding: "8px 15px"
  assembly-segment-selected:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.paper}"
  component-selector:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "17px 12px"
  component-selector-selected:
    backgroundColor: "#e3ece4"
---

# Design System: ReSource

## Overview

**Creative North Star: "The Assembly Workbench"**

The code-led Operate direction combines warm off-white work surfaces, forest navigation and actions, and pale sage selection. The physical assembly is the visual center of the inspection workspace. Nearby controls, evidence, and compact tables use quiet typography and thin separators so the object and the decision remain connected.

Geist supplies both headings and working text. White panels sit within a pale surface without decorative elevation; amber marks uncertainty, while explicit text and icons carry status. This record describes the implemented visual system, with the tokens above as its normative values. It does not establish geometry, compatibility, or evidence as verified merely because the interface displays them.

**Key Characteristics:**
- Assembly-centered inspection with a persistent selected-part context.
- Forest actions, sage selection, white panels, and thin separators.
- One variable sans-serif family with compact, tabular numeric content.
- Direct controls and keyboard alternatives accompany spatial motion.

Source evidence: `src/tokens.css`, the final cascade in `src/styles.css`, `src/main.tsx`, `src/App.tsx`, `src/components/Primitives.tsx`, and `src/scene/EngineScene.tsx`. Product context lives in `PRODUCT.md`; the surface direction and concept seed live in `briefs/workspace.md`. `design/figma-ledger.json` maps the [Figma exploration](https://www.figma.com/design/o4G1HFAyQybcPuBG1nV2lL) to variables and frames; source code determines the values recorded here.

## Colors

The palette is green-tinted and low in saturation, with a dark action color and distinct semantic status tones.

### Primary

- **Forest** (`brand`): global header, primary buttons, active segmented controls, links, and input accents. `brand-hover` deepens primary buttons on hover.
- **Sage** (`soft`): secondary buttons, active workspace tabs, and neutral provenance badges. `soft-hover` is the secondary button hover fill.
- **Focus green** (`focus`): visible keyboard outlines around interactive elements.

### Secondary

- **Amber** (`warning`): warnings and warning badges.
- **Status green, red, and amber** (`status-good`, `status-bad`, `status-unknown`): compact results paired with a check, circled cross, or question icon and a written state. Unknown is visually distinct from failure.

### Neutral

- **Off-white** (`surface`): page and assembly work surface.
- **Paper** (`paper`): forms, working panels, tables, and the evidence drawer.
- **Ink** (`ink`): primary text and control text.
- **Muted green** (`muted`): supporting text and labels.
- **Separator** (`border`): panel edges, field boundaries, and row dividers.

**The Explicit State Rule.** Pair semantic color with a written state and, where the status component is used, its icon; selection color alone does not communicate verification.

## Typography

**Display Font:** Geist Variable, with sans-serif fallback.
**Body Font:** Geist Variable, with the same fallback; self-hosted through the application font import.

One family handles display and dense operations. Headings use slightly tightened tracking and intermediate variable weights. Body copy remains sentence case; prices, quantities, timestamps, and numbered components use tabular figures where alignment matters. Paragraphs have an observed maximum measure of 75 characters.

### Hierarchy

- **Display:** the intake heading; its responsive size becomes 34px at widths up to 480px.
- **Headline:** the assembly title; it becomes 27px at widths up to 800px. Case-page headings use a local 30px size.
- **Title:** section headings; selected sections reduce to 23px at widths up to 480px.
- **Subheading:** panel headings, with local sizes for document and evidence headings.
- **Body:** ordinary working copy. The intake introduction uses a local 17px size, reduced to 16px on small screens.
- **Body-small:** supporting paragraphs and compact details. Tables also use 12px text with their inherited body line height.
- **Label:** badges. This role is not a general-purpose body size.

**The One Family Rule.** Use Geist for headings, prose, controls, and numeric data; use tabular figures rather than a second typeface for aligned values.

The existing 8–10px scene annotations and dense metadata are local implementation details, excluded from the reusable type ramp. They do not establish a preferred minimum text size for future screens.

## Layout

Desktop inspection uses a fluid assembly column and a fixed inspector (370px). The header is sticky (76px high). The assembly stage is sticky below it, with a height of `calc(100vh - 136px)`, bounded by 620px and 1050px. Scroll-driven assembly presentation uses a 1300px minimum section; direct-control mode uses the viewport-based stage height. The inspector has its own vertical overflow. Content pages use a centered 1680px maximum width and desktop padding of 30px 40px 60px. Intake has a separate 1800px maximum width.

The reusable spacing values above occur throughout padding and gaps; the implementation also uses optical adjustments between them. Thin row separators and grouping provide density without enclosing every item. Research uses a 1.6:1 grid; document review uses a fluid main column with a 310px action rail; source review uses a 0.9:1.1 grid.

- **At 1700px and wider:** the inspector grows to 440px, its padding becomes 40px, and assembly side padding becomes 48px.
- **At 1100px and narrower:** the inspector becomes 320px, general content padding becomes 24px, and the document action rail becomes 275px.
- **At 800px and narrower:** the header becomes 68px high; intake, research, document review, source review, and detail columns stack. The inspector and action rail become normal-flow content. The assembly remains sticky below the header, bounded by 620px and 800px; its canvas has a 280px minimum height. Source preview becomes static. Component selection remains available below the scene.
- **At 760px and narrower:** the comparison table reveals a horizontal-scroll instruction. The table remains horizontally scrollable instead of compressing its numeric columns.
- **At 480px and narrower:** outer content gutters become 16px, workspace navigation spans a full row, draft fields stack, and the draft footer becomes vertical. The assembly is bounded by 600px and 780px with a 260px minimum canvas height. Nonessential component numbers and icons are hidden by the relevant narrow-screen rules; the text buttons remain.

The current scroll observer starts at a 76px top offset even when the mobile header is 68px. That fixed observer value is recorded as source behavior, not promoted to a universal responsive rule.

## Elevation & Depth

Ordinary cards and forms are flat: background tone, whitespace, and fine borders establish their boundaries. Shadows are reserved for spatial pins and the evidence drawer. The rendered assembly has its own contact shadow and lighting; that physical depth does not imply elevation for surrounding UI panels.

### Shadow Vocabulary

- **Mesh pin:** a soft local shadow (`0 3px 9px #233d2830`) separates a numbered control from the model.
- **Evidence drawer:** a left-cast shadow (`-8px 0 35px #1430201a`) places the drawer above the workspace; its separate backdrop is translucent forest (`#152e2440`).
- **Assembly contact:** the scene uses contact-shadow opacity 0.25, blur 2.8, scale 14, and far distance 3. These are scene-rendering parameters, not CSS elevation tokens.

**The Flat Work Surface Rule.** Keep ordinary panels free of box shadows; reserve the existing shadow treatments for floating pins and the evidence drawer.

## Shapes

Controls and panels use restrained rounded rectangles. Control corners, field corners, workspace tabs, badges, citations, and panels have separate recorded radii; do not collapse their distinctions into one large pill shape. Mesh pins are circular, with a white 2px border and a rendered overlay size of 32px. Small circular step counters and event marks are part of their respective sequences.

Borders are normally 1px. Selected component buttons add a muted green border (`#a5c0af`) and a pale selection fill; table selection uses its own pale row tint. These are local state treatments rather than replacements for the primary action fill.

## Components

### Buttons

Compact and direct. Primary, secondary, text, and icon buttons share a 42px minimum height, medium weight, and the control radius. Icon-only buttons also have a 42px minimum width; compact actions use a 34px minimum height and 7px 12px padding. The header has a smaller icon-control override on narrow screens.

Primary and secondary hover fills are tokenized above. Text and icon buttons gain a sage background on hover. Background and text color transition over 160ms with CSS's default `ease`; there is no explicit pressed animation. Disabled buttons use opacity 0.5 and a not-allowed cursor.

All buttons, links, inputs, selects, textareas, and summaries have a 2px solid focus-green `:focus-visible` outline with a 4px offset. The upload label uses a 2px forest outline with the same offset on `:focus-within`.

### Chips and statuses

Badges are compact, slightly rounded provenance or state labels. Neutral badges use sage and forest. Warning and good variants have local tinted fills. Statuses are inline text and icons rather than filled chips; good, bad, and unknown must remain distinguishable by their contents.

### Cards / Containers

White panels use the panel radius and no box shadow. Drafts use 24px padding, changing to 22px below 800px and 20px 16px below 480px. Candidate details and requirement panels use related 24–28px interior spacing. Collapsible drafts use a native summary; the status sits at its trailing edge and wraps on small screens.

### Inputs / Fields

Selects use a white fill, separator border, field radius, and 9px 32px 9px 12px padding. Draft textareas use a pale fill, fine green border, tab radius, and the documented draft-field padding. They are full-width, vertically resizable, and have a 40px minimum height. Requirement textareas use their own 42px minimum height, 13px text, and field radius. All retain the shared visible focus treatment. This source does not define a reusable field-error border variant.

### Navigation

The forest global header has light navigation text, white active text, and a 3px sage underline at the active item. Workspace navigation is a separate white toolbar: muted text at rest, sage fill and forest text on the active rounded tab. The source defines selected and focus states without an additional workspace-tab hover fill. On narrow screens the toolbar wraps, then the tabs occupy a full row.

### Citations and evidence

Citations are small buttons with an inline document SVG, pale fill, and darker green text. They wrap long identifiers rather than truncating the reference; hover darkens the fill. A native modal dialog holds the right-aligned evidence drawer (540px, capped at the viewport width) with a separate close control and dismissible backdrop. The drawer scrolls independently. This pattern exposes source details; it does not assign evidentiary authority through styling.

### Assembly controls

Numbered mesh pins and text component buttons provide parallel entry points. Selected text buttons use a sage tint and green border with `aria-pressed`; the component list remains the renderer fallback. Assemble/Explode are two pressed-state buttons inside a pale segmented tray. A labelled range input exposes separation from 0 to 1 in 0.01 steps. Direct input turns scroll-driven separation off.

Scroll synchronizes separation linearly and reverses with scrolling. Mesh separation follows a damping coefficient of 10, with frame delta capped at 0.1 seconds. Camera focus interpolates with `1 - exp(-delta * 6)`. These are interpolation rates, not fixed animation durations. Under reduced motion, scroll-driven separation is disabled and geometry/camera positions update directly; CSS animation and transition durations reduce to 0.01ms, animation iteration count becomes one, and smooth scrolling becomes automatic. The loading spinner otherwise rotates over 1.4 seconds linearly. Motion communicates inspection state, never compatibility or approval.

## Do's and Don'ts

### Do:

- Do keep source identity, provenance, uncertainty, and status readable beside the object or decision they qualify.
- Do use the forest primary action, sage selection, and quiet white panels for their established roles.
- Do preserve visible keyboard focus, native controls, direct separation input, and the component-list fallback.
- Do use tabular figures and retain horizontal scrolling for dense comparison data.
- Do honor reduced motion in both CSS and the rendered scene.

### Don't:

- Don't use color alone to communicate a result or treat selection styling as verification.
- Don't make scrolling or mesh interaction the only route to component selection and inspection.
- Don't apply the evidence-drawer or pin shadow to ordinary working panels.
- Don't reuse the smallest scene annotations as the default body or label scale.
- Don't let animation or physical realism imply document-backed compatibility, generation, or approval.


## Engine-first entry revision

The first visit opens `EngineIntro`: a real R3F representative assembly, independent of API readiness. The concept PNG is not the primary hero. A 265vh desktop scroll track progressively separates seven modules and reassembles on reverse scroll; direct controls and reduced motion remain available. Indexed blade surfaces share normals, metal lighting has stronger depth, and the camera opens toward the intake. Module geometry and the labelled strip select the same module.

Source upload and requirements sit beside the scene. On narrow screens an explicit details control opens the same module, part and upload content; it is not removed. Supplier actions stay disabled until a real visitor run exists. Source navigation uses `#sources` so a reload resumes extraction/review. New visitors with no view hash see the assembly. Figma revision frames: `8:21`, `8:58`, `8:95`.
