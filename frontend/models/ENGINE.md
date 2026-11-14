# Prepared engine cutaway

The frontend uses `public/models/engine-cutaway.glb` for the compatible seeded
engine profile, including existing persisted runs whose manifest has no activated
GLB. An uploaded `asset.glb_path` always takes precedence. This is presentation
geometry only: no run, requirement set, component ID or source evidence changes.

## Source and preparation

The main cutaway is the premade [Innerscene turbofan quarter cutaway](https://www.innerscene.com/tools/library/3d-parts/turbofan-quarter-cutaway-e0184203),
released under CC0. Three small component studies come from the MIT-licensed
[Jet Engine Lab SolidCraft assets](https://github.com/AungMyoKyaw/jet-engine-lab/tree/07dc2651814ae4736f1ee2cbfd7f12c89d3b8b85).
The shipped source notice and full MIT license are in `public/models/licenses/`.
Pinned source hashes and mappings are recorded in `src/scene/prepared-engine.json`.

`prepare_engine.py` imports those existing meshes into Blender, converts axes,
preserves the seven module names, extracts representative study parts, adjusts
materials and authors a single reversible sequence: lift the casings, then spread
modules along the shaft. It saves an editable `.blend` with a studio camera and
exports actual keyed geometry animation to GLB. Runtime uses Anime.js scroll input
to seek those clips; direct controls and reduced motion remain available.

To rebuild with Blender 4.4.3, download the CC0 source from its official page and
check out the donor repository at the pinned commit, then run:

```sh
blender --background --factory-startup --python frontend/models/prepare_engine.py -- \
  /path/to/turbofan-cutaway.glb /path/to/jet-engine-lab
```

The recipe verifies all four source hashes before importing. No external source
scripts are executed. The exported asset is approximately 3.8 MB.

## Mapping limits

| Existing identity | Preserved node | Visual counterpart |
|---|---|---|
| component-primary | Component_FuelNozzle_07 | Premade atomizer tube/collar/tip study |
| component-secondary-a | Component_NGV_Segment_12 | Premade guide-vane study |
| component-secondary-b | Component_BleedDuct_HP | Premade bleed-port study |

These counterparts are illustrative; they do not establish OEM part identity,
numbered physical positions, dimensions or compatibility. The base educational
cutaway omits production detail and is not a complete engine BOM. Existing case
part numbers and evidence remain synthetic demonstration data. No arbitrary
blueprint reconstruction, manufacturing approval or operating-machine animation
is claimed.
