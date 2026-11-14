# Re::Source dark material theme

Display branding only; repository names, domains, API and component IDs remain unchanged.

The opening uses the user's pinned direction: Re::Source in the supplied solid-to-dotted vector wordmark, on white PatternWaves `silk` over black, edge fade, pointer radius 50 and strength 0.6. The hero gives the wordmark room, then exposes Start demo and Upload blueprint as native buttons. The prepared assembly remains accessible below it.

`dark-glass.css` is the last stylesheet in `main.tsx`. It defines near-black working surfaces, pale body text, blue selection/focus, warm status colors and translucent controls. Glass is concentrated on navigation and controls through backdrop blur, a directional highlight, a soft edge and a restrained offset shadow. Buttons and ranges keep native semantics, focus, keyboard behavior and disabled state. This is a local CSS implementation informed by Apple's liquid-glass appearance and the researched `rdev/liquid-glass-react` reference; that library is not installed or represented as the implementation.

PatternWaves is the verified React Bits implementation by David Haz, requiring `ogl`. Its original presets, shader and interaction API are retained. Full upstream license: [vendor/REACT-BITS-LICENSE.md](vendor/REACT-BITS-LICENSE.md). Local lifecycle changes suspend animation offscreen and in hidden tabs, react to motion preference changes, and fail to the static dark surface when WebGL is unavailable. The wordmark similarly keeps its static fallback and existing immediate pointer-exit clearing.

Theme tokens: surface `#08090b`, paper `#121419`, ink `#f2f4f8`, muted `#a8b0bf`, focus/selection `#9cbaff`, separator `#ffffff20`. Geist remains the display and body face. Working panels are opaque enough for readable evidence; the animated field is limited to the opening.

The title's pointer lens uses a locally generated optical displacement map and an SVG backdrop filter in browsers that render it. A blur/highlight fallback keeps the material legible elsewhere. It has no animation loop: pointer events schedule one transform per animation frame; pointer exit, blur, cancellation, hidden tabs and reduced-motion changes clear it. The original wordmark rig independently clears when leaving the hero. No wrapping library replaces native interactive controls.

Verification artifacts live under `frontend/.impeccable/review/dark-glass/` (not committed). The coordinating agent owns the consolidated frontend DESIGN.md and Figma record update after integration.
