# Re::Source — Devpost submission copy

Prepared from the implementation and recorded verification on 15 November 2026. The sections marked “paste” are submission copy. The final preparation notes are for the team.

## Project overview — paste

**Project name**

Re::Source

**Elevator pitch**

From blueprint to supplier shortlist. AI agents research parts with Linkup, structure evidence with Databricks, and prepare quote requests you can trace back to the source.

## Project details — paste

### Inspiration

An engineer can know exactly which component they need and still spend hours working out where to source it. The specification is in a drawing, supplier capabilities are scattered across websites, and the next step often becomes a spreadsheet and a chain of emails.

We wanted to connect those pieces. Our starting point was aerospace recovery, where a part's identity, evidence and delivery route all matter. We then broadened the idea to mechanical assemblies: let an engineer point to a part, give an agent the sourcing task, and inspect the evidence behind its progress.

That became Re::Source: a workspace that takes a sourcing investigation from technical requirements to supplier research and a concrete request for quotation.

### What it does

Re::Source accepts a product specification or prepared design package, identifies the parts and requirements, and makes the assembly explorable in 3D. The user selects the components they need and starts the sourcing agent.

The agent checks the specification, researches suppliers, compares what the sources establish, and prepares RFQs containing the requirements and unanswered questions. Different parts can be investigated concurrently, with visible progress, source links and supplier findings in the same workspace.

The workflow is persistent. Users can leave and return to an investigation, inspect its source documents, correct a requirement or pause the agent. A specification change invalidates dependent work so an earlier search cannot silently become the answer to a different request.

There are two clearly labelled experiences:

- **Prepared demo:** explore an assembly, research sample offers, generate simulated quote requests, receive correlated sample replies and reach a recommendation.
- **Live research:** upload a specification, discover public supplier sources through Linkup, structure their claims with Databricks and draft evidence-aware RFQs. The agent asks for a verified contact and connected mailbox before real delivery.

The current project does not place orders or send real supplier emails. Public supplier claims remain unverified, and prepared 3D models provide visual context rather than manufacturing certification.

### How we built it

The frontend uses React, TypeScript and Vite, with Three.js, React Three Fiber and Drei for interactive assemblies. D3 Geo and TopoJSON power the supplier map. A Python FastAPI backend exposes typed Pydantic contracts, while Vercel hosts the application and executes durable background jobs through Vercel Queues.

The generic sourcing agent advances through persisted service continuations. The retained aerospace recovery engine uses LangGraph for BUY/MAKE sourcing, evidence checks, scheduling and reassessment. OpenAI structured outputs help identify parts and plan searches; application code validates the resulting facts and controls state changes.

**Databricks is central to document understanding, evidence processing and persistence:**

- **`ai_parse_document`:** reads uploaded document bytes from a Unity Catalog volume. We exercised this on a real NASA turbine blade-section PDF, then proposed a part and three source-linked requirements for review.
- **`ai_extract`:** turns Linkup titles and snippets into structured supplier identity, country, material and certification claims. We batch extraction by field set and check output against literal source text.
- **Lakebase Postgres:** persists projects, research, RFQs, agent progress and queued work across serverless invocations. The recovery graph also uses Postgres checkpoints.
- **Unity Catalog Volumes:** preserve original files using content-addressed storage, allowing the application to recover source bytes after an instance restarts.
- **Delta and SQL:** support the recovery scenario's versioned evidence, relationships and decision projections across 16 application tables.
- **MLflow 3:** provides implemented tracing hooks and a recorded synthetic domain evaluation; current public tracing is disabled.

**Linkup connects the agent to actual supplier sources:**

- Calls the Search API with `depth: "standard"` and `outputType: "searchResults"`.
- Grounds queries in the confirmed part name, part number and requirements, with up to two model-planned searches per part.
- Retains titles, original URLs and snippets, with deduplication and bounded results.
- Feeds sources into Databricks extraction, requirement-level evidence notes, supplier candidates and RFQ questions.
- Records the providers actually used, so prepared data or failed searches cannot masquerade as successful live calls.

The combination matters: a source discovered by Linkup becomes a structured claim, a visible evidence gap and a next action, while Databricks preserves the task and its inputs.

### Challenges we ran into

**Keeping extraction faithful to engineering documents.** A drawing number can look like a part number; an unstated quantity can become a plausible default. We added source checks, explicit identity rules and review states so those guesses do not quietly enter the specification.

