#!/usr/bin/env bash
# SessionStart: show unread board posts and tell the agent to keep a background wait running.
# Never fails the session: always exits 0.
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
# Claude supplies the same session_id to each hook in this session.
reader="$(tr -d '\n' | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([[:alnum:]_-]*\)".*/claude-\1/p')"
out="$(BOARD_READER_ID="$reader" tools/board unread 2>&1)" || out="(board unreachable: $(printf '%s' "$out" | head -n 1)). Run tools/board unread later."
echo "Team board (GitHub issue #${BOARD_ISSUE:-1}). Rules are in AGENTS.md."
if [ -n "$out" ]; then
  echo "Unread posts:"
  echo "$out"
else
  echo "No unread posts."
fi
if [ -n "$reader" ]; then
  echo "Board reader ID for this Claude session: $reader. Use BOARD_READER_ID=$reader on every tools/board unread or wait command."
fi
if [ -z "$reader" ]; then
  echo "Claude session ID unavailable: unread shows the full history. Create a session ID with tools/board new-reader and use BOARD_READER_ID on every board command before starting wait."
elif [ "${BOARD_WAIT:-}" = "off" ]; then
  echo "Board loop: your supervisor watches the board and relays anything that affects you. Do NOT arm a background tools/board wait. Still run tools/board unread before each commit and after merges."
else
  printf '%s\n' "Start ONE background Bash command with run_in_background: BOARD_READER_ID=$reader tools/board wait. When it completes, handle its output and re-arm it. Posts from your own account also appear; do not reply to your own post merely to acknowledge it."
fi
exit 0
