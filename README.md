# Re-Source

The current product workspace supports a toy car, engine, table lamp or uploaded
design package. Its sourcing agent checks specifications, researches suppliers,
prepares quote requests and presents recommendations in one continuous flow.
The built-in mailbox uses explicitly simulated messages and sample replies;
real email delivery needs an authorized account and verified recipients. See the
[current product flow](docs/product-v2/DEMO-AND-LIVE.md) and
[agent outreach contract](docs/product-v2/AGENT-OUTREACH.md).

**Aerospace recovery agent.** When a jet-engine component fails, Re-Source finds replacement options, compares buying a spare (BUY) with commissioning manufacture (MAKE), checks the evidence (technical applicability, supplier and site suitability, UK CAA route), ranks the eligible plans transparently, and prepares the selected route's paperwork. When a monitored risk signal or a piece of evidence changes, it traces the impact through an explicit evidence graph, re-runs only the affected checks and shows how the recovery plan changed (D1 → D2).

- Specification: [`PRD.md`](PRD.md) (v1.2)
- Build status and how to resume: [`status.md`](status.md)
- Decision log: [`decisions.md`](decisions.md)
- Architecture: [`architecture.md`](architecture.md)
- Frontend ↔ backend contract: [`interface.md`](interface.md) (schemas in [`contracts/`](contracts/README.md))

> All suppliers, part numbers, approval references and reliability figures in the seeded scenario are **synthetic demo data**. Simulated submissions never reach a real authority.

## Stack

FastAPI BFF (Python 3.12, uv) · LangGraph orchestration with a persistent checkpointer · Databricks (SQL warehouse, Delta `workspace.resource.rs_*`, `ai_extract`, MLflow 3 tracing) · OpenAI Responses API for explanations and extraction fallback · Linkup search and Companies House adapters · OR-Tools CP-SAT for recovery scheduling · React + TypeScript + Vite + React Three Fiber frontend · Vercel Services and Queues for public application hosting (see [`deploy/vercel/README.md`](deploy/vercel/README.md)).

## Repository layout

```text
backend/recovery/{api,domain,agents,adapters,runtime,services}   FastAPI BFF, domain rules, graph, adapters
backend/scripts/                                                  contract export and tooling
contracts/{schemas,openapi,generated-types}                       generated from backend/recovery/domain/models.py
data/{manifests,fixtures,ingestion,evidence-inventory}            engine manifest, seeded scenario (seed-v1), Delta loader
rules/{requirements,applicability,ranking}                        versioned requirement sets, UK CAA catalogue, ranking config
templates/{registry,fields,renderers}                             document template registry
frontend/                                                         workspace UI and 3D scene (frontend owner)
deploy/{vercel,databricks,resources}                              Public deployment and retained platform resources
tests/{unit,integration,e2e,evaluations}                          tests and MLflow evaluation scorers
docs/{decisions,verification,demo,handoff}                        verification records, demo script, handoffs
```

## Quick start (backend)

```bash
cd backend
uv sync
cp ../.env.example ../.env        # fill in values locally; .env is gitignored, never commit or post keys
uv run python ../data/fixtures/build_seed.py
uv run uvicorn recovery.api.app:app --reload --port 8000
```

Then open `http://localhost:8000/api/v1/engines/engine-demo-001`. `RS_MODEL_ENABLED=false` and `RS_DATABRICKS_ENABLED=false` run the app fully offline with deterministic fallbacks. Tests: `uv run pytest -q`. Contracts: `uv run python scripts/export_contracts.py`.

## Agent message board

Teammate coding agents coordinate on one GitHub issue, using [`tools/board`](tools/board). The rules and the owner table are in [`AGENTS.md`](AGENTS.md). Setup is copied from [azizu06/hackathon-agent-board](https://github.com/azizu06/hackathon-agent-board). Walkthrough: [marvelous-relative-5de.notion.site/hack](https://marvelous-relative-5de.notion.site/hack).

Hookup, once per person:

1. `gh auth login`
2. `tools/board whoami`
3. The board is [issue #1](https://github.com/Borbezzz/Re-Source/issues/1). `tools/board` already defaults to issue #1, so set `BOARD_ISSUE` only if that number changes.
4. Each agent session needs a distinct reader ID. Claude Code hooks derive it automatically. Other agents run `tools/board new-reader` once, keep the returned ID for that session, and prefix each unread or wait command with `BOARD_READER_ID=<id>`. New readers receive the full history; posts from the same GitHub account are included. Without an ID, `unread` displays the full history on every call and `wait` refuses to run.

Claude Code loads [`CLAUDE.md`](CLAUDE.md), Cursor always applies [`.cursor/rules/agent-board.mdc`](.cursor/rules/agent-board.mdc), and Copilot reads [`.github/copilot-instructions.md`](.github/copilot-instructions.md). Other agents follow `AGENTS.md` and run `BOARD_READER_ID=<id> tools/board unread` before each task.

Issue #1 is pinned and has the `board` label.

## Frontend

Run `npm ci && npm run dev` in `frontend/` with the backend on port 8000. The default `#home` route is the new **Re::Source Studio** (`frontend/src/studio/`): the approved 10-screen journey on the prepared Mechanica turbofan package (see `status.md` → Local UI revamp). If port 8000 is taken, run the API on another port and set `RS_API_TARGET=http://127.0.0.1:<port>` for `npm run dev`. See [`frontend/README.md`](frontend/README.md) for build, tests, Figma and current contract limits. Public hosting is Vercel for both frontend and API (D-019); the retained Databricks App is not the public target.
