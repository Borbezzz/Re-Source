# ReSource frontend

React + TypeScript + Vite, React Three Fiber and Anime.js. Design source: [shared Figma file](https://www.figma.com/design/o4G1HFAyQybcPuBG1nV2lL). The implementation follows `briefs/workspace.md`; server payload types come from `../contracts/generated-types/api.ts`.

```sh
npm ci
npm run dev       # Vite 5173; /api proxies to backend 8000
npm run build     # typecheck and production bundle
npm test          # client, event and mesh invariants
npx playwright test # running Vite/backend required
```

The interface integrates blueprint + part-requirements upload, cited extraction review, mesh validation/activation, component investigation, supplier map/compare/evidence, versioned approval and simulated submission. Seven illustrative engine modules contain the three stable component identities in the backend manifest. Click meshes, projected labels or the keyboard-accessible list. Scroll explodes/reassembles the scene; direct controls and reduced-motion mode remain available. Repair install/restore actions use server gates.

Blueprint-to-mesh generation is **unavailable until a provider is connected**. The procedural demo and illustrative intake render are labelled. Imported GLBs require structural validation and source identity review; the frontend adds a source-confirmation guard, which is not engineering approval. Backend structural validation alone cannot prove a source mapping is semantically correct.

Uploaded identity/revision affect current checks; uploaded material, dimensions, tolerance and certification requirements currently need separate manual evidence review. Their compatibility is unknown until implemented in the rules. Live public leads do not turn synthetic offers into real quotes. Costs are estimates and receipts are simulation-only.

Uploads currently accept at most 4 MB. `deploy/vercel/README.md` documents public hosting, server configuration and remaining verification. No API secrets belong in this package. Lazy-load the 3D runtime and supplier map; fonts are self-hosted.
