# Cold 3D startup and sourcing entry

Follow-up to `dda3ae4`, profiled against the merged baseline `7ea27db` on 2026-11-15. Scope is the engine renderer, thumbnail and rendering tests; graph/map changes are owned by the coordinating chat.

## Measured causes and changes

- The package's component metadata arrives after its model URL. Previously both arrivals rebuilt the scene, scan outlines and materials. `usePrepared` now binds metadata to the existing scene. The browser regression asserts one prepared model identity through upload confirmation.
- `EdgesGeometry`/`ScanLines` preparation produced two synchronous upload tasks of 164 ms and 155 ms. The duplicate build is removed, and the remaining build yields between approximately 8 ms batches. The existing processing stage waits for completion. Cancellation prevents an abandoned upload from continuing to allocate resources.
- The engine stays mounted but hidden during sourcing. The split panel's animated width still resized its WebGL drawing buffer. Hidden canvases now retain their last visible dimensions and resume responsive sizing when shown. The browser regression asserts zero hidden renderer resize calls during sourcing entry.
- Thumbnail measurements followed the card's animated CSS scale, producing another drawing-buffer resize stall. `offsetSize` measures the actual layout size instead. The final trace retained a 74 × 56 content buffer throughout the transition, at unchanged DPR.
- Memoized environment children avoid repeating cube-map capture on progress updates. Thumbnail rendering is memoized too. Resolution, materials, model triangles, picking, selected-only callouts and reassembly are retained.
- Shader compilation was measured but did not explain the long tasks. No speculative shader warm-up or quality reduction was added.

## Cold samples

Fresh headless Chrome processes, 1440 × 900 viewport, Apple M4 Pro Metal renderer, local dev build and the same Mechanica package/API. Upload covers file selection through confirmation readiness. Sourcing covers the first five seconds after the Find suppliers action, including its initial mount and animation. Profiles were serialized with `/tmp/resource-startup-profile.lock`. These frame intervals describe this local sample, not a universal refresh-rate target.

| Measurement | Before | Final |
| --- | ---: | ---: |
| Upload readiness | 3,755 ms | 3,688 ms |
| Upload worst frame interval | 166.6 ms | 33.4 ms |
| Upload long tasks over 50 ms | 164, 155 ms | None |
| First 5 s sourcing worst frame interval | 100 ms | 50 ms |
| First 5 s sourcing 95th-percentile interval | 33.3 ms | 33.3 ms |
| First 5 s sourcing long tasks over 50 ms | 118, 51 ms | None |

Raw summarized samples: `before.json` and `final.json`. CDP CPU profiling, animation-frame timestamps, PerformanceObserver long tasks, and canvas drawing-buffer setters were used to attribute stalls. Remaining map/graph layout and paint costs are separate work; these changes target main-thread rendering stalls, not all frame-budget usage.

## Checks

- 38 frontend tests pass, including new deferred preparation equivalence/cancellation tests.
- TypeScript and production build pass (existing bundle-size advisory remains).
- Desktop group/individual/keyboard selection, mobile touch and full enquiry/reassembly browser tests passed together (3 tests, 58.1 s).
- The final thumbnail measurement change was additionally checked with the full enquiry/reassembly test. That test includes rotation, explode/assemble, flow view switching, the one-model-identity assertion and the zero-hidden-resize assertion.
- No graph/map/provider/API files were edited. Release, push and deployment remain with the coordinating chat.
