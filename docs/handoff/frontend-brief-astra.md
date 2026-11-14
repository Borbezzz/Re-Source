# Frontend delegation brief: Re-Source workspace and 3D engine (GPT-6 Astra + GPT Image 2.5)

**To:** @Borbezzz's OpenAI coding agent · **From:** Bede's Claude (backend, contracts, data) · **Date:** 2026-11-14
**Status:** proposed. Folder ownership needs the team lead's confirmation per `AGENTS.md` §4.

## 1. What to build

The single-workspace React + TypeScript + Vite frontend for Re-Source (PRD §3), including the interactive 3D engine (PRD §2.2, §3.1, FR-01, DISC-01). The backend (FastAPI BFF, LangGraph agent, Databricks data layer) is built by Bede's Claude. You build against a typed contract and a real local backend running the seeded scenario.

Read first:
1. `PRD.md`: §2 demo script, §3 product experience, FR-01, §6.3 states, §11 non-functional requirements, AC-01/AC-14/AC-17.
2. `interface.md`: routes, SSE events, state machines, manifest format, UX requirements, demo mapping. **This is the contract.**
3. `contracts/generated-types/api.ts` (generated from `backend/recovery/domain/models.py`), and `contracts/openapi/openapi.json` once published.
4. `data/manifests/engine-demo-001.json`: engine modules, component node names, anchors, camera focus, removal vectors, failure stories.

## 2. Proposed ownership

| Owner | Folders |
|---|---|
| Borbezzz's OpenAI agent | `frontend/**`, including `frontend/public/generated/**` (generated imagery) and `frontend/PRODUCT.md`, `frontend/DESIGN.md` |
| Bede's Claude | `backend/`, `contracts/`, `data/`, `rules/`, `templates/`, `deploy/`, `tests/`, `docs/` (except frontend docs), `status.md`, `decisions.md`, `architecture.md`, `interface.md` |

- **Bede's explicit permission (2026-11-14):** the demo flow and its input parameters may be simplified or made more specific for the demo. Your agent may overwrite earlier frontend decisions, edit `data/manifests/` (anchors, node names, labels, failure stories), and change the backend (`backend/**`, `contracts/**`, `data/**`, `rules/**`, `templates/**`) whenever the demo needs it.
- When you change the backend: keep `interface.md` and `contracts/` regenerated (`cd backend && uv run python scripts/export_contracts.py`), keep `cd backend && uv run pytest ../tests -q` green (update tests that encode deliberately changed behaviour), add a line to `decisions.md`, and post the contract change on the board so Bede's Claude can rebase.

## 3. Using GPT-6 Astra well (research summary)

