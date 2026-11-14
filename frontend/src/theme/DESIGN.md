# Re::Source dark material theme

Display branding only; repository names, domains, API and component IDs remain unchanged.

The opening uses the user's pinned direction: a crisp Re::Source vector wordmark on white PatternWaves `silk` over black, with stronger pointer ripples and gradual fades into the header, sides and following section. The hero gives the wordmark room, then exposes Start demo and Upload blueprint as native buttons. The prepared assembly remains accessible below it.

`dark-glass.css` is the last stylesheet in `main.tsx`. It defines near-black working surfaces, pale body text, blue selection/focus, warm status colors and translucent controls. Glass is concentrated on navigation and controls through backdrop blur, a directional highlight, a soft edge and a restrained offset shadow. Buttons and ranges keep native semantics, focus, keyboard behavior and disabled state. This is a local CSS implementation informed by Apple's liquid-glass appearance and the researched `rdev/liquid-glass-react` reference; that library is not installed or represented as the implementation.

PatternWaves is the verified React Bits implementation by David Haz, requiring `ogl`. Its presets and interaction API are retained, with local ripple-strength and edge-treatment refinements. Full upstream license: [vendor/REACT-BITS-LICENSE.md](vendor/REACT-BITS-LICENSE.md). Local lifecycle changes suspend animation offscreen and in hidden tabs, react to motion preference changes, and fail to the static dark surface when WebGL is unavailable. The wordmark similarly keeps its static fallback and immediate pointer-exit clearing.

Theme tokens: surface `#08090b`, paper `#121419`, ink `#f2f4f8`, muted `#a8b0bf`, focus/selection `#9cbaff`, separator `#ffffff20`. The header and hero edges meet at true black. Corners use control/field 8px, panel 12px and chip 4px; nested groups reduce the inner radius by the inset. Reserve capsule shapes for sliders and circles. Geist remains the display and body face. Working panels are opaque enough for readable evidence; spacing and tone replace redundant panel borders, and the animated field is limited to the opening.

The title stays sharp and solid at every pointer position. The oval optical lens, dotted hover mask and blue coordinate handles are removed. A separate white SVG rig uses six irregularly placed cubes, nine fine connections and neutral process labels. Its side mask fades the line work toward the page edges. These labels describe sourcing concepts rather than live search outcomes. Pointer events schedule one transform per animation frame; pointer exit, touch, blur, cancellation, hidden/offscreen contexts and reduced motion clear the rig. No wrapping library replaces native interactive controls.

Verification artifacts live under `frontend/.impeccable/review/dark-glass/` (not committed). The coordinating agent owns the consolidated frontend DESIGN.md and Figma record update after integration.
