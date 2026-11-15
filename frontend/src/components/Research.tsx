import { lazy, Suspense, useState } from "react";
import {
  ArrowRight,
  ShieldCheck,
  Clock3,
  Building2,
  ChevronDown,
} from "lucide-react";
import type {
  CaseView,
  Decision,
  DomainEvent,
  RankedCandidate,
} from "../api/types.ts";
import type { ConnectionState } from "../api/events.ts";
import { formatMoney, selectionBlock } from "../api/guards.ts";
import { Badge, Empty, EvidenceLink, Status, human } from "./Primitives.tsx";

const SupplyMap = lazy(() => import("./SupplyMap.tsx"));
export const supplierName = (r: RankedCandidate) =>
  r.supplier?.legal_entity_name ?? r.candidate.supplier_id;
export function Activity({
  events,
  connection,
  onEvidence,
  eventLabel,
}: {
  events: DomainEvent[];
  connection: ConnectionState;
  onEvidence: (id: string) => void;
  eventLabel?: (event: DomainEvent) => string;
}) {
  const [all, setAll] = useState(false);
  const relevant = events.filter(
    (e) => !["case.state_changed", "visual.updated"].includes(e.type),
  );
  const visible = (all ? relevant : relevant.slice(-12)).toReversed();
  return (
    <section className="activity">
      <div className="section-heading">
        <h3>Investigation activity</h3>
        <Badge tone={connection === "connected" ? "good" : "warning"}>
          {connection}
        </Badge>
      </div>
      <p className="muted small">
        Actual tool events · {events.length} received
      </p>
      {!visible.length ? (
        <Empty title="Ready to investigate">
          Select a component to start supplier research. Events and citations
          will appear here.
        </Empty>
      ) : (
        <ol className="event-list">
          {visible.map((e) => (
            <li key={e.event_id}>
              <span
                className={`event-mark ${e.type.endsWith("failed") ? "failed" : ""}`}
              />
              <div>
                {eventLabel && (
                  <p className="activity-part-label">{eventLabel(e)}</p>
                )}
                <div className="event-meta">
                  <span>{human(e.type.replace(".", " · "))}</span>
                  <time dateTime={e.occurred_at}>
                    {new Date(e.occurred_at).toLocaleTimeString("en-GB", {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </time>
                </div>
                <p>{e.summary}</p>
                {e.evidence_refs?.length > 0 && (
                  <div className="citations">
                    {e.evidence_refs.map((id) => (
                      <EvidenceLink key={id} id={id} onOpen={onEvidence} />
                    ))}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
      {relevant.length > 12 && (
        <button className="text-button" onClick={() => setAll(!all)}>
          {all ? "Show recent activity" : `Show all ${relevant.length} events`}
        </button>
      )}
    </section>
  );
}

export function Research({
  view,
  decision,
  events,
  connection,
  busy,
  onSelect,
  onEvidence,
}: {
  view: CaseView;
  decision: Decision | null;
  events: DomainEvent[];
  connection: ConnectionState;
  busy: boolean;
  onSelect: (c: RankedCandidate) => void;
  onEvidence: (id: string) => void;
}) {
  const [focused, setFocused] = useState<string | null>(null),
    [filter, setFilter] = useState("all");
  const candidates = decision?.candidates ?? [];
  const chosen = candidates.find((c) => c.candidate.candidate_id === focused);
  const visible = candidates.filter(
    (c) => filter === "all" || c.eligibility === filter,
  );
  return (
    <div className="research-workspace">
      <div className="research-top">
        <Suspense
          fallback={
            <div className="supply-map" role="status">
              Loading supplier locations…
            </div>
          }
        >
          <SupplyMap
            candidates={candidates}
            selected={focused}
            onSelect={setFocused}
          />
        </Suspense>
        <Activity
          events={events}
          connection={connection}
          onEvidence={onEvidence}
        />
      </div>
      <section className="comparison">
        <p className="scope-note">
          Checks below evaluate the configured requirement set. Uploaded
          dimensions, material, tolerances and certifications require a separate
          engineering evidence review; their compatibility remains unknown.
        </p>
        <div className="section-heading">
          <div>
            <h2>Compare recovery options</h2>
            <p className="muted">
              {decision
                ? `${decision.label} · ${decision.summary}`
                : "The comparison appears when the investigation publishes a decision."}
            </p>
          </div>
          <label className="filter-label">
            Eligibility
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="all">All options</option>
              <option value="eligible">Eligible</option>
              <option value="pending">Pending evidence</option>
              <option value="ineligible">Ineligible</option>
            </select>
          </label>
        </div>
        {decision && (
          <div className="inline">
            <Badge>{human(decision.status)}</Badge>
            <span className="small muted">
              Input revision {decision.input_revision} · Costs are estimates
              from the published plan.
            </span>
          </div>
        )}
        {!visible.length ? (
          <Empty
            title={
              candidates.length
                ? "No options match this filter"
                : "Research is in progress"
            }
          >
            Review the activity log for completed checks, missing evidence or
            tool failures.
          </Empty>
        ) : (
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Recovery comparison, scroll horizontally for costs and actions"
          >
            <p className="comparison-scroll-hint">
              Swipe or scroll across for landed cost, recovery time and review
              actions →
            </p>
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>Supplier / site</th>
                  <th>Compatibility</th>
                  <th>Landed cost</th>
                  <th>Recovery</th>
                  <th>Score</th>
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visible.map((c) => (
                  <tr
                    key={c.candidate.candidate_id}
                    className={
                      focused === c.candidate.candidate_id ? "selected-row" : ""
                    }
                  >
                    <td>
                      <button
                        className="supplier-title"
                        onClick={() => setFocused(c.candidate.candidate_id)}
                      >
                        {supplierName(c)}
                      </button>
                      <span>{c.site?.name ?? "Site not established"}</span>
                      <Badge>{c.candidate.route}</Badge>
                    </td>
                    <td>
                      <Status value={c.eligibility} />
                    </td>
                    <td className="numeric">
                      {c.plan ? formatMoney(c.plan.landed_cost) : "Unknown"}
                    </td>
                    <td>{c.plan ? `Day ${c.plan.finish_day}` : "Unknown"}</td>
                    <td className="numeric">
                      {c.score?.score != null
                        ? Number(c.score.score).toFixed(1)
                        : "—"}
                    </td>
                    <td>
                      <button
                        className="secondary compact"
                        onClick={() => setFocused(c.candidate.candidate_id)}
                      >
                        Review <ArrowRight size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {chosen && decision && (
          <CandidateDetail
            key={chosen.candidate.candidate_id}
            candidate={chosen}
            decision={decision}
            view={view}
            busy={busy}
            onSelect={() => onSelect(chosen)}
            onEvidence={onEvidence}
          />
        )}
      </section>
    </div>
  );
}

function CandidateDetail({
  candidate: c,
  decision,
  view,
  busy,
  onSelect,
  onEvidence,
}: {
  candidate: RankedCandidate;
  decision: Decision;
  view: CaseView;
  busy: boolean;
  onSelect: () => void;
  onEvidence: (id: string) => void;
}) {
  const block = selectionBlock(view, decision, c),
    checks = decision.checks.filter(
      (check) => check.candidate_id === c.candidate.candidate_id,
    );
  return (
    <section className="candidate-detail" aria-label="Supplier evidence review">
      <div className="section-heading">
        <div>
          <h3>{supplierName(c)}</h3>
          <p>{c.summary}</p>
        </div>
        <div className="selection-action">
          <button
            className="primary"
            disabled={busy || !!block}
            onClick={onSelect}
          >
            Select & prepare pack <ArrowRight size={16} />
          </button>
          {block && <p className="small warning">{block}</p>}
        </div>
      </div>
      <div className="detail-columns">
        <div>
          <h4>
            <ShieldCheck size={17} /> Requirements & compatibility
          </h4>
          <div className="checks">
            {checks.map((check) => (
              <details key={check.check_id} open={check.result !== "pass"}>
                <summary>
                  <Status value={check.result} />
                  <span>{check.requirement_title}</span>
                  <ChevronDown size={14} />
                </summary>
                <p>{check.plain_language ?? check.explanation}</p>
                <div className="citations">
                  {check.evidence_refs.map((id) => (
                    <EvidenceLink key={id} id={id} onOpen={onEvidence} />
                  ))}
                </div>
                {check.reused_from_decision_id && (
                  <p className="small muted">
                    Reused from a prior decision; input fingerprint unchanged.
                  </p>
                )}
              </details>
            ))}
          </div>
        </div>
        <div>
          <h4>
            <Building2 size={17} /> Company & site
          </h4>
          <dl className="facts">
            <div>
              <dt>Legal entity</dt>
              <dd>{supplierName(c)}</dd>
            </div>
            <div>
              <dt>Address</dt>
              <dd>{c.site?.address ?? "Unknown"}</dd>
            </div>
            <div>
              <dt>Capabilities</dt>
              <dd>{c.site?.capabilities.map(human).join(", ") || "Unknown"}</dd>
            </div>
            <div>
              <dt>Registry</dt>
              <dd>
                {c.supplier?.registry
                  ? Object.entries(c.supplier.registry).map(([k, v]) => (
                      <p key={k}>
                        {human(k)}: {human(v)}
                      </p>
                    ))
                  : "No company check supplied"}
              </dd>
            </div>
          </dl>
          {c.plan && (
            <>
              <h4>
                <Clock3 size={17} /> Cost & switching plan
              </h4>
              <div className="cost-lines">
                {c.plan.cost_breakdown.map((line, i) => (
                  <div key={i}>
                    <span>
                      {line.label}
                      <small>{line.source}</small>
                    </span>
                    <strong>{formatMoney(line.converted)}</strong>
                  </div>
                ))}
                <div className="total">
                  <span>Total landed estimate</span>
                  <strong>{formatMoney(c.plan.landed_cost)}</strong>
                </div>
              </div>
              <ol className="plan-steps">
                {c.plan.steps.map((s) => (
                  <li key={s.step_id}>
                    {s.name}{" "}
                    <span className="muted">
                      {s.start_day}–{s.finish_day} days
                    </span>
                  </li>
                ))}
              </ol>
              <p className="small muted">{c.plan.assumptions.join(" · ")}</p>
            </>
          )}
          {c.reliability.length > 0 && (
            <>
              <h4>Reliability evidence</h4>
              {c.reliability.map((m) => (
                <p className="small" key={m.metric_id}>
                  {m.label}:{" "}
                  <strong>
                    {m.value} {m.unit}
                  </strong>{" "}
                  · {human(m.data_origin)}
                  {m.fixture_note ? ` · ${m.fixture_note}` : ""}
                  {m.source_evidence_id && (
                    <EvidenceLink
                      id={m.source_evidence_id}
                      onOpen={onEvidence}
                    />
                  )}
                </p>
              ))}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