- **Model:** `gpt-6-astra` (OpenAI's frontend-strong model; used in Codex). Give it **references**: sketches, screenshots, existing UI, mood boards. It turns them into working UI and refines layout, typography, spacing, colour and interaction.
- **Durable context:** keep `frontend/PRODUCT.md` (users, jobs, demo script, must-show labels) and `frontend/DESIGN.md` (tokens, type scale, spacing, components, motion rules, 3D art direction). Ask Astra to *infer the underlying design system* from references rather than copy pixels.
- **Visual QA loop:** render, screenshot at **desktop (1440×900) and narrow (390×844)** widths, critique against DESIGN.md and the acceptance list below, fix, and repeat until another pass would not materially improve the result. Check reduced-motion mode in the same loop.
- **Division of labour:** one Astra worker owns quality-critical UI (the scene, recommendations, comparison view). A cheaper model may report screenshot defects but should not implement quality-critical UI.
- **Known weaknesses to guard against:** heavy token use (plan passes; use a lighter model for small fixes); some mobile/narrow-width bugs (always run the narrow-width pass); effect-heavy pages need a **reduced-effects mode** (also required by PRD §3.2 reduced motion).
- Optional and unofficial: the community skill `Enixes/astra-frontend-design` (prompt recipes, quality gates). Use it only if helpful. It is not an OpenAI product.

## 4. GPT Image 2.5: presentation imagery only

| Model | Use |
|---|---|
| `gpt-image-2.5-flare` (default snapshot `gpt-image-2.5-flare-2026-09-08`) | Fast, high-quality everyday generation: backgrounds, environment/HDR-style backdrops, matcaps, decals (e.g. crack overlay texture), icons, empty states, concept boards |
| `gpt-image-2.5-sunburst` | Precision edits and text-heavy concept boards (longer generation time) |

- **Images API:** `POST /v1/images/generations` with `model`, `prompt`, `n`, `size` (`1024x1024`, `1536x1024`, `1024x1536`, `auto`, or a custom `WxH` with both sides multiples of 16, aspect between 1:3 and 3:1, max edge 3840), `quality` (`low|medium|high|xhigh|max|auto`), `background` (`transparent|opaque|auto`; transparency needs `output_format` `png` or `webp`), `output_format`, `output_compression` (jpeg/webp), `partial_images` (0–3). The response image is `data[0].b64_json`.
- **Edits:** `POST /v1/images/edits` with `image` (one or more), optional `mask` (same size, with alpha) and `prompt`.
- **Responses API tool:** `tools: [{"type": "image_generation", "model": "gpt-image-2.5-flare"}]` with a mainline model such as `gpt-6-astra`. Use this to let Astra generate assets in-loop.
- Verify the alpha channel on transparent PNGs. Plan post-processing for seamless/tileable textures (not covered by the docs). Commit generated assets under `frontend/public/generated/` with a `PROMPTS.md` (prompt, model, size, date) for provenance.
- **Keys:** use your **own build key** for image generation. The app's runtime `OPENAI_API_KEY` is for the running product only and must not be used for building. Never commit keys or post them on the board (issue #1 is public).

## 5. The 3D engine: hard requirements

- The clickable engine **must be inspectable mesh geometry** (PRD DISC-01: "the clickable assembly requires an actual inspectable mesh structure"). Generated images may only dress the presentation (backdrop, reflections, decals).
- **Recommended approach:** procedural React Three Fiber geometry (`LatheGeometry` for casings, spinner, fan and compressor drums; instanced blades; `TubeGeometry` for the bleed duct and fuel manifold; `ExtrudeGeometry` for NGV segments and brackets), or a licensed GLB with separable meshes (record source and licence in `frontend/ASSETS.md`).
- **Blender or Unity for asset generation (allowed where it helps):** author or generate the engine in Blender (scripted with `bpy` so it is reproducible: keep the script in `frontend/assets-src/`, export glTF 2.0/GLB with Draco or meshopt compression, object names equal to the manifest node names, origin and scale in metres along +X) or in Unity (export GLB via glTFast/UnityGLTF with the same naming). The web runtime stays React Three Fiber per the PRD stack unless your agent decides otherwise and records why in `decisions.md`. GPT Image 2.5 output can feed Blender/Unity as textures, decals or reference boards, but never replaces the mesh.
- **Node names (exact):** modules `Module_Fan`, `Module_LPC`, `Module_HPC`, `Module_Combustor`, `Module_HPT`, `Module_LPT`, `Module_Exhaust`; components `Component_FuelNozzle_07` (primary), `Component_NGV_Segment_12` (secondary A), `Component_BleedDuct_HP` (secondary B). Use the manifest's `hotspot_anchor`, `exploded_offset`, `camera_focus` and `removal_vector`.
- **Stack:** `three`, `@react-three/fiber`, `@react-three/drei` (OrbitControls or CameraControls/Bounds for focus, `Html` for hotspot labels, `Outlines`/selection highlighting, `Environment`), `@react-three/postprocessing` only behind the reduced-effects toggle. Pin exact versions.
- **Domain-driven animation:** the scene renders `visual_state` from the API (`assembled → exploded → failed → removed → replacement_ready → installed → running`). It calls `POST /cases/{id}/visual-actions` and animates on the response and `visual.updated` events. It never fakes success locally. `install` is only enabled when `allowed_next` contains it, which happens after a simulated submission. The replacement part shown must correspond to the accepted candidate (`selected_candidate_id`).
- **Performance:** ≥ 30 fps during the main animation on a laptop. Use instancing, low draw calls, `frameloop="demand"` when idle, and no per-frame React re-renders of large trees.
- **Accessibility:** a keyboard-accessible component list mirrors the hotspots. 3D status has a text equivalent. Reduced motion means crossfades and a static camera.

## 6. Workspace panels (PRD §3.1)

Case overview · Activity panel (parallel BUY/MAKE tracks, tools, conclusions, evidence links, timestamps, expandable detail) · Recommendations (ranked eligible cards; pending and ineligible shown separately with gaps; route, part/revision, supplier/site, checks, reliability **labelled as scenario fixture**, price/currency, recovery time, risk, evidence coverage) · Change comparison (D1 | D2, trigger, impact path animation, changed fields/ranks, rerun vs reused checks) · Evidence inspector (title, revision/date, locator excerpt, extracted value, source link, retrieval time, applicable check) · Documents (route explanation, CAA Form 1 block layout, values and provenance, editable fields, completion tasks, review/approve, download, **SIMULATED** receipt) · Presenter controls (reset run, inject "Scenario signal", evidence change, clock advance, replay).

- Run SSE per case (`/cases/{id}/events?after=`). Dedupe by `event_id`, order by `sequence`, and reconnect with `Last-Event-ID`.
- Switching component must not leak state between cases.

## 7. Visual direction (suggestion)

Calm aerospace instrument-panel aesthetic: dark graphite or blueprint base, a single accent for focus, amber/red reserved for failure and risk, generous whitespace, and a legible tabular type scale for numbers (tabular figures). Status always pairs an icon with text (✓ pass, ✕ fail, ? unknown, ⏳ pending). The engine sits as the hero on the left or top; panels are on the right or below and stack at narrow widths. Motion is purposeful (explode, focus, impact-path pulse, part insertion) with a reduced-effects alternative.

## 8. Running against the backend

```bash
cd backend && uv sync && uv run uvicorn recovery.api.app:app --reload --port 8000
# new terminal
curl -X POST localhost:8000/api/v1/scenario-runs -H 'Content-Type: application/json' -H "Idempotency-Key: $(uuidgen)" -d '{"mode":"seeded"}'
```

Vite dev server: proxy `/api` to `http://localhost:8000`. For production, `npm run build` produces `frontend/dist`, which the BFF serves at `/` (single Databricks App). Set `RS_PACING_MS=350` for presenter-friendly pacing, or `0` for fast iteration.

## 9. Acceptance checklist

- [ ] **AC-01:** all three hotspots and list items work by pointer and keyboard, focus the correct mesh, open the isolated case, and survive switching and refresh.
- [ ] **AC-14:** replace/restore animations show the correct selected part, are gated by workflow prerequisites (`allowed_next`), and have working keyboard and reduced-motion paths.
- [ ] **AC-17:** no uncaught console errors; narrow viewport (390 px) usable end to end; full keyboard navigation.
- [ ] The §2.2 script runs end to end. Reset, then:
  1. engine and purpose
  2. explode and focus
  3. select the primary and show the failure animation
  4. start the investigation and watch parallel activity
  5. D1 ranked offers (A first)
  6. inject "Scenario signal" (D1 stays visible)
  7. impact path Port of Rotterdam → route → Offer A → case
  8. D2 beside D1 (B first; rerun vs reused checks)
  9. accept B
  10. document package with provenance and edits
  11. approve and run the simulated submission (receipt labelled SIMULATED)
  12. install and restore animation
  13. switch to a secondary case without losing primary history.
- [ ] The labels "Seeded/Live/Replay", "Scenario signal", "SIMULATED", "Synthetic demo data" and "Scenario fixture value" are visible where relevant.
- [ ] Explicit loading, working, waiting-for-evidence, interrupted, retry, complete and stale states.
- [ ] Screenshots at desktop and narrow widths saved under `docs/demo/` for the submission (PRD §13).
