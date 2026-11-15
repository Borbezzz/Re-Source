import { useState } from "react";
import { ArrowRight, Check, Mail, Pause, Play } from "lucide-react";
import { productApi } from "./client.ts";
import type {
  ProductAgentRun,
  ProductMailboxMessage,
  ProductProject,
} from "./types.ts";
import type { ProjectAction } from "./ProductFlow.tsx";
const statusLabels: Record<ProductAgentRun["status"], string> = {
  queued: "Starting",
  running: "Working",
  paused: "Paused",
  needs_attention: "Needs your input",
  recommendation_ready: "Recommendation ready",
  failed: "Run needs attention",
};
const stageLabels: Record<ProductAgentRun["stage"], string> = {
  requirements: "Checking document-backed requirements",
  research: "Researching suppliers",
  shortlist: "Choosing supplier leads",
  rfq: "Preparing quote requests",
  outreach: "Requesting and collecting quotes",
  complete: "Recommendation ready",
};
export function AgentLaunch({
  project,
  busy,
  dirty,
  onAction,
  onManual,
  onInspect,
}: {
  project: ProductProject;
  busy: string;
  dirty: boolean;
  onAction: ProjectAction;
  onManual: () => void;
  onInspect: () => void;
}) {
  const [mode, setMode] = useState<"demo" | "live">(
    project.demo_id ? "demo" : "live",
  );
  return (
    <section
      id="investigation-agent"
      tabIndex={-1}
      className="pf-agent-launch"
      aria-labelledby="agent-launch-title"
    >
      <div>
        <h2 id="agent-launch-title">
          Let the sourcing agent handle the next steps.
        </h2>
        <p>
          It checks source-backed parts, researches suppliers, chooses leads and
          prepares quote requests. It pauses when information is missing and
          stops before any purchase.
        </p>
        <label>
          Research mode
          <select
            value={mode}
            disabled={!!busy}
            onChange={(event) => setMode(event.target.value as "demo" | "live")}
          >
            {project.demo_id ? (
              <option value="demo">Demo suppliers & sample replies</option>
            ) : null}
            <option value="live">
              Research real suppliers · draft requests
            </option>
          </select>
        </label>
        <p className="pf-agent-scope">
          {mode === "demo"
            ? "One start authorizes routine RFQs and sample replies in the simulated demo mailbox. No real emails are sent."
            : "The agent can research public sources and draft RFQs. It pauses before sending because no verified external recipient is connected."}
        </p>
        {!project.parts.length &&
        !project.documents.some((document) => document.kind !== "model") ? (
          <p className="pf-footnote">
            Add your source documents below, then start the agent.
          </p>
        ) : null}
        {dirty ? (
          <p className="pf-inline-error">
            Save your source edits before starting the agent.
          </p>
        ) : null}
      </div>
      <div className="pf-agent-launch-actions">
        <button
          className="primary"
          disabled={
            !!busy ||
            dirty ||
            (!project.parts.length &&
              !project.documents.some((document) => document.kind !== "model"))
          }
          onClick={() =>
            void onAction(
              "Starting sourcing agent…",
              () =>
                productApi.startAgent(
                  project.project_id,
                  project.version,
                  mode,
                ),
              "agent",
            )
          }
        >
          <Play size={15} /> Start sourcing agent <ArrowRight size={16} />
        </button>
        <button className="text-button" disabled={!!busy} onClick={onManual}>
          Review and source manually
        </button>
        {project.model.asset_url ? (
          <button className="text-button" onClick={onInspect}>
            Inspect the 3D model
          </button>
        ) : null}
      </div>
    </section>
  );
}
export function AgentRun({
  project,
  busy,
  dirty,
  onAction,
  onInspect,
  onManual,
}: {
  project: ProductProject;
  busy: string;
  dirty: boolean;
  onAction: ProjectAction;
  onInspect: () => void;
  onManual: () => void;
}) {
  const agent = project.agent!;
  const downloadRfqs = () => {
    const content = project.package?.items
      .map((item) => item.rfq_text)
      .join("\n\n---\n\n");
    if (!content) return;
    const url = URL.createObjectURL(
      new Blob([content], { type: "text/plain" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "sourcing-agent-rfqs.txt";
    link.click();
    URL.revokeObjectURL(url);
  };
  const running = agent.status === "queued" || agent.status === "running";
  const current = agent.input_version === project.input_version;
  const messages = (project.mailbox ?? []).filter(
    (message) => message.run_id === agent.run_id,
  );
  const events = project.events.filter(
    (event) => event.created_at >= agent.created_at,
  );
  const sent = messages.filter((message) => message.direction === "outbound");
  const replies = messages.filter((message) => message.direction === "inbound");
  return (
    <section
      id="investigation-agent"
      className="pf-agent-run"
      tabIndex={-1}
      aria-labelledby="agent-run-title"
    >
      <div className="pf-section-heading">
        <div>
          <h2 id="agent-run-title">Sourcing agent</h2>
          <p className="pf-agent-status" aria-live="polite">
            {statusLabels[agent.status]}
            {agent.stage !== "complete" ? ` · ${stageLabels[agent.stage]}` : ""}
          </p>
          <p>{agent.summary}</p>
        </div>
        <div className="pf-agent-controls">
          {running ? (
            <button
              className="secondary"
              disabled={!!busy}
              onClick={() =>
                void onAction("Pausing the sourcing agent…", () =>
                  productApi.pauseAgent(
                    project.project_id,
                    agent.run_id,
                    project.version,
                  ),
                )
              }
            >
              <Pause size={15} /> Pause agent
            </button>
          ) : agent.status === "paused" && current ? (
            <button
              className="secondary"
              disabled={!!busy || dirty}
              onClick={() =>
                void onAction(
                  "Resuming sourcing agent…",
                  () =>
                    productApi.resumeAgent(
                      project.project_id,
                      agent.run_id,
                      project.version,
                    ),
                  "agent",
                )
              }
            >
              <Play size={15} /> Resume agent
            </button>
          ) : null}
          {project.package?.items.length ? (
            <button className="text-button" onClick={downloadRfqs}>
              Download quote requests
            </button>
          ) : null}
          <button className="text-button" onClick={onInspect}>
            Inspect parts & model
          </button>
        </div>
      </div>
      <p className="pf-agent-boundary">
        {agent.mandate.outreach === "demo_mailbox"
          ? "Demo mailbox · all deliveries and replies are simulated."
          : "Draft-only outreach · no external email has been sent."}{" "}
        Purchase authorization remains with you.
      </p>
      {agent.attention.length ? (
        <div className="pf-agent-attention">
          <h3>The agent needs your input</h3>
          {agent.attention.map((item, index) => (
            <p key={`${item.code}-${index}`}>{item.message}</p>
          ))}
          <button className="secondary" disabled={!!busy} onClick={onManual}>
            Review the missing inputs
          </button>
        </div>
      ) : null}
      {dirty ? (
        <p className="pf-inline-error">
          Save your source edits before resuming or starting another agent run.
        </p>
      ) : null}
      {!current ? (
        <p className="pf-inline-error">
          The source inputs changed after this run. Start a new run to use your
          latest requirements.
        </p>
      ) : null}
      {(agent.status === "failed" || !current) && !running ? (
        <button
          className="secondary"
          disabled={!!busy || dirty}
          onClick={() =>
            void onAction(
              "Starting a fresh sourcing run…",
              () =>
                productApi.startAgent(
                  project.project_id,
                  project.version,
                  agent.mode,
                ),
              "agent",
            )
          }
        >
          Start a new agent run
        </button>
      ) : null}
      {agent.targets.length && !running ? (
        <div className="pf-agent-decisions">
          <h3>
            {agent.status === "recommendation_ready"
              ? "Recommended next steps"
              : "Supplier choices"}
          </h3>
          {agent.targets.map((target) => {
            const part = project.parts.find(
              (item) => item.part_id === target.part_id,
            );
            const candidate = project.research
              .find((job) => job.part_id === target.part_id)
              ?.candidates.find(
                (item) => item.candidate_id === target.candidate_id,
              );
            return (
              <article key={target.part_id}>
                <div>
                  <h4>{part?.name ?? target.part_id}</h4>
                  <p>
                    {candidate?.supplier_name ?? "Supplier lead"}
                    {candidate?.data_origin === "synthetic_demo"
                      ? " · sample supplier"
                      : ""}
                  </p>
                </div>
                <p>{target.reason}</p>
                <small>
                  {target.readiness === "contact_required"
                    ? "A verified contact is required before outreach."
                    : "Sample quote workflow · supplier eligibility remains unverified."}
                </small>
              </article>
            );
          })}
        </div>
      ) : null}
      {messages.length ? (
        <section
          className="pf-agent-mailbox"
          aria-labelledby="agent-mailbox-title"
        >
          <div className="pf-section-heading">
            <div>
              <h3 id="agent-mailbox-title">
                <Mail size={17} /> Demo mailbox
              </h3>
              <p>
                Simulated delivery records and sample replies for this run. No
                real mailbox is connected.
              </p>
            </div>
            <span>
              {sent.length} sent · {replies.length} replies
            </span>
          </div>
          <div className="pf-mailbox-columns">
            <MailboxFolder title="Sent quote requests" messages={sent} />
            <MailboxFolder title="Inbox · sample replies" messages={replies} />
          </div>
        </section>
      ) : null}
      <details className="pf-agent-timeline">
        <summary>
          Agent activity & decisions · {events.length} recorded events
        </summary>
        <ol>
          {events.slice(-40).map((event) => (
            <li key={event.sequence}>
              <time dateTime={event.created_at}>
                {new Date(event.created_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </time>
              <span>{event.summary}</span>
            </li>
          ))}
        </ol>
      </details>
      {agent.status === "recommendation_ready" ? (
        <p className="pf-agent-finished">
          <Check size={16} /> Quotes and a recommendation are ready. No purchase
          or supplier commitment has been made.
        </p>
      ) : null}
    </section>
  );
}
function MailboxFolder({
  title,
  messages,
}: {
  title: string;
  messages: ProductMailboxMessage[];
}) {
  return (
    <div className="pf-mailbox-folder">
      <h4>{title}</h4>
      {messages.length ? (
        messages.map((message) => (
          <details className="pf-mail-message" key={message.message_id}>
            <summary>
              <span>
                <strong>{message.subject}</strong>
                <small>
                  {message.direction === "outbound"
                    ? `To ${message.to_label}`
                    : `From ${message.from_label}`}
                </small>
              </span>
              <span>Simulated</span>
            </summary>
            <dl>
              <div>
                <dt>From</dt>
                <dd>{message.from_label}</dd>
              </div>
              <div>
                <dt>To</dt>
                <dd>{message.to_label}</dd>
              </div>
              <div>
                <dt>Supplier</dt>
                <dd>{message.intended_supplier}</dd>
              </div>
            </dl>
            <p className="pf-mail-body">{message.body}</p>
            {message.quote ? (
              <p className="pf-mail-quote">
                Sample quote:{" "}
                {message.quote.price != null
                  ? `${message.quote.currency ?? ""} ${message.quote.price.toLocaleString()}`
                  : "Price not provided"}
                {message.quote.lead_time_days != null
                  ? ` · ${message.quote.lead_time_days} days`
                  : ""}
              </p>
            ) : null}
          </details>
        ))
      ) : (
        <p className="pf-mail-empty">
          {title.startsWith("Sent")
            ? "Quote requests will appear when the agent records simulated delivery."
            : "Sample replies will appear after the demo supplier responds."}
        </p>
      )}
    </div>
  );
}
