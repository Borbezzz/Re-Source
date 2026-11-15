# Autonomous sourcing and mailbox delivery

Yixin's 15 November direction replaces approval at every routine step with one
upfront sourcing mandate. The agent should make progress, ask suppliers for
missing information, and interrupt the user when a decision needs their input.

## Working flow

1. Start a sourcing agent for the project. Its mandate covers specification
   checks, research, shortlisting and non-binding quote requests, with no purchase
   authorization.
2. Check prepared requirements or extract an uploaded parts list. Automatically
   continue when the name, explicit quantity and asserted requirements have
   matching source passages; explicitly reviewed custom values are also usable.
   Record whether a human or the agent checked the specification. A default
   quantity of one is not source evidence. Missing or conflicting requirements
   become actionable clarification requests.
3. Run the existing supplier workers. Live investigations retain OpenAI query
   planning, Linkup discovery and Databricks extraction. The globe and cards show
   actual completed results.
4. Choose outreach targets and record why. A candidate's public marketing claim
   remains unverified. Missing price, lead time and certification are questions
   to resolve, rather than reasons to block every quote request.
5. Prepare RFQs containing the specification and unanswered questions. In the
   demo, persist simulated outgoing messages and labelled sample replies. End
   with a recommendation and the evidence still needed before purchase.

The user can inspect the sources, assembly, research, messages and reasoning
without advancing a wizard. Pausing stops further agent actions. Input changes
invalidate the mandate's revision so stale jobs cannot continue outreach.

## What the mailbox currently means

The built-in demo mailbox is a simulation. Message records identify their run,
part and candidate, retain the request/reply relationship, and label synthetic
prices and lead times. A simulated reply is not a verified offer or a delivered
internet email. Repeated worker delivery must not duplicate message records.

Real test-account email is a separate delivery integration. It needs a dedicated
sender account authorized by the team and an explicit set of test recipients.
The intended supplier and the actual test destination must remain distinguishable.
Do not infer an address from a company name, or redirect a fictional demo request
to a discovered real supplier.

Before real delivery is enabled, the provider boundary needs durable outbox
records, provider message IDs, retry/reconciliation behavior, reply correlation,
and credential storage outside source control. Authorization is established
once for routine RFQs within the mandate, rather than requested for every email.
The user has not yet supplied a demo email account or recipient addresses.

## Confidence belongs to an action

| Action | Required basis |
| --- | --- |
| Research a part | Identified part and a usable grounded or user-reviewed specification. |
| Request a quote | A relevant target, current mandate, known authorized destination, and explicit unanswered questions. |
| Compare replies | Reply provenance, comparable terms and visible unknowns. Sample replies stay sample data. |
| Purchase | A separate user decision covering the final offer and commitment. The current agent cannot purchase. |

An arbitrary model confidence percentage does not grant sending authority or
establish engineering compliance. The UI shows the concrete reason for proceeding
or asking for clarification.
