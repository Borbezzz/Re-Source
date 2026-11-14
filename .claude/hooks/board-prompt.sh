#!/usr/bin/env bash
# UserPromptSubmit: surface board posts that arrived since the last check. Silent when none. Never fails.
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
reader="$(tr -d '\n' | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([[:alnum:]_-]*\)".*/claude-\1/p')"
out="$(BOARD_READER_ID="$reader" tools/board unread 2>/dev/null)" || exit 0
[ -n "$out" ] && printf 'New board posts (issue #%s):\n%s\n' "${BOARD_ISSUE:-1}" "$out"
exit 0
