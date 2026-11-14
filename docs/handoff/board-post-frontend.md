# Board post: frontend delegation (to send once `gh auth login` is done)

Send with:

```bash
tools/board post "$(sed -n '/^---BEGIN---$/,/^---END---$/p' docs/handoff/board-post-frontend.md | sed '1d;$d')"
```

---BEGIN---
[Bede's Claude] @Borbezzz please ask your OpenAI agent to start on the frontend now. Bede wants it built with GPT-6 Astra (`gpt-6-astra`) for UI/UX and the 3D scene, and GPT Image 2.5 (`gpt-image-2.5-flare`, or `-sunburst` for precise edits) for imagery.

3D: the clickable engine must be real mesh geometry (PRD DISC-01). Use Blender (scripted bpy, GLB export) or Unity for asset generation where that helps, keeping the node names in `data/manifests/engine-demo-001.json`. Runtime stays React Three Fiber unless you decide otherwise.

Freedom to change: the demo flow and input parameters can be simplified or made more specific. Your agent may overwrite frontend decisions and the manifest, and may change the backend (`backend/**`, `contracts/**`, `data/**`) when the demo needs it. Keep `interface.md` and the tests green, and post contract changes here.

Start here: `docs/handoff/frontend-brief-astra.md`, `interface.md`, `contracts/generated-types/api.ts`, `status.md`, `decisions.md` (D-001: app model is OpenAI because the workspace has no Claude endpoint; please confirm). Backend runs locally: `cd backend && uv sync && uv run uvicorn recovery.api.app:app --port 8000`.

Ownership (AGENTS.md says you assign folders): proposal is your agent owns `frontend/**`. Use your own OpenAI build key, not the app's runtime key.
---END---$/p' docs/handoff/board-post-frontend.md | sed '1d;$d')"
```

---BEGIN---
[Bede's Claude] @Borbezzz frontend handoff request. Bede asked for the frontend to be built by your OpenAI agent.

Ask: could your agent build the React/TS/Vite workspace and the 3D engine in `frontend/**`? Please use GPT-6 Astra (`gpt-6-astra`) for UI/UX and the R3F scene, and GPT Image 2.5 (`gpt-image-2.5-flare`, or `gpt-image-2.5-sunburst` for precise edits) for presentation imagery. The clickable engine must stay real mesh geometry (PRD DISC-01).

Brief (models, image API params, 3D requirements, acceptance list): `docs/handoff/frontend-brief-astra.md`
Contract (routes, SSE events, state machines, manifest, demo mapping): `interface.md`, with types in `contracts/generated-types/api.ts`
Status and decisions: `status.md`, `decisions.md` (D-001: the app model is OpenAI rather than Claude, because the workspace has no Claude endpoint. Please confirm.)

Ownership: per AGENTS.md only you assign folders. Proposal: your agent owns `frontend/**`; Bede's Claude owns backend/contracts/data/rules/templates/deploy/tests/docs. Please confirm or adjust.

Use your own OpenAI build key for image generation, not the app's runtime key.
---END---
