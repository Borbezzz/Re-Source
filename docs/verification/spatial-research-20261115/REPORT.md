# Spatial research refinement

15 November 2026. Scope: the product investigation research presentation only.
The navigation, provider/backend contracts and approval gates are unchanged.

## Implemented

- Large central translucent dotted globe with real/sample country markers.
- Slow frame-rate-independent rotation (2 degrees/second), pause/resume and drag.
- Floating translucent right-hand supplier cards, entrance animation when actual
  candidate results mount, and expandable evidence/source details.
- Marker selection reveals and focuses its card; card focus highlights its mark.
- Existing unknown-location leads remain in the list, without invented markers.
- Responsive stacked cards below the globe on smaller screens.

## Verification

- Production build and TypeScript checks pass; all 18 frontend checks pass,
  including sourced geography and exact-package approval invariants.
- Real browser checks at 1280×720, 1440×1000 and 390×844 verified globe size,
  transparent cards, readable details, location focus and no horizontal overflow.
- Clicking the Germany marker focused Alpine Works and scrolled only the desktop
  rail. At mobile size it scrolled the page to reveal the focused card in view.
- Pause/resume changed the displayed state; closing the research section stopped
  auto-rotation. Manual reset restores the initial view and pauses rotation.
- Independent review checked reduced-motion, offscreen/hidden demand rendering,
  grounded marker filtering and preserved sourcing actions. Its responsive focus
  finding was fixed and verified in the browser. Reduced-motion preference logic
  was code-reviewed; no OS preference was changed during browser checks.
- Impeccable detection found advisory local palette differences. New spatial
  tints are documented in DESIGN.md; pre-existing error colors were retained.

No new dependencies, generated supplier data, or backend/provider changes.
