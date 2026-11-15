# Complete prepared sourcing inventory — 15 November 2026

Package 1.2 maps all 1,835 independent model pieces to explicit sourcing specifications. The 69 added families cover 508 previously unmapped pieces: retaining rings, fasteners, compressor/turbine/nozzle housings, casing tubes and shaft vanes. The package has 104 sourcing cases, including the retained nozzle assembly case. Repeated instances of one exported source mesh share a fixture identity; attached surface details remain part of their parent.

The backend fixture contains 838 sample offers. All parts use the existing simulated sourcing workflow. Small hardware has its own fixture pricing instead of inheriting the enclosing assembly's price. Blue availability dots and their legend are removed. Mixed assembly groups direct users to expand and select a part; they do not invent a single procurement identity for different parts.

Part confirmation accepts up to 200 reviewed parts so the full 104-case package can be confirmed through the API. The per-request investigation list limit remains 50; Studio requests the selected part only. No live providers or external outreach were added.

## Verification

- Production build/typecheck and 25 frontend tests pass.
- Full backend suite: 267 passed, four live-provider tests skipped. Tests confirm all 104 parts through the actual API, execute demo research jobs for all 104 cases, check candidate provenance and part scoping, and complete a new-stage simulated RFQ/approval flow.
- GLB round-trip, file hashes, all-piece sourcing coverage, CSV/manifest/requirements consistency and ZIP CRC checks pass. Frozen-build version and contradictory-CSV guards pass.
- Browser checks cover the ZIP upload, newly sourceable rings/housings/nozzle pieces/fasteners, eight fastener supplier sites, absent blue badges, group/individual hover, selection callouts, map widening and mobile interaction.

The source remains the MIT-licensed prepared Mechanica geometry. Part identities, requirements, prices and supplier offers are demonstration data; no OEM applicability or manufacturing acceptance is established. Uploading this version is necessary to expose the new per-piece mappings; older ZIPs retain their older manifest mappings.
