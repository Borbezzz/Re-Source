# Supplier enquiry email — 15 November 2026

The fulfilment preview now presents To, From and Subject fields and a readable email body, without the decorative gradient strip. The server drafts the greeting, reviewed part requirements, requested quantity/date/destination, commercial questions, evidence requests and buyer sign-off. Fictional supplier provenance and simulated delivery remain explicit.

Studio submits a bounded enquiry context when building the package. The stored package, displayed email and approved package contain the same request. A changed quantity, date, selected occurrence or buyer creates a fresh draft/package ID; an old approval cannot approve or simulate the replacement. A scoped enquiry excludes earlier part selections. The existing bodyless package endpoint remains supported.

Validation:
- Frontend production build and all 25 frontend tests passed.
- Backend: 268 passed, four live-provider tests skipped.
- Real local browser-to-API journey passed: upload v1.2 ZIP, select Fan blade 03, request three units for 5 January 2027, compare/select a supplier, inspect desktop/mobile email, and approve the exact stored draft.
- Checked absence of the document gradient pseudo-element and availability badges; no horizontal mobile overflow or browser errors.
- Screenshots saved outside the repository in `artifacts/resource-email-20261115/`.

The email is a demo RFQ template. No verified supplier recipient or real sender email is configured, and no external message was sent.
