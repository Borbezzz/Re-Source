# Agent message board

Follow `AGENTS.md` at the repo root. It is the shared workflow for every coding agent on this repo (Copilot, Cursor, Claude Code, Codex, and others).

- The group chat is the "Message Board" GitHub issue. In this repo that is issue #1: https://github.com/Borbezzz/Re-Source/issues/1. Talk to it only through `tools/board`. `BOARD_ISSUE` defaults to `1`.
- Every post starts with `[<human>'s <agent>]`. Mention teammates by GitHub login (`@Borbezzz`, `@bede-lau`, `@alvinbong03`) or `@all`.
- Run `tools/board unread` at the start of a task, before each commit, and after merges. Commands: `unread`, `read -n 20`, `post`, `wait`, `whoami`.
- Reply when a post mentions your human or `@all`. Otherwise read it and change course only if it affects your files or a contract you own.
- Edit only the folders in your row of the `AGENTS.md` owner table. Ask on the board before touching someone else's folders. Only the team lead, `@Borbezzz`, reassigns work.
- Branch `<issue#>-<slug>` from fresh `main`. Stage only your own files. PRs include `Closes #N`. Fetch and rebase before pushing. Never force-push a shared branch. Post on the board when an API, schema, or env var changes.
