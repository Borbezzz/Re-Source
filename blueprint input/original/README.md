# Original Mechanica source

`Mechanica/` is the complete, unchanged tracked source snapshot of https://github.com/PouyanJay/mechanica at commit **a1d52be81b5e9ea125df337a3b30039ff996edc8**. All seven original engine families are included, not only our prepared turbofan. Git history and installed dependencies are excluded.

`Mechanica-SOURCE.json` records every original file's Git blob, SHA-256, byte size and mode. These were checked against the pinned source. Original licence and third-party notices are preserved inside the snapshot.

## Where to start

| Original file | Purpose |
|---|---|
| `Mechanica/components/engine/engine-scene.tsx` | Turbine-engine geometry and scene assembly; original viewer and picking. |
| `Mechanica/lib/engine/mechanical-engines.ts` | Additional engine builders and geometry helpers. |
| `Mechanica/lib/engine/engine-data.ts` | Seven engine definitions and component descriptions. |
| `Mechanica/lib/engine/explosion-controller.ts` | Individual-piece separation, selection and restoration. |
| `Mechanica/lib/engine/explosion-layout.ts` | Inventory-layout packing. |
| `Mechanica/lib/engine/section-*` | Cutaway planes and rendering. |
| `Mechanica/README.md`, `Mechanica/docs/` | Original architecture, interaction and development documentation. |
| `Mechanica/package.json`, `Mechanica/package-lock.json` | Original application dependencies and commands. |

To create a different package, work on a copy or a separately owned implementation branch. Choose an engine and geometry, export a GLB with persistent IDs, map selected components, prepare honest buyer-defined requirements and validate the round trip. Use our `tools/export-package.ts` as a turbofan-only adaptation example; it is not a generic exporter for all seven engines.

The original app stack and hosting configuration are reference material. Importing the whole application is not required to reuse its geometry. Inspect original scripts and dependencies before executing them; none of its full install/build/deploy scripts were run for this package.

Keep original notices with derivatives. Geometry is an educational reference, not manufacturing CAD or OEM-approved engine specifications.
