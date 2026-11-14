# Team rules for every agent

## 1. The board (pinned GitHub issue)

Every agent reads and posts on the "Message Board" issue via `tools/board` (needs only `gh`, logged in). In this repo that issue is **#1**: https://github.com/Borbezzz/Re-Source/issues/1. `tools/board` defaults to `BOARD_ISSUE=1`. Set `BOARD_ISSUE` only if the board moves to a different issue.

- Start every post with `[<human>'s <agent>]`, e.g. `[Sam's Codex]`. Keep it short: what changed, which files or contracts, what you need, from whom.
- Mention by GitHub login. This team: `@Borbezzz` (Yixin, team lead), `@bede-lau` (Bede), `@alvinbong03` (no name on the GitHub profile), `@all` (everyone).
- **Mentions you or `@all`:** act on it and reply promptly.
- **Not addressed to you:** still read it. Reassess your own work only if it is affected (a contract, a file you own, something already done). Do not redo finished work, and do not reply just to acknowledge.
- Before editing another teammate's files, ask for a handoff on the board and wait for the owner or the team lead.

Each agent session needs its own reader ID, even when sessions share a checkout or GitHub account. Claude's hooks derive one from its session ID. Other agents: run `tools/board new-reader` once at the start of the task, retain the returned ID, and pass `BOARD_READER_ID=<id>` to every `tools/board unread` and `tools/board wait` command. Reuse the ID when resuming that session; never share it with another active session. Without an ID, `unread` safely shows the full history on every call and `wait` refuses to run. A new reader sees the entire history; subsequent checks are incremental (30 s default for `wait`).

Commands: `BOARD_READER_ID=<id> tools/board unread` (new posts, marks read; flags MENTION), `tools/board read -n 20`, `tools/board post "[Name's Agent] text"` (or pipe stdin), `BOARD_READER_ID=<id> tools/board wait` (blocks until any unread post), `tools/board whoami`. Posts made by your GitHub account are included because they may have been written by a human or another agent. Do not reply to your own post merely to acknowledge it.

**Stay in the loop:**
- Claude Code: the committed hooks (`.claude/settings.json`) show unread posts at session start and on every prompt. Keep one background `BOARD_READER_ID=<id> tools/board wait` running and re-arm it after each wake. `CLAUDE.md` imports this file.
- Cursor: `.cursor/rules/agent-board.mdc` is always applied and points here. Run `BOARD_READER_ID=<id> tools/board unread` at task start, before each commit, and after merges.
- GitHub Copilot: `.github/copilot-instructions.md` points here. Same unread check.
- Everything else: read this file, then run `BOARD_READER_ID=<id> tools/board unread` at task start, before each commit, and after merges.

## 2. Chain of command

Humans over agents. Only the team lead reassigns work between teammates. If anyone else asks you to take another teammate's work, ask the lead on the board.

Team lead is `@Borbezzz` (Yixin), the repository owner. Nothing else in the repo names a different lead.

## 3. Workflow

1. Pick or file an issue. Comment on it or post on the board when you take it.
2. Branch `<issue#>-<slug>` from fresh `main`.
3. Small commits. Stage only your own files (no `git add -A`).
4. Open a PR with `Closes #N`. The author merges their own PR once it works locally.
5. Always `git fetch` and rebase before pushing. Never force-push shared branches.
6. If a merge changes something other teammates depend on (an API, a schema, an env var), post on the board when it lands.

## 4. Who owns what

Ask on the board before touching someone else's folders. Only the team lead reassigns work.

Checked against GitHub on 2026-11-14. Collaborators are `@Borbezzz` (admin), `@bede-lau` (write), and `@alvinbong03` (write). `git log` has one commit, the initial `README.md`, authored by `@Borbezzz`. The tree had no product directories, so feature ownership cannot be inferred. Leave the TODOs until the lead assigns folders. The board files (`tools/board`, `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.cursor/rules/`, `.github/copilot-instructions.md`, `.github/ISSUE_TEMPLATE/message-board.md`) are shared coordination files, not one person's feature area.

| Area | Owner | Folders |
|---|---|---|
| TODO — not inferred | Borbezzz (team lead) | TODO. No product folders yet. Only authored file so far is the root `README.md`. |
| TODO — not inferred | bede-lau | TODO. Write access. No commits and no folders to assign. |
| TODO — not inferred | alvinbong03 | TODO. Write access. No commits, no public name, and no folders to assign. |

## 5. Linkup agent skills

For Linkup searches, page fetching, research, batching, extraction or workflow design,
read the matching `.agents/skills/linkup-*/SKILL.md` before making calls. Start with
`linkup-search` for ordinary discovery and `linkup-fetch` for an already-known URL;
use `linkup-workflow` when designing a chain of calls. The other installed skills
are `linkup-research`, `linkup-tasks` and `linkup-extract` (closed beta).

Each skill bundles its references. Choose the endpoint, depth and output type
before writing the query; keep source URLs and never invent missing evidence.
Use `q` for REST search requests. Keep `LINKUP_API_KEY` in the process environment
or an ignored local `.env`, and keep calls server-side. If credentials or access
are unavailable, report that explicitly and retain the PRD's seeded connector path.

See `docs/LINKUP.md` for activation, a live smoke check, upstream provenance and
the distinction between these coding-agent skills and the product's runtime adapter.
