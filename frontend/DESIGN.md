---
name: "Re::Source"
description: "A precise product-parts workspace connecting prepared assemblies to source-backed evidence."
colors:
  surface: "#08090b"
  paper: "#121419"
  ink: "#f2f4f8"
  muted: "#a8b0bf"
  brand: "#9cbaff"
  soft: "#1d2943"
  border: "#ffffff20"
  warning: "#e7bb83"
  brand-hover: "#c2d4ff"
  soft-hover: "#283b60"
  stage: "#0d1016"
  selection-fill: "#223553"
  selection-text: "#dbe8ff"
  selection-border: "#8aafff"
  status-good: "#a4d8c0"
  status-bad: "#f4aaa7"
  status-unknown: "#e7bb83"
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
  selection-chip: "4px"
  control: "8px"
  badge: "5px"
  tab: "8px"
  field: "8px"
  panel: "12px"
  hero-action: "14px"
  group: "14px"
  group-inner: "10px"
  segment: "10px"
  segment-inner: "7px"
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

# Design System: Re::Source

## Overview

The current direction is the user-requested dark Re::Source display brand. The two colons suggest parts :: sources. The opening uses React Bits PatternWaves `silk` with white on black, soft edge fades and pointer ripples. The title stays crisp and solid. A compact white sourcing cluster follows the pointer, chooses a new arrangement on re-entry and clears on exit; there is no optical lens or dotted hover mask.

`src/theme/dark-glass.css` is the final theme stylesheet. [Theme details](src/theme/DESIGN.md) document the material, tokens and fallback behavior. Native buttons, links, selects and ranges keep their semantics and keyboard focus. Glass is concentrated on navigation/controls; evidence and working panels remain readable. Mobile navigation items cannot shrink below their text.


**Creative North Star: "From Solid to Source"**

Re::Source uses bright solid-to-dotted lettering, near-black work surfaces, pale glass controls, cool blue focus/selection and fine dotted geometry. The supplied wordmark establishes the signature: solid Geist lettering resolves into a dotted outline around the pointer, with a restrained vector rig. The working interface carries that precision through thin dividers, compact controls, and prepared physical geometry.

The assembly has depth; the surrounding interface stays flat and legible. Selection is explicit in the model, the part list, and removable chips. Source requirements and unavailable actions remain written beside the relevant controls. The v2 entry and prepared toy-car selection are implemented; the engine demo retains the working intake, evidence, and sourcing flows. The sourced dotted globe and parallel-research workspace are implemented for enabled engine components; generic-product research remains gated.

**Key Characteristics:**
- Near-black surfaces, pale lettering and glass controls; cool blue identifies focus and selection.
- Solid-to-dotted Re::Source lettering and precise variable Geist typography.
- Prepared geometry paired with a persistent, keyboard-operable part list.
- Reversible separation with direct controls, reduced motion, and explicit source states.

