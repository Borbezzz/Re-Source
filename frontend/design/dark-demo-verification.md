# Dark Re::Source and real-screen demo verification

Date: 14 November 2026. Integrated from dark theme 5f9f61f, guided demo 097d573 and premade engine a6ee902. The coordinating branch preserves the original engine commit ancestry for PR #26.

## Local checks

- Production build passes. All 14 frontend invariants pass after engine integration.
- Before the engine merge, all 11 app browser scenarios passed: batch/retry, intake/reload, full prepared demo, slow-bootstrap/extraction retry, prepared product/failure and recovery/disruption.
- After engine integration, all 6 targeted browser scenarios passed: intake2, engine intro, persisted-engine/three-part/resize/uploaded-mesh coverage, prepared demo2.
- Demo tests use actual local APIs and a private operational store with model/Databricks/Linkup/Companies House/prewarm disabled. They exercise deterministic fallbacks and all normal confirmation/approval gates, not live provider success.
- First visual review returned fix for stale header branding and a mobile active tab shrinking under its label. Both were fixed in the integrated app and recaptured at1440x900 and390x844. The independent scoring pass returned ship for those fixes, with no visible introduced regression. No QUALITY BAR card was supplied; no whole-surface ceiling certification is claimed.
- Native controls, pointer-exit clearing, reduced motion, no-WebGL fallback and background suspension were verified by the dark worker. The initial optical pointer lens was subsequently removed at the user's request.
- A subsequent full-workflow review caught legacy light research/comparison panels. Their dark backgrounds and field states are corrected. The fresh working-screen reviewer returned `disposition: ship` for comparison, evidence, approval and desktop/mobile receipt captures; motion, keyboard behavior and other mobile stages were outside that capture-only scope.
- After the contrast correction, the production build, 14 frontend invariants and the complete prepared-demo browser journey passed again.
- Connected staging successfully extracted 12 source-linked fields with Databricks `ai_extract`. The first browser assertion expired across two uploads, job acceptance and extraction; the extraction itself completed in about 86 seconds. The test now waits separately for accepted extraction before checking its terminal review screen, and passes locally again.
- Connected timing exposed an existing public run-history N+1 lookup. Filtering ownership in a single query preserves visitor isolation, ordering and internal no-visitor behavior while reducing the measured 30-run case from 31 SELECTs to one. Full backend suite after the fix: 181 passed, 4 skipped, including three new lookup regressions. No migration or API change is required.

## Source and provider facts

Exact PatternWaves source/license are preserved under src/theme/vendor and require ogl. Glass controls/lens are local native-control/SVG implementations informed by the researched liquid-glass-react repository, not that wrapper installed as a control library.

Production readiness read during this task reports model ok=true/model=gpt-5.4-mini, Lakebase Postgres and postgres checkpointing. Web-instance usage counters are process-local and were0 on this fresh read; no global usage conclusion is drawn from them.

OpenAI Responses is called for configured structured extraction, task/decision explanations and risk-signal normalization. Databricks managed extraction/parsing can precede it; its underlying model is not pinned by this code. Linkup can run when configured even in seeded mode. Companies House currently has readiness-refresh calls only. Deterministic code decides eligibility, ranking, scheduling, selection and approval gates.

## Connected baseline and requested visual refinement

The complete production-connected prepared-demo browser test passed in 2.5 minutes on a5a2ee5, including manual correction/confirmation, two-part investigation, evidence, approval invalidation/reapproval, simulated receipt, reload persistence and mobile/reduced-motion overflow. Runtime error-log scan returned no records. A fresh engine GET after the lookup fix took 3.39 seconds; this is one observation, not a latency guarantee.

The user's subsequent refinement removes the oval lens and dotted/blurred title hover. Actual title-canvas pixels remained identical at rest, hover, movement and exit. A separate six-cube white rig with nine connections uses neutral sourcing labels; responsive placement keeps its groups clear of the copy/actions. Touch, exit, hidden/offscreen, reduced-motion and no-WebGL checks pass.

Actual wave input is strengthened (cursor strength 1, field coupling 0.5). Four-edge black fades, a black header and a gradual assembly transition preserve the background in connecting/model-loading states. Corners use controls/fields 8px, panels 12px and chips 4px, with concentric nested groups. Redundant dividers are removed while field, selection and focus boundaries remain. Final combined visual review and rollout results are recorded on PR #27.

The independent refinement review returned `disposition: ship` after fixing the persistent sticky-header fade, clipped mobile focus ring and mobile graph-label collision. This is scoped to supplied desktop/mobile/loading/ready/exit/reduced-motion captures, not a QUALITY BAR ceiling. The final local production build, 14 frontend invariants and complete prepared-demo browser journey passed again. The home-only header tail is absent from the Sources screen; actual mobile keyboard focus is fully visible.

## Remaining boundaries

Generic-product research remains gated; engine is the supported complete demo. Toy-car geometry is a separate selection playground. Uploaded engineering fields still require manual evidence review, and automatic blueprint-to-segmented-mesh generation needs a real provider. Offers and simulated receipts keep their labels. Public connected rollout evidence will be posted on the integration PR after staged/canonical verification.
