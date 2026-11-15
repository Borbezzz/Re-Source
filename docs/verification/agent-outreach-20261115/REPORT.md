# Autonomous sourcing verification

15 November 2026. Scope: one upfront sourcing mandate, automatic grounded
specification checks, supplier investigation, RFQ drafting and a labelled demo
mailbox. Actual email sending and purchasing are not connected.

## Local evidence

- Full Python suite: **265 passed, 4 skipped**.
- Frontend production build/TypeScript checks pass; **20 frontend tests pass**.
- Independent grounding/lifecycle audit: 29 tests, included in the full suite.
- Fresh HTTP session: one agent start completed three part investigations,
  created three simulated quote requests and three correlated sample replies,
  and reached `recommendation_ready`. The RFQ package stayed a draft, no purchase
  was authorized, and another visitor received 404 for the project.
- A custom JSON BOM with an explicit quantity of 20 was extracted and checked
  automatically. With local discovery deliberately disabled, it stopped at
  `research_failed`, retaining source provenance and sending no messages.
- Browser: the same prepared-demo flow completed from one start action without
  a confirm/select/approve sequence. Manual source inspection followed by Start
  correctly switched back to agent management. Unsaved source edits disabled
  launch and restoring the original value enabled it again.
- Desktop and 390×844 mobile checks verified launch controls, sent/inbox
  disclosures, readable replies, and no horizontal overflow. No browser errors
  were recorded in the completed local flow.
- Audit coverage includes missing quantities, identity and conflicting source
  facts; changed specifications; visitor isolation; pause/resume; duplicate and
  concurrent delivery; partial research retry; and recovery of a committed
  continuation when queue publication initially fails.

The demo mailbox is durable application data, not a connected email account.
Live mode drafts RFQs and requests verified contact/mailbox details. All supplier
eligibility remains unverified; sample replies cannot establish compliance.

## Connected staging

Verified the existing Production environment without assigning public domains:
`https://resource-ri1jnhqhj-borbez2s-projects.vercel.app` (backend commit `a80a96c`).
Vercel inspection reported the API and queue subscriber ready.

- Demo: three investigations, three simulated requests and three sample replies
  persisted in Lakebase Postgres through the durable queue. The project summary
  reported recommendation-ready and another anonymous visitor received 404.
- Background execution: after a fresh start, the verifier made no reads for 60
  seconds. Its first read found the entire demo complete. This checks that a
  browser polling loop is not needed to advance the task. An earlier 30-second
  observation found it still running, then it completed normally.
- Custom BOM: an explicit M8 hex-nut specification with quantity 20 was extracted
  and checked automatically, then produced six public leads using **OpenAI,
  Linkup and Databricks AI Extract**. It drafted the RFQ and stopped with
  `contact_required`; no messages were sent and no purchasing was authorized.
- The deployed browser loaded the prepared gallery through its real API.

Sanitized observations are in `staged-demo.json`, `staged-unattended.json` and
`staged-live.json`. A final UI-only correction keeps a prior manual simulation
receipt from making a newly started agent look complete; its build also passes.