Ground truth: `src/tokens.css`, the cascade from `src/styles.css` into `src/product.css` and the final `src/theme/dark-glass.css`, `src/main.tsx`, `src/brand/VectorWordmark.tsx`, `src/product/*.tsx`, and retained shared primitives. `PRODUCT.md` owns product scope. The direction contract is in `.impeccable/surfaces/src-product-producthome-tsx.md`. `design/figma-ledger.json` maps the [v2 entry and selection frames](https://www.figma.com/design/o4G1HFAyQybcPuBG1nV2lL?node-id=13-24) and the earlier research concept; current source and the theme documentation determine the implemented visual record.

## Colors

Cool neutrals support an electric action color; the legacy workflow retains distinct semantic status colors.

### Primary

- **Cool blue** (`brand`): links, focus outlines, range accents and checked selections. Primary buttons use pale glass fills; renderer mesh selection retains its own explicit blue emission.
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

The prepared assembly has a 230vh scroll track and a sticky working area below the 72px header. Its height is `calc(100vh - 72px)` with a 690px minimum. A fluid scene sits beside a 340px opaque dark inspector; the inspector becomes 290px below 1050px. Title and controls use 32px horizontal gutters, reduced to 20px at that breakpoint. The inspector scrolls independently on desktop.

At 700px and narrower, the assembly becomes normal-flow content with a 370px scene row and the parts inspector below it. The part buttons form two columns. Direct-control and reduced-motion modes remove the long scroll track. The current scroll observer retains its 72px offset; do not generalize it as a responsive rule.

Compatible engine-workflow layouts remain: centered content pages with a 1680px maximum width, fluid research and source-review columns, document action rails, and horizontally scrollable comparison tables. These flows stack at their existing 800px breakpoint; outer content gutters reduce at 480px. The reusable spacing scale above supplies shared gaps and padding, with local optical adjustments documented by the source.

## Elevation & Depth

Working panels use tone, whitespace and borders; native controls and navigation add restrained glass edges and blur. The toy-car model receives scene lighting and a soft contact shadow (opacity 0.24, blur 2.6, scale 15, far 4). These are renderer settings, not CSS elevation values. Prepared selected meshes add cobalt emission at intensity 0.85; this is selection feedback rather than a material claim.

The existing engine workflow still uses floating mesh-pin, evidence-drawer, and mobile-inspector shadows. They retain their behavior while the dark theme overrides their surrounding working surfaces and text.

**The Flat Work Surface Rule.** Use tone, whitespace, and fine borders for ordinary panels; keep physical lighting and contact shadows within the assembly scene.

## Shapes

Controls and fields use 8px corners, panels 12px, and selection chips 4px. The standalone 52px hero actions use 14px corners. Nested assembly controls use a 14px outer radius and 10px inner radius across their 4px inset; segmented controls use 10px and 7px across 3px. Separate ordinary surfaces through tone and spacing; retain field boundaries, selected states and visible focus. Part checkboxes stay small squares and slider thumbs stay circles.

This follows the size and nesting principles in the [REI Cedar radius guide](https://cedar.rei.com/guidelines/radius) and [Apple's concentric-shape guidance](https://developer.apple.com/videos/play/wwdc2025/356/).

The wordmark remains crisp and solid during hover. Nine small white wireframe cubes, short connections and three neutral sourcing labels form a local cluster around the pointer. Keep the cluster bounded near the pointer rather than distributing it across the hero; soft masks preserve edge treatment. Existing engine mesh pins remain circular and numbered.

## Components

### Buttons

Compact and direct. Primary, secondary, text, and icon buttons share the control radius, a 42px minimum height, medium weight, and the documented padding. Icon buttons have a 42px minimum width. Compact actions use a 34px minimum height with 7px 12px padding. The entry upload action has a 48px minimum height, reduced to 46px below 600px.

Primary and secondary hover fills are tokenized above. Text and icon buttons gain the cobalt wash on hover. Background and color transitions last 160ms with CSS’s default ease; no separate pressed animation is defined. Disabled buttons use opacity 0.5 and a not-allowed cursor.

Interactive elements share a 2px solid cobalt focus outline with a 4px offset. The upload field’s focus-within treatment follows the same brand token. Preserve these visible keyboard states.

### Chips and statuses

Neutral provenance badges use the cobalt wash and cobalt text. Selected parts appear as removable chips with an inline close SVG and an accessible removal label. Badge warning and good variants retain their semantic engine-workflow fills. Inline compatibility and review results remain icon-plus-text statuses rather than selection chips.

### Cards / Containers

Dark drafts, upload slots, requirement panels and candidate details use role-appropriate corners and separate content primarily through tone and spacing. Retain borders where they identify fields, selections or necessary data boundaries. Draft padding is 24px on desktop, 22px below 800px, and 20px 16px below 480px. Native summaries retain an explicit status and keyboard interaction.

### Inputs / Fields

Select fields use a dark fill, separator border, field radius, and the frontmatter padding. Retained draft and requirement textareas stay full-width and vertically resizable; their existing local fills and radii remain compatibility details. All retain visible focus. This implementation has no reusable error-border variant.

### Navigation

The global header is black with pale identity and muted navigation labels, matching the hero's upper fade. The active item uses pale text and a restrained tonal background. Header navigation remains in a horizontal row on small screens with reduced gaps and hidden nonessential mark detail.

Engine workspace tabs remain a distinct dark toolbar with a cobalt-wash selected state. Their existing wrapping behavior and accessible selected state remain intact.

### Prepared assembly and selection

The eight prepared visual groups share stable component and node IDs. Clicking the model or pressing a part-list button toggles one member of the selection; Select all and Clear selection manage the whole set. The list’s checkmark, pressed state, selection count, and removable chips mirror the mesh highlight. The active part’s detail remains distinct from the set of selected parts.

Reversible Anime.js scroll progress drives prepared separation. Ordinary scene movement damps toward that progress; reduced motion applies direct values. Assemble, Explode, and a labelled range input from 0 to 1 with 0.01 steps are always available. Direct input disables scroll separation and switches the hint to direct controls without adding a reset button. Reduced motion uses a static wordmark and removes the extended scroll track. Model loading and failure text keep the part list usable when rendering is unavailable.

The geometry label and source-required dimensions/material text stay beside the object. The toy-car source review and supplier research are explicitly unavailable; the working engine-demo action is separate. The future dotted-globe research concept is not a component in this record.

### Wordmark

The Re::Source title retains the supplied vector identity with crisp, solid lettering that does not blur or turn into a dotted outline on hover. Nine small white cubes follow the pointer with short connections and three neutral process labels. Re-entering the hero reshuffles the arrangement; moving within one hover preserves it. Copy collisions suppress local elements rather than pushing them across the screen. Decorative effects are hidden from assistive technology while the page carries a real Re::Source heading. Reduced motion and unsupported WebGL use the static title. Rendering pauses offscreen and in hidden tabs; pointer exit clears the rig.

### Citations and evidence

The working engine flow retains source-link buttons with inline document icons, long-identifier wrapping, and an independently scrollable evidence drawer in a native modal dialog. The drawer is 540px wide, capped at the viewport width, with a separate close control and dismissible backdrop. Keep provenance and source status visible on opaque dark evidence surfaces.

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


## Guided demo and prepared engine

Start demo opens a new isolated seeded run and guides the same Intake, assembly, batch investigation, evidence, comparison and approval screens used by the app. Sample documents are explicitly labelled; confirmation and approval remain user actions. The guide shows the real missing blueprint-to-mesh provider state and makes the separate prepared assembly choice explicit.

The engine viewport uses the licensed Blender-prepared cutaway for compatible engine cases, including existing runs; activated uploaded GLBs take precedence. Casing-first separation, module spread, reverse scrolling and focus follow actual mesh transforms. Source notices and an editable Blender project are supplied; visual counterparts do not establish engineering compatibility.

## Verification scope

Desktop/mobile captures and a fresh independent Impeccable review found two material issues (header naming and mobile pill sizing); both were resolved and scored ship with no visible regressions. No QUALITY BAR card was supplied, so this is not a whole-surface ceiling certification. Build, frontend invariants and real-screen demo/browser regression checks pass locally. See frontend/design/dark-demo-verification.md for exact evidence and limitations.
