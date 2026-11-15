# Re::Source — prepared Mechanica demo package

This is the approved Mechanica direction made concrete: a real exported GLB, 35 mapped demo sourcing families, buyer-defined demo requirements and an implementation handover. Package 1.1 adds individual occurrence browsing and compressor/turbine stages. Start with **[HANDOVER.md](HANDOVER.md)**.

## Folder map

- **[original/Mechanica](original/Mechanica/)** — complete unchanged original source for all seven engine families, so teammates can build their own version. See [source map and guidance](original/README.md).
- **[input-package](input-package/)** and **[mechanica-input-package.zip](mechanica-input-package.zip)** — our prepared recommended upload.
- **[tools](tools/)** — our turbofan exporter, frozen geometry adapter and validation tooling.
- **[alternative/Jet Engine](alternative/Jet%20Engine/README.md)** — Jet Engine Lab findings, checks and pinned source links.
- **[alternative/KJ66](alternative/KJ66/README.md)** — existing STEP CAD, document sources, checks and remaining work.
- **[DESIGN-FLOW-SUMMARY.md](DESIGN-FLOW-SUMMARY.md)** — concise approved product journey and inputs.
- **[Approved frontend references](../frontend%20improve/README.md)** — screenshots, visual language and workflow references already in the team repository.

## Give the build agent

- **`mechanica-input-package.zip`** — the file to upload in the demo. Its root contains `assembly.glb`, `components.csv`, `requirements.json`, `manifest.json` and licence/attribution notices.
- **This handoff folder** — includes instructions, source provenance, reproducible tools, validation results and a package inspector.

| Case | Component ID | Demo part / revision | Quantity in assembly |
|---|---|---|---:|
| **Primary: front fan blade 01** | `RS-TF-FAN-BLADE` | `RS-DEMO-FB-001` / B | 24 |
| Secondary: fuel injector 01 | `RS-TF-FUEL-INJECTOR` | `RS-DEMO-FI-001` / C | 18 |
| Secondary: core exhaust nozzle assembly | `RS-TF-CORE-NOZZLE` | `RS-DEMO-NZ-001` / A | 1 |

The injector is deliberately a simplified original Mechanica shape; the blade has the stronger close-up geometry. Assembly quantity is not purchase quantity. The 24 blades and 18 injectors now have explicit shared family specifications; the browser can inspect and highlight each occurrence separately. Additional demo families cover fan guide vanes/spinner, nine compressor rotor and eight stator stages, five turbine rotor and four stator stages, liners, fuel tubes, casing sections, and shafts. Details without a fixture specification remain inspection-only.

## Inspect locally

The prepared input ZIP needs no dependency installation. To use the optional inspector or rebuild tools, use Node 24 (tested with 24.14.0), then from this folder:

```sh
npm ci --prefix tools --ignore-scripts --no-audit --no-fund
node tools/validate-package.mjs
python3 -m http.server 8768 --bind 127.0.0.1
```

Open `http://127.0.0.1:8768/preview.html`. Test component buttons, model clicks, casing, explosion and reassembly. Stop the local server with Ctrl-C. The inspector is a utility, not the approved final website layout.

To rebuild the data, run `node tools/export-package.ts`, `python3 tools/sync-demo.py`, then `node tools/validate-package.mjs`. The sync step updates the backend profile, extra fictional map sites, public GLB and both ZIP copies. Increment `tools/package-config.json` before changing the exporter. The pinned upstream source snapshots are retained under `tools/vendor/` for inspection, not installation as a full application.

## What is real and what is prepared

The geometry is derived from Mechanica's MIT-licensed procedural turbofan at commit `a1d52be81b5e9ea125df337a3b30039ff996edc8`. The GLB has **1,835 independent pieces and 240 attached surface details**, flattened into 2,075 mesh occurrences to preserve picking without instancing extensions. No external textures or buffers are needed.

This is a **prepared visualization assembly**, not manufacturing CAD or an OEM engine package. Its physical scale has not been validated. Part numbers, revisions and buyer requirements are fictional demo fixtures. Model-derived bounds are recorded in visualization units; no physical tolerances or material grades are invented. Applicable approval/traceability evidence still has to be supplied or requested by the product workflow.

The final website should say **“Upload design package”** and **“Preparing assembly”**. This package reveals a matching prepared model; it does not demonstrate arbitrary CAD generation. Supplier discovery, qualification, risks, paperwork and Databricks integration are work for the product agent, not features already implemented here.

See [verification](verification/README.md), [source provenance](source-provenance.json), [package contract](PACKAGE-CONTRACT.md) and [Mechanica licence](LICENSE-Mechanica.txt).
