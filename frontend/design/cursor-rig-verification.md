# Cursor-local sourcing rig

Historical verification: the user requested removal of this overlay on 15 November 2026. Its component, listeners and stylesheet have been removed; the title and background ripples remain.

14 November 2026. Refines the hero interaction from main 2d13863.

- Nine small white cubes and three optional neutral labels stay near the pointer. Short links follow the same local cluster.
- Each entry/reactivation samples new offsets. Motion preserves that arrangement within the hover and briefly settles; idle frames stop.
- Copy, buttons and the explore link suppress colliding elements without moving the cluster elsewhere. Optional labels also clear the occupied wordmark band. Pointer exit, scroll, touch, cancellation, blur, hidden/offscreen state and reduced motion clear it.
- Actual browser checks at widths 1440, 900 and 390 measured maximum visible extents of 188, 173 and 89 pixels from the pointer in the captured samples. Same-point re-entry signatures differed. All tested copy intersections were zero.
- Idle SVG mutations stayed at zero over 500 ms. Scroll cleared the stationary-pointer cluster; the next pointer movement reactivated it locally. No browser errors were observed.
- Production build and typecheck pass. This interaction-only change does not alter the application workflow, APIs, providers or engine assets.

Local screenshots, the real browser clip and proof data are under `frontend/.impeccable/review/cursor-rig/` (untracked). The release PR records the scoped independent review and public verification.
