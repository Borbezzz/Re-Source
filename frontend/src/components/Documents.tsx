import { useState } from "react";
import { Download, Send, Check, Save, FileText } from "lucide-react";
import { api, type Command } from "../api/client.ts";
import { submissionBlock } from "../api/guards.ts";
import type { CaseView, DocumentsView, Schema } from "../api/types.ts";
import {
  Badge,
  Empty,
  EvidenceLink,
  Loading,
  Status,
  human,
} from "./Primitives.tsx";

export function Documents({
  view,
  documents,
  busy,
  execute,
  onEvidence,
}: {
  view: CaseView;
  documents: DocumentsView | null;
  busy: boolean;
  execute: (c: Command<unknown>) => Promise<boolean>;
  onEvidence: (id: string) => void;
}) {
  if (!documents) return <Loading>Loading documents…</Loading>;
  const pkg = documents.current_package;
  if (!pkg)
    return (
      <Empty
        title={
          documents.generation_status === "preparing"
            ? "Preparing the approval pack"
            : "Choose a recovery option first"
        }
      >
        {documents.generation_status === "preparing"
          ? "The server is preparing source-backed drafts. Completed documents will appear here."
          : "Review supplier compatibility, then select an eligible option to prepare its draft package."}
      </Empty>
    );
  const blocked = submissionBlock(view, pkg),
    stale = pkg.status !== "current";
  const blocking = Array.isArray(documents.readiness.blocking)
    ? documents.readiness.blocking
    : [];
  const tasks = Array.isArray(documents.readiness.completion_tasks)
    ? documents.readiness.completion_tasks
    : [];
  return (
    <div className="document-workspace">
      <section className="document-content">
        <div className="section-heading">
          <div>
            <h2>Review the approval pack</h2>
            <p className="muted">
              Version {pkg.version} · Draft documents, subject to qualified
              review
            </p>
          </div>
          <Status value={pkg.review_state} />
        </div>
        <p>{pkg.route_explanation}</p>
        {stale && (
          <div className="warning-box">
            This package is stale. Select an option from the latest decision to
            regenerate it.
          </div>
        )}
        {documents.current_drafts.map((draft) => (
          <Draft
            key={`${draft.draft_id}:${pkg.version}`}
            draft={draft}
            packageVersion={pkg.version}
            busy={busy || stale}
            execute={execute}
            onEvidence={onEvidence}
          />
        ))}
      </section>
      <aside className="document-actions">
        <h3>Package review</h3>
        <div className="inline">
          <Badge>Version {pkg.version}</Badge>
          <Status value={pkg.status} />
        </div>
        <p className="muted">
          Confirm the fields and their evidence before approving this exact
          version.
        </p>
        <dl className="facts">
          <div>
            <dt>Blocking fields</dt>
            <dd>{blocking.length}</dd>
          </div>
          <div>
            <dt>Completion tasks</dt>
            <dd>{tasks.length}</dd>
          </div>
          <div>
            <dt>Destination</dt>
            <dd>{human(pkg.destination_type)}</dd>
          </div>
        </dl>
        {blocking.length > 0 && (
          <div className="warning-box">
            {blocking.map((b, i) => (
              <p key={i}>{human(b)}</p>
            ))}
          </div>
        )}
        <button
          className="primary"
          disabled={
            busy ||
            stale ||
            blocking.length > 0 ||
            pkg.review_state === "approved"
          }
          onClick={() =>
            void execute(
              api.editDocument(pkg.package_id, pkg.version, {}, "approve"),
            )
          }
        >
          <Check size={16} />
          Approve package
        </button>
        <button
          className="secondary"
          disabled={busy || stale}
          onClick={() =>
            void execute(
              api.editDocument(
                pkg.package_id,
                pkg.version,
                {},
                "request_changes",
              ),
            )
          }
        >
          Request changes
        </button>
        <a
          className="secondary button-link"
          href={api.packageUrl(pkg.package_id)}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Download size={16} />
          Download draft
        </a>
        <hr />
        <button
          className="primary"
          disabled={busy || !!blocked}
          onClick={() => void execute(api.submit(view, pkg))}
        >
          <Send size={16} />
          Simulate submission
        </button>
        {blocked && <p className="small muted">{blocked}</p>}
        <p className="small">
          Simulation only. No supplier order or regulatory filing is sent.
        </p>
        {documents.receipts.map((receipt) => (
          <div className="receipt" key={receipt.receipt_id}>
            <Badge>SIMULATED</Badge>
            <h4>Receipt recorded</h4>
            <p className="small">{receipt.receipt_id}</p>
            <p className="small muted">
              Package version {receipt.package_version}
            </p>
          </div>
        ))}
        {documents.history.length > 1 && (
          <details>
            <summary>Package history ({documents.history.length})</summary>
            {documents.history.map((p) => (
              <p key={p.package_id} className="small">
                Version {p.version} · {human(p.status)} ·{" "}
                {human(p.review_state)}
              </p>
            ))}
          </details>
        )}
      </aside>
    </div>
  );
}
function Draft({
  draft,
  packageVersion,
  busy,
  execute,
  onEvidence,
}: {
  draft: Schema<"DocumentDraft">;
  packageVersion: number;
  busy: boolean;
  execute: (c: Command<unknown>) => Promise<boolean>;
  onEvidence: (id: string) => void;
}) {
  const [edits, setEdits] = useState<Record<string, string>>({});
  return (
    <details className="draft" open>
      <summary>
        <FileText size={19} />
        <span>{draft.template_title}</span>
        <Status value={draft.review_state} />
      </summary>
      <p className="muted small">{draft.why_included}</p>
      <div className="draft-fields">
        {draft.fields.map((field) => (
          <div key={field.field_id} className="draft-field">
            <label htmlFor={`${draft.draft_id}-${field.field_id}`}>
              {field.label}
              {field.required && <span className="muted"> · required</span>}
            </label>
            <div>
              {field.editable ? (
                <textarea
                  id={`${draft.draft_id}-${field.field_id}`}
                  rows={
                    typeof field.value === "string" && field.value.length > 120
                      ? 3
                      : 1
                  }
                  disabled={busy}
                  value={
                    edits[field.field_id] ??
                    (field.value == null ? "" : human(field.value))
                  }
                  onChange={(e) =>
                    setEdits((prev) => ({
                      ...prev,
                      [field.field_id]: e.target.value,
                    }))
                  }
                />
              ) : (
                <p id={`${draft.draft_id}-${field.field_id}`}>
                  {human(field.value)}
                </p>
              )}
              <div className="field-meta">
                <Status value={field.status} />
                <span>{human(field.provenance.origin)}</span>
              </div>
              {field.note && <p className="small muted">{field.note}</p>}
              {field.responsible && (
                <p className="small muted">Owner: {field.responsible}</p>
              )}
              <div className="citations">
                {field.provenance.evidence_refs.map((id) => (
                  <EvidenceLink key={id} id={id} onOpen={onEvidence} />
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="draft-footer">
        <span className="small muted">
          Edits create a new version and reset approval.
        </span>
        <button
          className="secondary"
          disabled={busy || !Object.keys(edits).length}
          onClick={() =>
            void execute(
              api.editDocument(draft.draft_id, packageVersion, edits),
            )
          }
        >
          <Save size={15} />
          Save field edits
        </button>
      </div>
    </details>
  );
}