**Making agents durable in a serverless application.** Investigations must survive reloads, worker restarts and queue redelivery. We persisted job intent and progress, added revision checks and duplicate protection, and separated HTTP requests from background work.

**Showing evidence honestly.** A supplier page may mention a material without proving a specific part is available or certified. We retained citations and unknowns, making missing evidence part of the RFQ rather than inventing a confident answer.

**Keeping the interface responsive.** Assemblies, maps and workflow animations compete for browser resources. We profiled startup and transitions, reduced repeated geometry preparation and camera work, and checked the journey on desktop and mobile.

### Accomplishments that we're proud of

- Connecting the task from specification and part selection to supplier investigation, RFQ and persistent recommendation workflow.
- Exercising real Linkup and Databricks calls together in deployed research, with six cited supplier leads in the recorded live examples.
- Parsing an archival engineering PDF through Databricks while preserving the distinction between a drawing identifier and manufacturer part number.
- Completing a three-part prepared demo through simulated requests and replies from one agent start action.
- Verifying queued progress without browser polling: a staged run was complete when the verifier returned after 60 seconds without reading its state.
- Making provider provenance inspectable, including skipped demo calls, extraction fallbacks and the actual persistence backend.
- Passing 265 backend tests and 20 frontend tests at the recorded autonomous-sourcing milestone, with later verification covering provider labels and rendering performance.

### What we learned

The difficult part of an agent is often deciding what it is allowed to conclude. Finding a supplier is useful; showing exactly which requirements remain unsupported makes that result actionable.

Autonomy also depends on durable state and clear boundaries. An agent can advance routine research without making the user click through every stage, while still stopping for a missing specification, an unknown recipient or a purchasing decision.

Finally, integrating tools deeply matters more than displaying their names. Linkup and Databricks earn their place because their outputs drive subsequent work and remain inspectable by the engineer.

### What's next for Re::Source

- Connect an authorized mailbox for test-recipient RFQs, delivery tracking and reply correlation.
- Bring real quotations, stock information and supporting documents into comparisons.
- Evaluate extraction across more drawings and assemblies.
- Extend monitoring and reassessment from the seeded recovery scenario to live sourcing evidence.
- Connect a geometry-generation provider where it can return useful models with clear provenance and validation.
- Evaluate newer Linkup and Databricks APIs against measured sourcing quality, latency and cost.

## Built with — paste as individual tags

Databricks, Lakebase, Unity Catalog, Delta Lake, Databricks AI Functions, Linkup, OpenAI, Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, LangGraph, Vercel, Vercel Queues, React, TypeScript, Vite, Three.js, React Three Fiber, Blender, D3.js, OR-Tools, MLflow, Playwright, pytest.

MLflow and OR-Tools apply to the documented diagnostics/recovery subsystem. Figma can be included as a design tool if the team uses its linked reference in the submission.

## Track and bounty answers — paste into matching fields

**Track:** Autonomous Agents

**Bounties:** Databricks and Linkup

### Databricks — detailed answer

Re::Source uses Databricks as the document, evidence and state layer of an engineering sourcing agent:

- **AI Functions / `ai_parse_document`:** parses uploaded files from a Unity Catalog volume into content used for parts extraction. A connected run processed a NASA turbine blade-section PDF and produced a named part with three requirements for review.
- **AI Functions / `ai_extract`:** extracts supplier name, country, materials and certification claims from Linkup snippets. The SQL adapter batches up to 20 rows by field-label set; application code checks claims against literal source text.
- **Lakebase:** provides durable Postgres state for projects, research, jobs, RFQ packages and simulated mailbox records. The retained LangGraph workflow also stores checkpoints in Postgres.
- **Unity Catalog Volumes:** store original files by SHA-256 hash, preserving sources across serverless restarts and enabling inspection.
- **Delta and SQL warehouse:** retain versioned recovery evidence, relationships and revision-labelled decision/action projections in 16 `rs_*` tables using idempotent ingestion.
- **MLflow 3:** implemented tracing and recorded domain evaluation support inspection of recovery logic. Current public tracing is disabled rather than claimed for every run.

The features to highlight most are AI document parsing and Lakebase-backed agent persistence, combined with SQL-native evidence extraction. Databricks participates before research, during source analysis and throughout the task's lifetime. Real parsing, extraction and persistence were verified in connected deployments.

### Linkup — detailed answer

