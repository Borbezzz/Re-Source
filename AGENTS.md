# Team rules for every agent

## Session start

Once at the start of every session, before other work, help your human keep a board watcher running. Say it once. Do not repeat it on later messages in the same session.

1. Run `tools/board whoami`. If it fails, `gh` is not logged in. Walk your human through `gh auth login`, then run `tools/board whoami` again. Stop board work until it prints their GitHub login.
2. Check that a watcher is running.
   - Claude Code: the hooks in `.claude/settings.json` show unread posts and keep a background wait. Do not ask for a second terminal unless those hooks did not run.
   - Any other agent: if nothing is watching, tell your human to open a separate terminal and paste:

     ```
     tools/board watch
     ```

     That command creates a reader, waits for new posts, prints them, and beeps (twice, with a `MENTION` line, when the post tags their login or `@all`).

     To wake their agent CLI with those posts on stdin, paste the matching line instead:

     ```
     tools/board watch -- claude -p
     tools/board watch -- codex exec -
     tools/board watch -- sh -c 'agent -p "$(cat)"'
     tools/board watch -- sh -c 'copilot -p "$(cat)"'
     ```

     Claude Code (`claude -p`) and Codex (`codex exec -`) read stdin as the prompt. The Cursor CLI (`agent`) and Copilot CLI (`copilot -p`) take the prompt as an argument, so the `sh -c` form puts stdin there.

     The same loop without the helper, after one reader id:

     ```
     export BOARD_READER_ID="$(tools/board new-reader)"
     while posts="$(tools/board wait)"; do printf '%s\n' "$posts" | <agent cmd>; done
     ```

Still run `BOARD_READER_ID=<id> tools/board unread` at task start, before each commit, and after merges.

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
