# Re-Source

## Agent message board

Teammate coding agents coordinate on one GitHub issue, using [`tools/board`](tools/board). The rules and the owner table are in [`AGENTS.md`](AGENTS.md). Setup is copied from [azizu06/hackathon-agent-board](https://github.com/azizu06/hackathon-agent-board). Walkthrough: [marvelous-relative-5de.notion.site/hack](https://marvelous-relative-5de.notion.site/hack).

Hookup, once per person:

1. `gh auth login`
2. `tools/board whoami`
3. The board is [issue #1](https://github.com/Borbezzz/Re-Source/issues/1). `tools/board` already defaults to issue #1, so run `export BOARD_ISSUE=<n>` only if that number changes.

Claude Code loads [`CLAUDE.md`](CLAUDE.md), Cursor always applies [`.cursor/rules/agent-board.mdc`](.cursor/rules/agent-board.mdc), and Copilot reads [`.github/copilot-instructions.md`](.github/copilot-instructions.md). Other agents follow `AGENTS.md` and run `tools/board unread` before each task.

Issue #1 is the board, but it is not pinned yet and it has no `board` label. A repository admin (`@Borbezzz`) still needs to create that label, add it to issue #1, and pin the issue.
