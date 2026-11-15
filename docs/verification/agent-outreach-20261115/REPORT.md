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
