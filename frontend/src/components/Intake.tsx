import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowLeft,
  ExternalLink,
  FileUp,
  FileCheck2,
  RefreshCw,
} from "lucide-react";
import { api } from "../api/client.ts";
import { meshSourceBlock } from "../api/guards.ts";
import { watchEvents, type ConnectionState } from "../api/events.ts";
import type { EngineView, Schema } from "../api/types.ts";
import { Badge, ErrorNotice, Loading, Status, human } from "./Primitives.tsx";
type Upload = Schema<"IntakeUpload">;
type Draft = Schema<"PartRequirementDraft">;
interface Saved {
  blueprintId?: string;
  requirementsId?: string;
  draftId?: string;
  jobId?: string;
  componentId?: string;
}
const accepted = ".pdf,.png,.jpg,.jpeg,.txt,.md,.json";
export function Intake({
  engine,
  onExplore,
  onActivated,
}: {
  engine: EngineView | null;
  onExplore: () => void;
  onActivated: () => Promise<void>;
}) {
  const [blueprint, setBlueprint] = useState<File | null>(null),
    [requirements, setRequirements] = useState<File | null>(null),
    [uploads, setUploads] = useState<{
      blueprint?: Upload;
      requirements?: Upload;
    }>({});
  const [componentId, setComponentId] = useState("component-primary"),
    [draft, setDraft] = useState<Draft | null>(null),
    [job, setJob] = useState<Schema<"MeshJob"> | null>(null);
  const [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [connection, setConnection] = useState<ConnectionState>("connecting"),
    [available, setAvailable] = useState<boolean | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({}),
    [activeField, setActiveField] = useState<string | null>(null),
    [reviewedJob, setReviewedJob] = useState<string | null>(null);
  const ids = useRef<Saved>({}),
    alive = useRef(true),
    locked = useRef(false);
  const runId = engine?.scenario_run_id,
    storageKey = runId ? `resource:intake:v1:${runId}` : null;
  const save = (next: Saved) => {
    ids.current = { ...ids.current, ...next };
    if (storageKey)
      try {
        sessionStorage.setItem(storageKey, JSON.stringify(ids.current));
      } catch {}
  };
  const refresh = async () => {
    const c = ids.current;
    const [d, j] = await Promise.all([
      c.draftId ? api.requirementDraft(c.draftId) : null,
      c.jobId ? api.meshJobStatus(c.jobId) : null,
    ]);
    if (alive.current) {
      // Upload/validation events can finish a refresh for the previous job
      // after a new command has replaced it. Keep the current identity.
      if (d && ids.current.draftId === c.draftId) setDraft(d);
      if (j && ids.current.jobId === c.jobId) setJob(j);
    }
  };
  useEffect(() => {
    alive.current = true;
    const abort = new AbortController();
    // Let the engine request establish the visitor cookie before parallel APIs.
    if (!runId || !storageKey)
      return () => {
        alive.current = false;
        abort.abort();
      };
    api
      .manifest(abort.signal)
      .then(() => setAvailable(true))
      .catch(() => {
        if (!abort.signal.aborted) setAvailable(false);
      });
    try {
      ids.current = JSON.parse(sessionStorage.getItem(storageKey) ?? "{}");
    } catch {
      ids.current = {};
    }
    const saved = ids.current;
    if (saved.componentId) setComponentId(saved.componentId);
    void Promise.all([
      saved.blueprintId
        ? api.uploadStatus(saved.blueprintId, abort.signal)
        : undefined,
      saved.requirementsId
        ? api.uploadStatus(saved.requirementsId, abort.signal)
        : undefined,
    ])
      .then(([b, r]) => {
        if (alive.current) setUploads({ blueprint: b, requirements: r });
      })
      .catch((e) => {
        if (!abort.signal.aborted) setError(e.message);
      });
    void refresh().catch((e) => {
      if (alive.current) setError(e.message);
    });
    const stop = watchEvents({
      caseId: "__run__",
      runId,
      streamPath: `/api/v1/scenario-runs/${encodeURIComponent(runId)}/events`,
      onConnection: setConnection,
      onSnapshotRequired: () => {
        void refresh().catch((e) => setError(e.message));
      },
      onEvent: (e) => {
        if (e.type.startsWith("intake.") || e.type === "manifest.updated")
          void refresh().catch((e) => setError(e.message));
      },
    });
    return () => {
      alive.current = false;
      abort.abort();
      stop();
    };
  }, [runId, storageKey]);
  const action = async (label: string, work: () => Promise<void>) => {
    if (locked.current) return;
    locked.current = true;
    setBusy(label);
    setError("");
    try {
      await work();
    } catch (e) {
      if (alive.current)
        setError(
          e instanceof Error ? e.message : "Request failed. Please retry.",
        );
    } finally {
      locked.current = false;
      if (alive.current) setBusy("");
    }
  };
  const extract = () =>
    action("Uploading and extracting…", async () => {
      if (!blueprint || !requirements) return;
      if (Math.max(blueprint.size, requirements.size) > 4 * 1024 * 1024)
        throw new Error("Each source must be 4 MB or smaller for web upload.");
      const b = await api.upload(blueprint, "blueprint").execute();
      save({ blueprintId: b.upload_id, componentId });
      const r = await api
        .upload(requirements, "part_requirements", componentId)
        .execute();
      save({ requirementsId: r.upload_id });
      setUploads({ blueprint: b, requirements: r });
      const d = await api
        .extractRequirements(r.upload_id, componentId)
        .execute();
      save({ draftId: d.draft_id });
      setDraft(d);
      await refresh();
    });
  const patch = (confirm = false) =>
    action(confirm ? "Confirming…" : "Saving corrections…", async () => {
      if (!draft) return;
      const changes = Object.fromEntries(
        Object.entries(edits).map(([key, value]) => {
          if (Array.isArray(draft.fields.find((f) => f.name === key)?.value)) {
            try {
              return [key, JSON.parse(value)];
            } catch {}
          }
          return [key, value];
        }),
      );
      const d = await api
        .patchRequirements(draft, changes, confirm ? "confirm" : undefined)
        .execute();
      setDraft(d);
      setEdits({});
    });
  const generate = () =>
    action("Requesting generation…", async () => {
      if (!uploads.blueprint || draft?.status !== "confirmed") return;
      const j = await api.meshJob(uploads.blueprint.upload_id).execute();
      save({ jobId: j.job_id });
      setJob(j);
    });
  const uploadMesh = (file: File) =>
    action("Validating segmented mesh…", async () => {
      if (draft?.status !== "confirmed") return;
      if (file.size > 4 * 1024 * 1024)
        throw new Error(
          "The segmented GLB must be 4 MB or smaller for web upload.",
        );
      const u = await api.upload(file, "mesh_glb").execute();
      const j = await api.meshJob(u.upload_id).execute();
      save({ jobId: j.job_id });
      setJob(j);
    });
  const activate = () =>
    action("Activating assembly…", async () => {
      if (
        !job ||
        reviewedJob !== job.job_id ||
        meshSourceBlock(job, uploads.blueprint?.upload_id)
      )
        return;
      await api.activateMesh(job.job_id).execute();
      await onActivated();
      onExplore();
    });
  const field =
    draft?.fields.find((f) => f.name === activeField) ??
    draft?.fields.find((f) => f.source_ref);
  const canConfirm =
    draft?.status === "needs_review" &&
    !draft.fields.some(
      (f) =>
        (f.required && f.validation_state !== "valid") ||
        f.validation_state === "invalid",
    );
  const sourceBlock = job
    ? meshSourceBlock(job, uploads.blueprint?.upload_id)
    : null;
  if (draft)
    return (
      <main className="intake-review content-width">
        <div className="section-heading">
          <div>
            <h1>
              {draft.status === "confirmed"
                ? "Generate the assembly."
                : "Confirm the part requirements."}
            </h1>
            <p>
              Blueprint + part specification ·{" "}
              {
                engine?.components.find(
                  (c) => c.component_id === draft.component_id,
                )?.part_identity
              }{" "}
              · version {draft.version}
            </p>
          </div>
          <div className="inline">
            <Badge>{human(draft.status)}</Badge>
            <button
              className="secondary compact"
              disabled={!!busy}
              onClick={() => void action("Refreshing…", refresh)}
            >
              <RefreshCw size={14} />
              Refresh status
            </button>
          </div>
        </div>
        {error && <ErrorNotice>{error}</ErrorNotice>}
        {busy && <Loading>{busy}</Loading>}
        {draft.status === "extracting" ? (
          <div className="extraction-state">
            <Loading>Extracting source-linked fields…</Loading>
            <p>Updates arrive from the extraction service · {connection}</p>
          </div>
        ) : (
          <>
            <div className="source-review-grid">
              <section className="source-preview">
                <h3>
                  {uploads.requirements?.filename ?? "Uploaded specification"}
                </h3>
                <SourcePreview upload={uploads.requirements} />
                {field?.source_ref && (
                  <div className="source-region">
                    <strong>{field.label} · cited source</strong>
                    <p className="small">
                      {field.source_ref.page
                        ? `Page ${field.source_ref.page}`
                        : ""}
                      {field.source_ref.line
                        ? ` · Line ${field.source_ref.line}`
                        : ""}
                    </p>
                    <blockquote>
                      {field.source_ref.excerpt ?? "No text excerpt supplied."}
                    </blockquote>
                    {field.source_ref.bbox && (
                      <p className="small muted">
                        Document region: {field.source_ref.bbox.join(", ")}{" "}
                        (source coordinates)
                      </p>
                    )}
                  </div>
                )}
              </section>
              <section className="requirement-fields">
                <h2>
                  {draft.status === "confirmed"
                    ? "Confirmed source fields"
                    : "Review extracted fields"}
                </h2>
                <p className="muted small">
                  Unknown values stay blank. Check every value against its
                  source.
                </p>
                {draft.fields.map((f) => (
                  <div className="requirement-field" key={f.name}>
                    <div className="section-heading">
                      <label htmlFor={`req-${f.name}`}>
                        {f.label}
                        {f.required ? " · required" : ""}
                      </label>
                      <Status value={f.validation_state} />
                    </div>
                    <textarea
                      id={`req-${f.name}`}
                      rows={f.name === "description" ? 2 : 1}
                      disabled={!!busy || draft.status !== "needs_review"}
                      value={
                        edits[f.name] ??
                        (f.value == null
                          ? ""
                          : typeof f.value === "object"
                            ? JSON.stringify(f.value)
                            : String(f.value))
                      }
                      onFocus={() => setActiveField(f.name)}
                      onChange={(e) =>
                        setEdits((p) => ({ ...p, [f.name]: e.target.value }))
                      }
                    />
                    <div className="field-meta">
                      <span>{f.unit ?? "No unit supplied"}</span>
                      <span>
                        {f.confidence == null
                          ? "Confidence unknown"
                          : `${Math.round(f.confidence * 100)}% extraction confidence`}
                      </span>
                      <span>{human(f.extraction_mode)}</span>
                    </div>
                    {f.source_ref ? (
                      <button
                        className="text-button compact"
                        onClick={() => setActiveField(f.name)}
                      >
                        View source{" "}
                        {f.source_ref.page
                          ? `· page ${f.source_ref.page}`
                          : f.source_ref.line
                            ? `· line ${f.source_ref.line}`
                            : ""}
                      </button>
                    ) : (
                      <p className="small warning">
                        No source location supplied.
                      </p>
                    )}
                    {f.validation_note && (
                      <p className="small muted">{f.validation_note}</p>
                    )}
                  </div>
                ))}
                {draft.status === "needs_review" && (
                  <div className="review-actions">
                    <button
                      className="secondary"
                      disabled={!!busy || !Object.keys(edits).length}
                      onClick={() => void patch()}
                    >
                      Save corrections
                    </button>
                    <button
                      className="primary"
                      disabled={
                        !!busy || !canConfirm || !!Object.keys(edits).length
                      }
                      onClick={() => void patch(true)}
                    >
                      Confirm requirements <ArrowRight size={16} />
                    </button>
                    <p className="small muted">
                      Save corrections before confirming. Confirmation triggers
                      reassessment for this component.
                    </p>
                  </div>
                )}
              </section>
            </div>
            <div className="warning-box">
              <strong>Compatibility scope</strong>
              <p>
                Uploaded part number and revision feed automated identity
                checks. Uploaded material, dimensions, tolerances and
                certification requirements still need an engineering evidence
                review; they are not automatically verified by this build.
              </p>
            </div>
            {draft.status === "confirmed" && (
              <section className="generation-panel">
                <h2>Generate a selectable 3D assembly</h2>
                <p className="muted">
                  Create real meshes from the blueprint, then validate every
                  part identity against its source.
                </p>
                {!job ? (
                  <button
                    className="primary"
                    disabled={!!busy || !uploads.blueprint}
                    onClick={() => void generate()}
                  >
                    Generate assembly <ArrowRight size={16} />
                  </button>
                ) : (
                  <div className="mesh-job">
                    <div className="inline">
                      <Status value={job.status} />
                      <Badge>
                        {job.provider === "none"
                          ? "Provider not connected"
                          : job.provider}
                      </Badge>
                    </div>
                    <h3>
                      {job.status === "provider_required"
                        ? "A mesh-generation provider is required."
                        : job.status === "succeeded"
                          ? "Mesh validation passed."
                          : "Mesh validation needs attention."}
                    </h3>
                    <p>
                      {job.status === "provider_required"
                        ? "Your sources and confirmed requirements are saved. No 3D mesh has been generated. Connect a server-side generation provider to continue."
                        : job.message}
                    </p>
                    {job.validation?.checks.map((c) => (
                      <div className="mesh-check" key={c.node_name}>
                        <strong>{c.node_name}</strong>
                        <Status value={c.ok ? "valid" : "invalid"} />
                        <p className="small muted">{c.problems.join(" · ")}</p>
                        {c.source_ref && (
                          <p className="small">
                            {c.component_id} ·{" "}
                            {c.source_ref.page
                              ? `Page ${c.source_ref.page}`
                              : c.source_ref.line
                                ? `Line ${c.source_ref.line}`
                                : "Source reference"}
                            {c.source_ref.excerpt && (
                              <> — {c.source_ref.excerpt}</>
                            )}
                          </p>
                        )}
                      </div>
                    ))}
                    {job.status === "succeeded" && (
                      <>
                        {uploads.blueprint && (
                          <a
                            className="text-button"
                            href={api.uploadUrl(uploads.blueprint.upload_id)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Review blueprint source <ExternalLink size={14} />
                          </a>
                        )}
                        {sourceBlock ? (
                          <p className="warning" role="status">
                            {sourceBlock}
                          </p>
                        ) : (
                          <label className="identity-review">
                            <input
                              type="checkbox"
                              checked={reviewedJob === job.job_id}
                              onChange={(e) =>
                                setReviewedJob(
                                  e.target.checked ? job.job_id : null,
                                )
                              }
                            />{" "}
                            I checked every part identity and cited location
                            against the blueprint. This is not an engineering
                            approval.
                          </label>
                        )}
                        <button
                          className="primary"
                          disabled={
                            !!busy ||
                            !!sourceBlock ||
                            reviewedJob !== job.job_id
                          }
                          onClick={() => void activate()}
                        >
                          Activate validated assembly
                        </button>
                      </>
                    )}
                  </div>
                )}
                <details>
                  <summary>Use an existing segmented GLB</summary>
                  <p className="small muted">
                    The file must contain the manifest’s named component meshes
                    and source references in node metadata. A model does not
                    prove dimensional accuracy or compatibility.
                  </p>
                  <label className="secondary file-button">
                    Choose segmented GLB
                    <input
                      type="file"
                      accept=".glb"
                      disabled={!!busy}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) void uploadMesh(file);
                      }}
                    />
                  </label>
                </details>
              </section>
            )}
            <div className="inline">
              <button className="text-button" onClick={onExplore}>
                Open recovery workspace <ArrowRight size={16} />
              </button>
              <button
                className="text-button"
                disabled={!!busy}
                onClick={() => {
                  ids.current = {};
                  if (storageKey) sessionStorage.removeItem(storageKey);
                  setDraft(null);
                  setJob(null);
                  setUploads({});
                  setEdits({});
                }}
              >
                <ArrowLeft size={15} />
                Start another intake
              </button>
            </div>
          </>
        )}
      </main>
    );
  return (
    <main className="intake">
      <section className="intake-copy">
        <h1>Start with the source.</h1>
        <p className="intro">
          A clearer path from jet-engine parts to a verified supply decision.
        </p>
        <ol className="input-steps">
          <li className="current">Upload sources</li>
          <li>Confirm requirements</li>
          <li>Generate assembly</li>
        </ol>
        <div className="upload-field">
          <FileUp size={24} />
          <div>
            <h2>Blueprint</h2>
            <p>Assembly drawing, diagram or blueprint.</p>
            <label className="secondary file-button">
              {blueprint ? blueprint.name : "Choose blueprint"}
              <input
                type="file"
                accept={accepted}
                disabled={!!busy}
                onChange={(e) => setBlueprint(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>
        </div>
        <div className="upload-field">
          <FileCheck2 size={24} />
          <div>
            <h2>Part requirements</h2>
            <p>
              Dimensions, materials, tolerances and required certifications.
            </p>
            <label className="secondary file-button">
              {requirements ? requirements.name : "Choose specification"}
              <input
                type="file"
                accept={accepted}
                disabled={!!busy}
                onChange={(e) => setRequirements(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>
        </div>
        <label className="component-target">
          Map this specification to
          <select
            value={componentId}
            disabled={!!busy}
            onChange={(e) => setComponentId(e.target.value)}
          >
            {engine?.components.map((c) => (
              <option key={c.component_id} value={c.component_id}>
                {c.part_identity} · {c.display_name}
              </option>
            ))}
          </select>
          <small className="muted">
            This build supports three existing component identities. Your
            document supplies its own requirements.
          </small>
        </label>
        <button
          className="primary"
          disabled={
            !!busy || !available || !engine || !blueprint || !requirements
          }
          onClick={() => void extract()}
        >
          {busy || "Extract & review requirements"} <ArrowRight size={16} />
        </button>
        {error && <ErrorNotice>{error}</ErrorNotice>}
        <p className="small muted" role="status">
          {available === false
            ? "The intake service is unavailable on this server."
            : "PDF, image or structured text · up to 4 MB each. Review extraction before generating the assembly."}
        </p>
        <div className="demo-entry">
          <div>
            <strong>Explore the recovery workflow</strong>
            <p className="small muted">
              A representative engine, three selectable components and synthetic
              supplier evidence.
            </p>
          </div>
          <button className="text-button" onClick={onExplore}>
            Open seeded workspace <ArrowRight size={16} />
          </button>
        </div>
      </section>
      <aside className="intake-art">
        <div className="art-caption">
          <Badge>Jet-engine recovery</Badge>
          <span>From requirement to recovery.</span>
        </div>
        <img
          src="/images/engine-concept.png"
          width="1536"
          height="1024"
          alt="Illustrative exploded turbofan engine with fan, compressor, combustor and turbine stages"
        />
        <div className="art-note">
          <h2>
            See the part.
            <br />
            Understand the options.
          </h2>
          <p>
            Source-backed requirements stay connected to every supplier check
            and draft approval.
          </p>
          <small>AI-generated illustration. Not an engineering model.</small>
        </div>
      </aside>
    </main>
  );
}
function SourcePreview({ upload }: { upload?: Upload }) {
  const [text, setText] = useState("");
  useEffect(() => {
    if (!upload || !upload.media_type.startsWith("text/")) return;
    const abort = new AbortController();
    fetch(api.uploadUrl(upload.upload_id), { signal: abort.signal })
      .then((r) => r.text())
      .then(setText)
      .catch(() => {});
    return () => abort.abort();
  }, [upload?.upload_id]);
  if (!upload) return <p className="muted">Source details are loading.</p>;
  const url = api.uploadUrl(upload.upload_id);
  return (
    <>
      <a
        className="text-button compact"
        href={url}
        target="_blank"
        rel="noopener noreferrer"
      >
        Open original source <ExternalLink size={13} />
      </a>
      {upload.media_type.startsWith("image/") ? (
        <img src={url} alt={`Uploaded source: ${upload.filename}`} />
      ) : upload.media_type === "application/pdf" ? (
        <iframe
          sandbox="allow-same-origin"
          title="Uploaded specification PDF"
          src={url}
        />
      ) : (
        <pre>
          {text || "Open the original source to inspect this document."}
        </pre>
      )}
    </>
  );
}
