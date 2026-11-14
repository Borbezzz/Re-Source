# Dark theme verification — 14 November 2026

Isolated branch `codex/re-source-dark-glass`, based on `3a2ed24`. No App, scene, backend or model asset changes.

- `npm run build`: passed (existing large Three/SupplyMap chunk warnings remain).
- `npm test`: 13 passed.
- Existing `e2e/product.spec.ts`: 2 passed, covering prepared geometry, reversible separation, multiple selection, reduced motion, and failed model fallback.
- Chromium at 1440×1000 and 390×844: no page errors or horizontal overflow; native buttons and range usable; keyboard focus visible.
- Glass lens: computed backdrop contains the SVG displacement filter and visibly bends the title in Chromium. Lens is inactive outside the wordmark; blue rig and numeric labels clear immediately outside the hero (label opacity 0.6 inside, 0 outside).
- Hidden-tab lifecycle handler: wave and wordmark draw counts remained `[235, 95]` over the observation interval. Offscreen below sticky header: counts remained `[273, 107]`.
- Live reduced-motion preference: animated wordmark canvas is replaced by the static Re::Source mark; wave frame counter stops. No-WebGL check preserves the static mark and working entry controls.
- Complete React Bits license notice is retained in source and distributed runtime canvas metadata.

Captures (untracked) are under `frontend/.impeccable/review/dark-glass/`: `desktop.png`, `desktop-full.png`, `desktop-hover.png`, `desktop-exit.png`, `desktop-controls.png`, `mobile.png`, `mobile-full.png`, `mobile-reduced.png`, `mobile-no-webgl.png`. `lifecycle.json` contains the final measured frame counters. The coordinating agent owns final combined-flow screenshots after App integration.

Impeccable detector ran once. Findings are design-system drift against the incumbent light DESIGN.md (new dark colors, sizes and radii) and the pre-existing wordmark coordinate font/size. No detector repair was run. The theme additions are documented in this directory's DESIGN.md; the coordinating agent owns the consolidated frontend DESIGN.md update and independent finish review.

Browser limitation: SVG backdrop displacement is a progressive enhancement. Other browsers retain readable glass-like blur/highlight styling and native controls; Safari/Firefox distortion was not claimed or verified.
