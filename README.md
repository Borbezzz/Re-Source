# Re-Source

## Agent message board

Teammate coding agents coordinate on one GitHub issue, using [`tools/board`](tools/board). The rules and the owner table are in [`AGENTS.md`](AGENTS.md). Setup is copied from [azizu06/hackathon-agent-board](https://github.com/azizu06/hackathon-agent-board). Walkthrough: [marvelous-relative-5de.notion.site/hack](https://marvelous-relative-5de.notion.site/hack).

Hookup, once per person:

1. `gh auth login`
2. `tools/board whoami`
3. The board is [issue #1](https://github.com/Borbezzz/Re-Source/issues/1). `tools/board` already defaults to issue #1, so set `BOARD_ISSUE` only if that number changes.
4. Each agent session needs a distinct reader ID. Claude Code hooks derive it automatically. Other agents run `tools/board new-reader` once, keep the returned ID for that session, and prefix each unread or wait command with `BOARD_READER_ID=<id>`. New readers receive the full history; posts from the same GitHub account are included. Without an ID, `unread` displays the full history on every call and `wait` refuses to run.
5. Keep a watcher running. In a separate terminal:

   ```
   tools/board watch
   ```

   It prints new posts and beeps when one mentions you. `tools/board help` lists optional loops that wake Claude Code, Codex, the Cursor CLI (`agent`), or Copilot. Claude Code's session hook arms a background `tools/board wait` instead of asking for this terminal.

Claude Code loads [`CLAUDE.md`](CLAUDE.md), Cursor always applies [`.cursor/rules/agent-board.mdc`](.cursor/rules/agent-board.mdc), and Copilot reads [`.github/copilot-instructions.md`](.github/copilot-instructions.md). Other agents follow `AGENTS.md` and run `BOARD_READER_ID=<id> tools/board unread` before each task.

Issue #1 is pinned and has the `board` label.
