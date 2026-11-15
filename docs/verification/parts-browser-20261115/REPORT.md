# Grouped assembly browser and stage demos — 15 November 2026

The Studio now exposes the uploaded GLB as seven expandable sections containing 1,835 independent pieces. Fan blades and injectors expand into 24 and 18 occurrences. Compressor and turbine blade/vane families retain their stage boundaries. Decorative liner details remain attached to their parent instead of becoming separate purchasable parts.

Hovering or focusing a row previews its exact node set. A cyan x-ray material reveals occluded blades without changing selection or starting a request. Pointer exit, Escape, window blur and hiding the document clear the preview. Clicking a leaf focuses that occurrence; family identity and selected geometry remain separate for sourcing and replacement animation. Touch uses expand/select controls.

Package 1.1 defines 35 explicit fictional sourcing families. All seven sections have sourcing cases, including nine compressor rotor/eight stator stages and five turbine rotor/four stator stages. Fasteners and other pieces without defined requirements remain inspection-only. The GLB is prepared geometry, not a drawing reconstruction or manufacturing model.

Three additional fictional suppliers in Montréal, Singapore and Rzeszów provide varied stock, pricing, transit times and missing-evidence examples. They appear in every case. The fan-blade scenario now has 15 sites; new stage cases have eight. Discovery reveals the returned sample candidates progressively and automatically widens a global map, reserving room for the checks panel even in split view. User pan/zoom overrides automatic framing. The panel says “Demo sourcing agent”. No live-provider or real-email behavior was introduced.

## Verification

- Production build and typecheck pass; 24 frontend tests pass.
- Backend: 266 passed, four existing live-provider tests skipped.
- All 35 cases pass confirmation and actual backend research jobs using prepared offers. A new compressor-stage case passes selection, RFQ, approval and simulated fulfilment.
- Two actual Chrome browser scenarios pass: desktop group/individual hover, keyboard focus/Escape, selection isolation, zero hover-triggered API mutations, new stage research, eight map pins and more than 2× widening during discovery; mobile upload, expansion, touch selection, return and no horizontal overflow.
- Model/manifest/CSV/requirements hashes and GLTFLoader round-trip validation pass for all 35 mappings. Version guards and contradictory-CSV regression checks pass. ZIP CRC and both distributed ZIP copies match.
- Rebuilt on `11b2624`, preserving the team's interactive map changes. No API schema changes.

## Reproduce

From the repository root:

```sh
npm ci --prefix 'blueprint input/tools' --ignore-scripts
node 'blueprint input/tools/export-package.ts'
python3 'blueprint input/tools/sync-demo.py'
node 'blueprint input/tools/validate-package.mjs'
python3 'blueprint input/tools/check-regressions.py'
npm --prefix frontend run build
npm --prefix frontend test
```

With an isolated local backend and the Vite proxy running, execute `RESOURCE_BASE_URL=http://127.0.0.1:5198 RESOURCE_BROWSER_CHANNEL=chrome RESOURCE_HEADED=1 npx playwright test e2e/parts-browser.spec.ts` from frontend. Browser checks inspect the development scene's actual mesh materials, not a mocked selection model.

The importer still uses the prepared backend profile, and does not transfer arbitrary changed upload requirements. Studio's downstream qualification/disruption presentation and fulfilment remain demonstration behavior. These limitations are unchanged and should not be described as live supplier validation.
