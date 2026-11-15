# Workflow entry performance

Combined verification of the existing rendering optimization, cold-start follow-up, and supplier-map camera change on 2026-11-15. The terminal agent reviewed workflow/map startup read-only through issue #1; the rendering chat owned scene changes; the coordinating chat measured and integrated the map change.

The map now frames each returned result batch once, while supplier pins continue to appear progressively. Discovery and checking reserve the same side-panel space. A pin appearing no longer restarts a 1.1-second zoom every 160 ms, and entering checking no longer triggers an unnecessary camera refit. All 50m coastline detail, supplier locations, routes, pan, zoom, and keyboard controls remain.

The rendering follow-up reuses model preparation when metadata arrives, yields scan-outline preparation in small batches, freezes the hidden engine drawing buffer, and measures thumbnail layout size independently of animated transforms. See the sibling `render-startup-20261115` report for isolated scene measurements and regression assertions.

## Combined local measurement

Fresh headed Chrome, 1440 × 900, 120 Hz display, normal motion, local fixture API, actual prepared ZIP and an individual fan blade. Sampling starts on the **Find suppliers** click, before map mounting. CDP CPU/timeline profiling was enabled in both runs; Chrome profiling runs were serialized across agents. These are local observations, not guaranteed rates on other machines.

| Time after click | Before: frames in that second | Combined: frames in that second | Before p95 gap | Combined p95 gap |
| --- | ---: | ---: | ---: | ---: |
| 0–1 s | 44 | 66 | 40.8 ms | 41.7 ms |
| 1–2 s | 47 | 112 | 33.2 ms | 16.6 ms |
| 2–3 s | 59 | 112 | 33.4 ms | 16.6 ms |
| 3–4 s | 81 | 114 | 25.0 ms | 16.4 ms |
| 4–5 s | 108 | 114 | 16.7 ms | 16.6 ms |

Main-thread long tasks fell from 90/133/67 ms to one 101 ms task attributable to cold thumbnail WebGL context creation. The initial GPU-context hitch is not claimed to be eliminated; the sustained camera/resize slowdown is reduced. No page errors occurred. Raw samples are `before.json` and `after.json`.

Validation: production build, all 38 frontend unit tests, grouped/individual selection and mobile browser checks, the full enquiry/reassembly journey, and provider-provenance/error-path browser checks. Backend behavior is unchanged.
