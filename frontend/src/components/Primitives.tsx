import {
  Check,
  CircleHelp,
  CircleX,
  ExternalLink,
  FileText,
  LoaderCircle,
} from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { api } from "../api/client.ts";
import { sourceUrl } from "../api/guards.ts";
import type { Schema } from "../api/types.ts";
export const human = (value: unknown): string =>
  typeof value === "string"
    ? value.replaceAll("_", " ")
    : value == null
      ? "Not provided"
      : typeof value === "object"
        ? JSON.stringify(value)
        : String(value);
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function Status({ value }: { value: string }) {
  const good = [
    "pass",
    "eligible",
    "approved",
    "current",
    "completed",
    "filled",
    "ready",
    "valid",
  ].includes(value);
  const bad = ["fail", "ineligible", "failed", "stale", "invalid"].includes(
    value,
  );
  const Icon = good ? Check : bad ? CircleX : CircleHelp;
  return (
    <span className={`status ${good ? "good" : bad ? "bad" : "unknown"}`}>
      <Icon size={14} />
      {value === "pass"
        ? "Match"
        : value === "fail"
          ? "Mismatch"
          : human(value)}
    </span>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function Loading({ children = "Loading…" }: { children?: ReactNode }) {
  return (
    <div className="loading" role="status">
      <LoaderCircle size={18} className="spin" />
      {children}
    </div>
  );
}
export function ErrorNotice({
  children,
  retry,
}: {
  children: ReactNode;
  retry?: () => void;
}) {
  return (
    <div className="error-notice" role="alert">
      <CircleX size={18} />
      <span>{children}</span>
      {retry && (
        <button className="text-button" onClick={retry}>
          Retry
        </button>
      )}
    </div>
  );
}
export function EvidenceLink({
  id,
  onOpen,
}: {
  id: string;
  onOpen: (id: string) => void;
}) {
  return (
    <button className="citation" onClick={() => onOpen(id)}>
      <FileText size={12} />
      {id}
    </button>
  );
}
export function EvidencePanel({
  id,
  onClose,
}: {
  id: string;
  onClose: () => void;
}) {
  const [value, setValue] = useState<Schema<"EvidenceView"> | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    setValue(null);
    setError("");
    api
      .evidence(id, abort.signal)
      .then(setValue)
      .catch((e) => {
        if (!abort.signal.aborted) setError(e.message);
      });
    return () => abort.abort();
  }, [id]);
  const e = value?.evidence,
    url = sourceUrl(e?.source_url);
  return (
    <section className="evidence-panel" aria-label="Evidence detail">
      <div className="section-heading">
        <h3>Source evidence</h3>
        <button onClick={onClose} className="text-button">
          Close
        </button>
      </div>
      {error ? (
        <ErrorNotice>{error}</ErrorNotice>
      ) : !e ? (
        <Loading />
      ) : (
        <>
          <h3>{e.title}</h3>
          <div className="inline">
            <Badge>{human(e.data_origin)}</Badge>
            <Status value={e.validation_state} />
          </div>
          <dl className="facts">
            <div>
              <dt>Revision</dt>
              <dd>{e.revision ?? "Not stated"}</dd>
            </div>
            <div>
              <dt>Authority</dt>
              <dd>{e.authority}</dd>
            </div>
            <div>
              <dt>Retrieved</dt>
              <dd>{new Date(e.retrieved_at).toLocaleString("en-GB")}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>
                {url ? (
                  <a href={url} target="_blank" rel="noopener noreferrer">
                    Open source <ExternalLink size={13} />
                  </a>
                ) : (
                  "No public URL; stored evidence"
                )}
              </dd>
            </div>
          </dl>
          {value?.status === "superseded" && (
            <p className="warning">
              Superseded by {value.superseded_by}. Review the latest evidence.
            </p>
          )}
          <pre className="source-excerpt">
            {value?.preview_text ??
              e.content_text ??
              "No text preview is available."}
          </pre>
          {value?.facts.map((f) => (
            <div className="fact-row" key={f.fact_id}>
              <strong>{human(f.field)}</strong>
              <span>{human(f.typed_value)}</span>
            </div>
          ))}
        </>
      )}
    </section>
  );
}

export function EvidenceDialog({
  id,
  onClose,
}: {
  id: string;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const node = dialog.current;
    node?.showModal();
    return () => node?.close();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="evidence-overlay"
      onCancel={onClose}
      aria-label="Source evidence"
    >
      <button
        className="evidence-backdrop"
        tabIndex={-1}
        aria-label="Close evidence"
        onClick={onClose}
      />
      <EvidencePanel id={id} onClose={onClose} />
    </dialog>
  );
}
