# Upload and sourcing rendering performance

Verified on 2026-11-15 against baseline `6783ecc`, using the same Mechanica ZIP, Chrome, 1440 × 900 viewport, and Apple M4 Pro Metal renderer. Local API ran with isolated test storage and demo data. These are short local samples, not guaranteed frame rates on other devices.

| Three-second sample | Before | After |
| --- | ---: | ---: |
| Upload scan: browser animation frames/sec | 5.6 | 60.2 |
| Upload scan: 95th percentile frame interval | 400 ms | 16.7 ms |
| Settled assembly: GPU draw calls in sample | 375,575 | 0 |
| Sourcing transition: browser animation frames/sec | 21.9 | 47.5 |
| Sourcing transition: 95th percentile frame interval | 150 ms | 33.4 ms |

The animation-frame sampler ran from the confirmation-ready upload screen, then the settled assembly, then immediately after supplier discovery became visible. WebGL draw calls were counted by instrumenting `drawElements`, `drawArrays`, and their instanced equivalents. Raw samples are in `before.txt` and `after.txt`.

The full model still contains **2,075 meshes, 141 shared geometries, and 1,732,128 triangles**. Repeated solid parts and thumbnails share instanced draw calls, with original object identities used for selection. Transparent highlights retain individual sorting. The upload scan uses five-degree technical edges (419,374 lines across every part) instead of all triangulation seams; the thermal sweep and original solid geometry remain. Settled scenes stop requesting frames and resume for camera motion, selection, explode/assemble, or reassembly. Moving-part bounds are cached. The flow clock is isolated from the graph, camera movement reuses graph contents, and static map geography paints separately from animated overlays.

Validation:

- `npm test`: 30 passed, including geometry preservation, per-part raycasting, moved/hidden selection, scan transforms, and shared-resource cleanup.
- `npm run build`: TypeScript and production bundle passed; existing large-chunk advisory remains.
- `RESOURCE_BASE_URL=http://127.0.0.1:5175 RESOURCE_BROWSER_CHANNEL=chrome npx playwright test e2e/parts-browser.spec.ts e2e/render-performance.spec.ts`: 3 passed, 58.5 seconds.
- Browser coverage: group and individual highlights, keyboard focus, mobile touch, progressive map framing, idle rendering, rotation, explode/assemble, flow view switching, demo enquiry approval/send, part removal/insertion, and return to assembly. No browser errors in the full journey.
- Visually checked the scan, solid assembly, highlighted blade, supplier map/thumbnail, and completed reassembly.

The existing local API on port 8000 rejected product creation with HTTP 405. Verification used a fresh API on 8012 and frontend on 5175; this change does not modify backend behavior or deploy production.