Re::Source uses Linkup as the live supplier-discovery tool inside a multi-step sourcing agent:

- Calls `/v1/search` with `depth: "standard"` and `outputType: "searchResults"`.
- Grounds queries in the reviewed component name, part number and technical requirements; OpenAI can plan up to two concise queries per part.
- Investigates multiple parts through concurrent queued workers, preserving separate sources and progress.
- Retains original URLs, titles, snippets and retrieval timestamps, with URL deduplication and bounded leads.
- Sends snippets to Databricks `ai_extract` and builds requirement-level evidence notes around the original sources.
- Carries missing evidence into RFQs rather than inventing prices, stock or certification.
- Records actual provider usage and a recoverable failed state if live discovery cannot finish.

Recorded live runs returned six cited leads and advanced to RFQ drafting. Linkup directly determines which suppliers the agent considers and which questions it asks next. This build uses standard search; it does not claim Deep, Fetch, Research or structured-output endpoints.

## Links and assets

| Devpost field | Value |
| --- | --- |
| Application | https://resource-borbez2s-projects.vercel.app/ |
| Public repository | https://github.com/Borbezzz/Re-Source |
| Existing draft preview | https://devpost.com/software/1547385 |
| Design reference, if entering Figma | https://www.figma.com/design/o4G1HFAyQybcPuBG1nV2lL |
| Demo video | **Team must supply the actual uploaded video URL.** |
| Thumbnail | **Choose a project screenshot: JPG, PNG or GIF, at most 5 MB, preferably 3:2.** |

## Team preparation notes — do not paste into the story

### Evidence to have open for judging

- [Live supplier result](../verification/product-workflow-20261115/deployed-product.json): six source URLs and `openai`, `linkup`, `databricks_ai_extract` recorded.
- [Real PDF parsing](../verification/product-workflow-20261115/nasa-blueprint.json): actual parsing, one proposed part, three requirements, no invented part number or model.
- [Live autonomous result](../verification/agent-outreach-20261115/staged-live.json): quantity 20, six leads, Lakebase, durable queue, `contact_required`, zero messages sent.
- [Autonomous verification](../verification/agent-outreach-20261115/REPORT.md): one-start demo and unattended completion observations.
- [Production check and feature audit](VERIFICATION.md): current runtime observations and precise newer-feature boundaries.
- [README sponsor detail](../../README.md): feature-level explanation and code links.

### Suggested two-minute video structure

| Time | Show | Voice-over focus |
| --- | --- | --- |
| 0:00–0:15 | Specification beside the workspace | “Engineering teams have the specification, but sourcing means reading documents, opening supplier tabs and chasing missing evidence. Re::Source connects that work.” |
| 0:15–0:35 | Upload, extracted part and source quote | Identify the part and show where its requirements came from. Label a separate NASA parsing example as a separate run if used. |
| 0:35–1:05 | Live investigation and cited results | Show actual Linkup/Databricks provider usage, then inspect a source and evidence gap. |
| 1:05–1:30 | RFQ and actual stopping/completion state | Show how unanswered requirements become questions. Label prepared geometry, sample replies and simulated actions wherever shown. |
| 1:30–1:50 | Architecture and provider evidence | “Linkup discovers sources. Databricks parses documents, extracts claims and preserves state in Lakebase. Queued workers advance the task.” |
| 1:50–2:00 | Finished investigation | Name the closest comparator actually evaluated, explain the workflow difference, and give a measured success count if available. |

Use one real sourcing run as the main sequence. Label any speed-up and state actual duration. Do not present separate examples as one uninterrupted run. Test counts do not establish a production success percentage; the 60-second unattended observation is not a general runtime benchmark.

### Submission details still to supply

- The uploaded demo video URL, at most two minutes.
- Each teammate added to Devpost, with full name, Luma signup email and university email in the team question.
- Final thumbnail/screenshot.
- Any measured repeated-run success count and actual duration used in the video.
- A verified closest-product comparison for the video; this draft does not invent competitor research.

The [published submission requirements](https://imperial-ai-hackathon.devpost.com/) specify a public repository, video, one track and up to two track bounties. The [rules](https://imperial-ai-hackathon.devpost.com/rules) set the deadline at **12:00 GMT on Sunday 15 November 2026** and judge bounties on how central the partner tool is to the product. Complete the actual Devpost fields and final submission before the deadline; saving this document does not submit the project.
