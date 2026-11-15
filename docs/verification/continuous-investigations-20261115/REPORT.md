# Continuous investigation navigation verification

15 November 2026. Implementation checkpoints: `c5dc629` (private summary API)
and `fb3cd22` (shared navigation and continuous project workspace).

## Behavior

The main navigation has Home, Investigations and New investigation. New work
starts from a design package or a prepared demo. A project retains one URL through
source review, assembly selection, research/choice, RFQ review and simulation.
Completed sections become expandable summaries. Research and supplier comparison
are presented together. Saved projects resume from persisted progress.

The dashboard reads only visitor-owned summary columns, ordered by most recent
update, with a maximum of 100 projects. It never returns source text, requirements,
models or another visitor's records. Queue dispatch recovery remains available
when visitors return to the dashboard. Research uses the existing durable queue.

## Automated checks

- Backend: **230 passed, 4 skipped**.
- Frontend: **18 passed**; production build and TypeScript checks passed.
- New API checks cover ownership, private caching, bounded sorting, mixed job
  statuses, package progress and service restart/resume.
- Independent code review found edit-loss, history metadata and overlapping-poll
  hazards. Fixes were applied before the UI checkpoint.
- Impeccable detection found advisory token differences only; new dashboard type
  sizes were aligned with the documented scale. Existing error colors remain.

## Browser checks

Actual browser, local API plus frontend and a deployed production build:

- Exactly three shared navigation destinations on entry, projects and dashboard.
- Prepared lamp → reviewed source parts → 3D selection → three research jobs →
  supplier choice → RFQ → package approval → simulated receipt, all at one URL.
- Completed sections reopen without losing local source edits.
- Saved list resumes a completed project, and reload preserves its receipt.
- Custom project creation appears as a resumable draft.
- Canceling Back while a part name is edited preserves both the draft and browser
  history; restoring the original value allows Back to reach Investigations.
- Keyboard Skip to content moves focus to the workspace without changing route.
- 390 × 844 navigation, dashboard, custom entry and completed flow have no
  horizontal page overflow; header controls remain readable and usable.
- Home retains the crisp wordmark, ripple background and toy-car controls without
  the removed reset button.

## Connected API

The staged build uses the existing Production environment; Preview has no backend
credentials. The connected test exercises the PostgreSQL summary query and durable
queue, not only the SQLite test implementation. See `deployed-summary.json` for
sanitized observations. No credentials or visitor cookies are included.

This change does not add automatic 3D generation or external purchasing. Prepared
models remain labelled, public leads remain unverified, and the final receipt is
simulation only.
