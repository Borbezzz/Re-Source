import {
  lazy,
  Suspense,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  ExternalLink,
  FilePlus2,
  Plus,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { sourceUrl } from "../api/guards.ts";
import { productApi } from "./client.ts";
import type { DemoProduct, ProductPart, ProductProject } from "./types.ts";
import { AgentLaunch, AgentRun } from "./AgentRun.tsx";
import { ProductResearch } from "./ProductResearch.tsx";
import "./product-flow.css";
const AssemblyScene = lazy(() => import("./AssemblyScene.tsx"));
export type ProductEntry = "gallery" | "upload" | `project:${string}`;
type Step = "agent" | "sources" | "assembly" | "research" | "approval";
export type ProjectAction = (
  label: string,
  work: () => Promise<ProductProject>,
  next?: Step,
) => Promise<void>;
const agentWorking = (project: ProductProject) =>
  project.agent?.status === "queued" || project.agent?.status === "running";
const pending = (project: ProductProject) =>
  agentWorking(project) ||
  project.status === "extracting" ||
  project.research.some(
    (job) => job.status === "queued" || job.status === "running",
  );
const resumeAt = (project: ProductProject): Step =>
  project.agent || (project.demo_id && !project.research.length)
    ? "agent"
    : project.package
      ? "approval"
      : project.research.length
        ? "research"
        : project.parts.length &&
            project.parts.every((part) => part.status === "confirmed")
          ? "assembly"
          : "sources";
const errorText = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";

export function ProductFlow({
  entry,
  onProjectOpened,
  onNew,
  onDirtyChange,
}: {
  entry: ProductEntry;
  onProjectOpened: (id: string) => void;
  onNew: () => void;
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const [project, setProject] = useState<ProductProject | null>(null);
  const [demos, setDemos] = useState<DemoProduct[]>([]);
  const [screen, setScreen] = useState(entry);
  const [openSections, setOpenSections] = useState<Record<Step, boolean>>({
    agent: false,
    sources: true,
    assembly: false,
    research: false,
    approval: false,
  });
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [sourceDirty, setSourceDirty] = useState(false);
  const [manualMode, setManualMode] = useState(false);
  const reportDirty = useRef(onDirtyChange);
  reportDirty.current = onDirtyChange;
  useEffect(() => {
    reportDirty.current?.(sourceDirty);
  }, [sourceDirty]);
  useEffect(
    () => () => {
      reportDirty.current?.(false);
    },
    [],
  );
  const [focusRequest, setFocusRequest] = useState<{
    section: Step;
    serial: number;
  } | null>(null);
  const currentProject = useRef<ProductProject | null>(null);
  const actionLock = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const reveal = (section: Step) => {
    setOpenSections({
      agent: section === "agent",
      sources: section === "sources",
      assembly: section === "assembly",
      research: section === "research",
      approval: section === "approval",
    });
    setFocusRequest((previous) => ({
      section,
      serial: (previous?.serial ?? 0) + 1,
    }));
  };
  useEffect(() => {
    if (!focusRequest) return;
    const frame = requestAnimationFrame(() => {
      const section = document.getElementById(
        `investigation-${focusRequest.section}`,
      );
      const target =
        focusRequest.section === "approval"
          ? (section?.querySelector<HTMLElement>(".pf-simulation") ?? section)
          : section;
      target?.scrollIntoView({ block: "start", behavior: "instant" });
      target?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(frame);
  }, [focusRequest]);
  const accept = (value: ProductProject) => {
    const isNew = currentProject.current?.project_id !== value.project_id;
    if (!isNew && currentProject.current!.version > value.version) return;
    currentProject.current = value;
    setProject(value);
    if (isNew) {
      setSelected([]);
      setSourceDirty(false);
      setManualMode(false);
      setOpenSections({
        agent: Boolean(value.demo_id),
        sources: !value.demo_id,
        assembly: false,
        research: false,
        approval: false,
      });
      onProjectOpened(value.project_id);
    }
  };
  useEffect(() => {
    const id = entry.startsWith("project:") ? entry.slice(8) : null;
    // Creation updates the shared URL without restarting this same workspace.
    if (id && currentProject.current?.project_id === id) {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError("");
    const request = id
      ? productApi.project(id, controller.signal).then((value) => {
          if (controller.signal.aborted) return;
          currentProject.current = value;
          setProject(value);
          setSelected(value.research.map((job) => job.part_id));
          setSourceDirty(false);
          reveal(resumeAt(value));
        })
      : productApi.demos(controller.signal).then((value) => {
          if (!controller.signal.aborted) {
            setDemos(value);
            setScreen(entry);
          }
        });
    void request
      .catch((error) => {
        if (!controller.signal.aborted) setError(errorText(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [entry]);
  const partIds = project?.parts.map((part) => part.part_id).join("|") ?? "";
  useEffect(() => {
    const allowed = new Set(project?.parts.map((part) => part.part_id) ?? []);
    setSelected((previous) => previous.filter((id) => allowed.has(id)));
  }, [partIds]);
  const active = project ? pending(project) : false;
  useEffect(() => {
    if (!project || !active) return;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    const poll = async () => {
      try {
        const next = await productApi.project(
          project.project_id,
          controller.signal,
        );
        if (
          !controller.signal.aborted &&
          (!currentProject.current ||
            currentProject.current.version <= next.version)
        ) {
          currentProject.current = next;
          setProject(next);
          setError("");
        }
      } catch (error) {
        if (!controller.signal.aborted)
          setError(`Updates paused: ${errorText(error)} Retrying…`);
      }
      if (!controller.signal.aborted) timer = setTimeout(poll, 1500);
    };
    timer = setTimeout(poll, 1500);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [project?.project_id, active]);
  const act: ProjectAction = async (label, work, next) => {
    if (actionLock.current) return;
    if (next === "agent" && sourceDirty) {
      setError("Save your source edits before starting or resuming the agent.");
      reveal("sources");
      return;
    }
    actionLock.current = true;
    setBusy(label);
    setError("");
    try {
      const value = await work();
      if (!mounted.current) return;
      accept(value);
      if (next === "agent") setManualMode(false);
      if (next) reveal(next);
    } catch (error) {
      if (mounted.current) setError(errorText(error));
    } finally {
      if (mounted.current) setBusy("");
      actionLock.current = false;
    }
  };
  const continueAction: ProjectAction = async (label, work, next) => {
    if (project && agentWorking(project)) {
      setError("Pause the sourcing agent before making manual changes.");
      reveal("agent");
      return;
    }
    if (sourceDirty) {
      setError(
        "Save and confirm your source edits before continuing this investigation.",
      );
      reveal("sources");
      return;
    }
    return act(label, work, next);
  };
  const confirmed =
    !!project?.parts.length &&
    project.parts.every((part) => part.status === "confirmed");
  const researched = !!project?.research.length;
  const complete = project?.agent
    ? project.agent.status === "recommendation_ready"
    : project?.package?.status === "simulated";
  const agentActive = !!project && agentWorking(project);
  const agentManaged = !!project?.agent && !manualMode;
  const editorBusy = busy || (agentActive ? "Sourcing agent is working" : "");
  const sourceDocumentCount =
    project?.documents.filter((document) => document.kind !== "model").length ??
    0;
  const selectedSuppliers = project
    ? Object.keys(project.selections).length
    : 0;
  const toggleSection = (section: Step) =>
    setOpenSections((current) => ({
      ...current,
      [section]: !current[section],
    }));
  return (
    <div className="pf-root">
      <div className="pf-main">
        {error ? (
          <div className="pf-error" role="alert">
            {error}
            <button aria-label="Dismiss error" onClick={() => setError("")}>
              <X size={16} />
            </button>
          </div>
        ) : null}
        {busy ? (
          <p className="pf-busy" role="status">
            {busy}
          </p>
        ) : null}
        {loading ? (
          <p className="pf-loading" role="status">
            Opening the investigation…
          </p>
        ) : !project ? (
          <>
            <div className="pf-entry-heading">
              <h1>New investigation</h1>
              <p>
                Add your design documents, or start with a prepared demo
                package.
              </p>
            </div>
            {screen === "upload" ? (
              <form
                className="pf-create"
                onSubmit={(event) => {
                  event.preventDefault();
                  void act(
                    "Creating investigation…",
                    () =>
                      productApi.create({ name: name.trim() || "New product" }),
                    "sources",
                  );
                }}
              >
                <label>
                  Product name
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="For example, a desk lamp"
                    maxLength={160}
                  />
                </label>
                <p>
                  Add your blueprint, specification or parts list next. You can
                  also add parts by hand.
                </p>
                <button className="primary" disabled={!!busy}>
                  Continue with your product <ArrowRight size={16} />
                </button>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => setScreen("gallery")}
                >
                  <ArrowLeft size={15} /> Choose a prepared demo instead
                </button>
              </form>
            ) : (
              <>
                <div className="pf-upload-choice">
                  <div>
                    <h2>Use your own design package</h2>
                    <p>
                      Start with a drawing, specification or bill of materials.
                    </p>
                  </div>
                  <button
                    className="primary"
                    onClick={() => setScreen("upload")}
                  >
                    <Upload size={17} /> Add your documents
                  </button>
                </div>
                <div className="pf-demo-heading">
                  <h2>Or explore a prepared demo</h2>
                  <p>
                    Sample documents and a matching 3D model, ready for the same
                    sourcing workflow.
                  </p>
                </div>
                <div className="pf-demo-list">
                  {demos.map((demo) => (
                    <button
                      key={demo.demo_id}
                      className="pf-demo-choice"
                      disabled={!!busy}
                      onClick={() =>
                        void act(
                          "Opening demo investigation…",
                          () => productApi.create({ demo_id: demo.demo_id }),
                          "agent",
                        )
                      }
                    >
                      <span>
                        <strong>{demo.name}</strong>
                        <span>{demo.description}</span>
                      </span>
                      <span className="pf-demo-meta">
                        {demo.part_count} parts <ArrowRight size={22} />
                      </span>
                    </button>
                  ))}
                </div>
                {!demos.length ? (
                  <p>
                    No prepared packages are available. You can still start with
                    your own documents.
                  </p>
                ) : null}
                <p className="pf-footnote">
                  Demo models are prepared in advance. Sample offers and
                  simulated purchasing remain labelled.
                </p>
              </>
            )}
          </>
        ) : (
          <>
            <div className="pf-project-heading">
              <div>
                <h1>{project.name}</h1>
                <p>
                  {complete
                    ? project.agent
                      ? "Recommendation ready · no purchase authorized"
                      : "Investigation complete · simulated purchasing"
                    : project.demo_id
                      ? "Demo investigation · sample documents and prepared geometry"
                      : "Review your parts, find suppliers and prepare a sourcing package."}
                </p>
              </div>
              <span className="pf-project-status">
                {project.agent
                  ? project.agent.status === "recommendation_ready"
                    ? "Recommendation ready"
                    : project.agent.status.replaceAll("_", " ")
                  : complete
                    ? "Complete"
                    : active
                      ? "Research in progress"
                      : project.package
                        ? "Ready for review"
                        : researched
                          ? "Choose suppliers"
                          : confirmed
                            ? "Choose parts"
                            : "Review sources"}
              </span>
            </div>
            {project.agent ? (
              <AgentRun
                project={project}
                dirty={sourceDirty}
                busy={busy}
                onAction={act}
                onInspect={() =>
                  reveal(confirmed || project.demo_id ? "assembly" : "sources")
                }
                onManual={() => {
                  setManualMode(true);
                  reveal("sources");
                }}
              />
            ) : (
              <AgentLaunch
                project={project}
                busy={busy}
                dirty={sourceDirty}
                onAction={continueAction}
                onManual={() => {
                  setManualMode(true);
                  reveal("sources");
                }}
                onInspect={() => reveal("assembly")}
              />
            )}
            <div className="pf-continuous-flow">
              <FlowSection
                id="sources"
                label="Sources & parts"
                summary={`${sourceDocumentCount} ${sourceDocumentCount === 1 ? "document" : "documents"} · ${project.parts.length} ${confirmed ? (project.parts.every((part) => part.confirmation_origin === "agent_grounded") ? "source-checked" : "reviewed") : "proposed"} parts${sourceDirty ? " · unsaved edits" : ""}`}
                completed={confirmed}
                collapsible={
                  confirmed ||
                  !!project.agent ||
                  (!!project.demo_id && !manualMode)
                }
                open={
                  project.agent || (project.demo_id && !manualMode)
                    ? openSections.sources
                    : !confirmed || openSections.sources
                }
                onToggle={() => toggleSection("sources")}
              >
                <Sources
                  key={project.project_id}
                  project={project}
                  busy={editorBusy}
                  onAction={act}
                  onDirtyChange={setSourceDirty}
                />
              </FlowSection>
              {confirmed || project.demo_id ? (
                <FlowSection
                  id="assembly"
                  label="Assembly & selected parts"
                  summary={
                    researched
                      ? `${project.research.length} parts in this investigation`
                      : `${selected.length} parts selected`
                  }
                  completed={researched}
                  collapsible={
                    researched ||
                    !!project.agent ||
                    (!!project.demo_id && !manualMode)
                  }
                  open={
                    project.agent || (project.demo_id && !manualMode)
                      ? openSections.assembly
                      : !researched || openSections.assembly
                  }
                  onToggle={() => toggleSection("assembly")}
                >
                  <Assembly
                    project={project}
                    busy={editorBusy}
                    selected={selected}
                    onSelected={setSelected}
                    onAction={continueAction}
                  />
                </FlowSection>
              ) : (
                <p className="pf-next-hint">
                  Confirm the reviewed parts to explore the assembly and start
                  supplier research.
                </p>
              )}
              {researched ? (
                <FlowSection
                  id="research"
                  label="Supplier research & choices"
                  summary={`${project.research.filter((job) => job.status === "complete").length} of ${project.research.length} parts researched · ${selectedSuppliers} supplier ${selectedSuppliers === 1 ? "choice" : "choices"}`}
                  completed={!!project.package && !agentManaged}
                  open={
                    agentManaged || !project.package || openSections.research
                  }
                  onToggle={() => toggleSection("research")}
                >
                  <ProductResearch
                    project={project}
                    agentManaged={agentManaged}
                    busy={editorBusy}
                    onAction={continueAction}
                  />
                </FlowSection>
              ) : null}
              {project.package && !agentManaged ? (
                <FlowSection
                  id="approval"
                  label="Sourcing package"
                  summary={`${project.package.items.length} ${project.package.items.length === 1 ? "RFQ" : "RFQs"} · ${project.package.status}`}
                  completed={complete}
                  open={openSections.approval || !complete}
                  onToggle={() => toggleSection("approval")}
                >
                  <Approval
                    project={project}
                    busy={busy}
                    onAction={continueAction}
                  />
                </FlowSection>
              ) : null}
            </div>
            {complete ? (
              <div className="pf-complete-next">
                <p>
                  {project.agent
                    ? "The agent run is saved with its sources, quote requests, replies and recommendation."
                    : "This investigation is saved with its sources, supplier choices and simulated receipt."}
                </p>
                <button className="secondary" onClick={onNew}>
                  Start a new investigation <ArrowRight size={16} />
                </button>
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
function FlowSection({
  id,
  label,
  summary,
  completed,
  collapsible = completed,
  open,
  onToggle,
  children,
}: {
  id: Step;
  label: string;
  summary: string;
  completed: boolean;
  collapsible?: boolean;
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <section
      id={`investigation-${id}`}
      className={`pf-flow-section ${completed ? "pf-flow-completed" : ""}`}
      tabIndex={-1}
      aria-label={label}
    >
      {collapsible ? (
        <button
          className="pf-flow-summary"
          aria-expanded={open}
          aria-controls={`investigation-${id}-content`}
          onClick={onToggle}
        >
          <span className="pf-flow-check">
            {completed ? <Check size={16} /> : null}
          </span>
          <span>
            <strong>{label}</strong>
            <small>{summary}</small>
          </span>
          <span className="pf-flow-edit">
            {open ? "Collapse" : "Review"}
            <ChevronDown size={16} />
          </span>
        </button>
      ) : null}
      <div id={`investigation-${id}-content`} hidden={!open}>
        {children}
      </div>
    </section>
  );
}
function Sources({
  project,
  busy,
  onAction,
  onDirtyChange,
}: {
  project: ProductProject;
  busy: string;
  onAction: ProjectAction;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const [parts, setParts] = useState<ProductPart[]>(project.parts),
    [kind, setKind] = useState("blueprint"),
    [reviewed, setReviewed] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const partsSignature = JSON.stringify(project.parts);
  const hasEdits = JSON.stringify(parts) !== partsSignature;
  useEffect(() => {
    onDirtyChange(hasEdits);
  }, [hasEdits, onDirtyChange]);
  useEffect(() => {
    if (!hasEdits) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [hasEdits]);
  const invalidParts = parts.some(
    (part) =>
      !part.name.trim() ||
      !Number.isInteger(part.quantity) ||
      part.quantity < 1 ||
      part.quantity > 1000000 ||
      part.requirements.some(
        (requirement) => !requirement.value.trim() || !requirement.label.trim(),
      ),
  );
  useEffect(() => {
    setParts(project.parts);
    setReviewed(false);
  }, [partsSignature]);
  const update = (index: number, value: Partial<ProductPart>) =>
    setParts((parts) =>
      parts.map((p, i) => (i === index ? { ...p, ...value } : p)),
    );
  const save = (confirm: boolean) =>
    void onAction(
      confirm ? "Confirming reviewed parts…" : "Saving your changes…",
      () =>
        productApi.parts(project.project_id, parts, confirm, project.version),
      confirm ? "assembly" : undefined,
    );
  return (
    <section className="pf-sources">
      <aside className="pf-source-files">
        <h2>Source documents</h2>
        <p>
          Use a drawing, specification or parts list. Extracted text is a
          proposal for you to review.
        </p>
        {project.documents
          .filter((d) => d.kind !== "model")
          .map((doc) => (
            <div key={doc.document_id} className="pf-file">
              <FilePlus2 size={18} />
              <span>
                <strong>{doc.name}</strong>
                <small>
                  {doc.kind === "blueprint"
                    ? "Blueprint / drawing"
                    : "Specification"}
                  {doc.data_origin === "synthetic_demo" ? " · sample" : ""}
                </small>
                {doc.excerpt ? (
                  <details>
                    <summary>Read source excerpt</summary>
                    <blockquote>{doc.excerpt}</blockquote>
                  </details>
                ) : null}
                {doc.content_url ? (
                  <a href={doc.content_url} target="_blank" rel="noreferrer">
                    Open document <ExternalLink size={12} />
                  </a>
                ) : null}
              </span>
            </div>
          ))}
        <label>
          Document type
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="blueprint">Blueprint / drawing</option>
            <option value="requirements">Specification / parts list</option>
          </select>
        </label>
        <input
          ref={fileInput}
          type="file"
          accept=".pdf,.txt,.md,.json,.png,.jpg,.jpeg"
          aria-label="Choose source document"
          disabled={!!busy || hasEdits || project.status === "extracting"}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            void onAction("Uploading document…", () =>
              productApi.upload(project.project_id, file, kind),
            );
            e.target.value = "";
          }}
        />
        <button
          className="secondary"
          disabled={
            !!busy ||
            !project.documents.some((document) => document.kind !== "model") ||
            hasEdits ||
            project.status === "extracting"
          }
          onClick={() =>
            void onAction("Starting document extraction…", () =>
              productApi.extract(project.project_id),
            )
          }
        >
          {project.status === "extracting"
            ? "Reading your documents…"
            : "Extract proposed parts"}
        </button>
        {hasEdits ? (
          <p className="pf-footnote">
            Save your part edits before adding documents or extracting again.
          </p>
        ) : null}
        <p className="pf-footnote">
          PDF, text, Markdown, JSON, PNG or JPEG. Extraction can take a moment.
          Your reviewed parts remain editable.
        </p>
      </aside>
      <fieldset
        className="pf-reviewed-parts pf-review-fields"
        disabled={!!busy || project.status === "extracting"}
        aria-busy={!!busy || project.status === "extracting"}
      >
        <legend className="sr-only">Review and confirm product parts</legend>
        {project.status === "extracting" ? (
          <p className="pf-editing-paused" role="status">
            Reading your documents. Part editing will resume when extraction
            finishes.
          </p>
        ) : null}
        <div className="pf-section-heading">
          <div>
            <h2>Review the parts</h2>
            <p>
              Correct names, quantities and requirements. Keep missing details
              unknown.
            </p>
          </div>
          <button
            className="text-button"
            disabled={!!busy}
            onClick={() =>
              setParts([
                ...parts,
                {
                  part_id: `part-${crypto.randomUUID()}`,
                  name: "New part",
                  quantity: 1,
                  node_names: [],
                  status: "proposed",
                  requirements: [],
                },
              ])
            }
          >
            <Plus size={16} /> Add part
          </button>
        </div>
        {!parts.length ? (
          <div className="pf-empty">
            <h3>Your parts will appear here.</h3>
            <p>
              Upload a source and extract its parts, or add the first part
              yourself.
            </p>
          </div>
        ) : (
          parts.map((p, index) => (
            <fieldset className="pf-part-edit" key={p.part_id}>
              <legend>Part {index + 1}</legend>
              <div className="pf-part-fields">
                <label>
                  Part name
                  <input
                    value={p.name}
                    onChange={(e) =>
                      update(index, {
                        name: e.target.value,
                        identity_source: null,
                      })
                    }
                    maxLength={160}
                  />
                </label>
                <label>
                  Quantity
                  <input
                    type="number"
                    min="1"
                    max="1000000"
                    value={p.quantity}
                    onChange={(e) =>
                      update(index, {
                        quantity: Number(e.target.value),
                        quantity_source: null,
                      })
                    }
                  />
                </label>
                <button
                  className="text-button pf-remove"
                  aria-label={`Remove ${p.name}`}
                  onClick={() => setParts(parts.filter((_, i) => i !== index))}
                >
                  <Trash2 size={16} />
                </button>
              </div>
              {p.requirements.map((r, ri) => (
                <div className="pf-requirement" key={`${p.part_id}-${ri}`}>
                  <label>
                    {r.label || r.key}
                    {r.unit ? ` (${r.unit})` : null}
                    <input
                      value={r.value}
                      onChange={(e) =>
                        update(index, {
                          requirements: p.requirements.map((current, i) =>
                            i === ri
                              ? {
                                  ...current,
                                  value: e.target.value,
                                  source: null,
                                  status: "proposed",
                                }
                              : current,
                          ),
                        })
                      }
                    />
                  </label>
                  <details className="pf-requirement-options">
                    <summary>Edit requirement label or unit</summary>
                    <div className="pf-part-fields">
                      <label>
                        Requirement name
                        <input
                          value={r.label}
                          maxLength={160}
                          onChange={(event) =>
                            update(index, {
                              requirements: p.requirements.map((item, i) =>
                                i === ri
                                  ? { ...item, label: event.target.value }
                                  : item,
                              ),
                            })
                          }
                        />
                      </label>
                      <label>
                        Unit
                        <input
                          value={r.unit ?? ""}
                          maxLength={50}
                          onChange={(event) =>
                            update(index, {
                              requirements: p.requirements.map((item, i) =>
                                i === ri
                                  ? {
                                      ...item,
                                      unit: event.target.value || null,
                                      source: null,
                                      status: "proposed",
                                    }
                                  : item,
                              ),
                            })
                          }
                        />
                      </label>
                      <button
                        className="text-button pf-remove"
                        aria-label={`Remove ${r.label}`}
                        onClick={() =>
                          update(index, {
                            requirements: p.requirements.filter(
                              (_, i) => i !== ri,
                            ),
                          })
                        }
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </details>
                  {r.source ? (
                    <details>
                      <summary>
                        Source excerpt
                        {r.source.page ? ` · page ${r.source.page}` : ""}
                      </summary>
                      <blockquote>{r.source.quote}</blockquote>
                      <small>
                        {project.documents.find(
                          (d) => d.document_id === r.source?.document_id,
                        )?.name ?? "Source document"}
                      </small>
                    </details>
                  ) : (
                    <small>Added for review · no document citation</small>
                  )}
                </div>
              ))}
              <button
                className="text-button compact"
                onClick={() =>
                  update(index, {
                    requirements: [
                      ...p.requirements,
                      {
                        key: `requirement_${crypto.randomUUID().replaceAll("-", "")}`,
                        label: `Requirement ${p.requirements.length + 1}`,
                        value: "",
                        status: "proposed",
                      },
                    ],
                  })
                }
              >
                <Plus size={14} /> Add requirement
              </button>
            </fieldset>
          ))
        )}
        <div className="pf-source-confirm">
          <label className="pf-check">
            <input
              type="checkbox"
              checked={reviewed}
              onChange={(e) => setReviewed(e.target.checked)}
            />{" "}
            I have reviewed these parts and their requirements.
          </label>
          {invalidParts ? (
            <p className="pf-footnote">
              Give every part a name, a whole-number quantity and a value for
              each requirement.
            </p>
          ) : null}
          <div className="pf-actions">
            <button
              className="secondary"
              disabled={!!busy || !parts.length || invalidParts}
              onClick={() => save(false)}
            >
              Save changes
            </button>
            <button
              className="primary"
              disabled={!!busy || !reviewed || !parts.length || invalidParts}
              onClick={() => save(true)}
            >
              Confirm parts <ArrowRight size={16} />
            </button>
          </div>
          <p className="pf-footnote">
            Changing reviewed parts invalidates earlier research selections and
            approval.
          </p>
        </div>
      </fieldset>
    </section>
  );
}
function Assembly({
  project,
  busy,
  selected,
  onSelected,
  onAction,
}: {
  project: ProductProject;
  busy: string;
  selected: string[];
  onSelected: (value: string[]) => void;
  onAction: ProjectAction;
}) {
  const [mappings, setMappings] = useState<Record<string, string[]>>(() =>
    Object.fromEntries(project.parts.map((p) => [p.part_id, p.node_names])),
  );
  const [separation, setSeparation] = useState(0),
    [researchMode, setResearchMode] = useState<"demo" | "live">(
      project.demo_id ? "demo" : "live",
    ),
    [reduced, setReduced] = useState(
      () => matchMedia("(prefers-reduced-motion: reduce)").matches,
    );
  useEffect(() => {
    const q = matchMedia("(prefers-reduced-motion: reduce)"),
      change = () => setReduced(q.matches);
    q.addEventListener("change", change);
    return () => q.removeEventListener("change", change);
  }, []);
  const toggle = (id: string) =>
    onSelected(
      selected.includes(id)
        ? selected.filter((p) => p !== id)
        : [...selected, id],
    );
  const confirmed =
    project.parts.length > 0 &&
    project.parts.every((p) => p.status === "confirmed");
  const hasModel = Boolean(project.model.asset_url);
  return (
    <section className="pf-assembly">
      <div className="pf-assembly-view">
        <div className="pf-section-heading">
          <div>
            <h2>Explore the assembly</h2>
            <p>
              {project.model.mapping_status === "unmapped" &&
              project.model.origin === "uploaded"
                ? "Connect model groups to parts in Model options, or select from the list."
                : "Select a part in the model or use the list."}
            </p>
          </div>
          {hasModel ? (
            <span className="pf-model-origin">
              {project.model.origin === "prepared_demo"
                ? "Prepared demo model"
                : project.model.origin === "uploaded"
                  ? "Uploaded model"
                  : "Generated model"}
            </span>
          ) : null}
        </div>
        {hasModel ? (
          <Suspense
            fallback={
              <div className="pf-model-canvas pf-loading">Opening 3D view…</div>
            }
          >
            <AssemblyScene
              model={project.model}
              parts={project.parts}
              selected={selected}
              separation={separation}
              reduced={reduced}
              onSelect={toggle}
            />
          </Suspense>
        ) : (
          <div className="pf-model-empty">
            <h3>
              {project.demo_id
                ? "Use the prepared assembly."
                : "Add a 3D model when you have one."}
            </h3>
            <p>
              {project.model.notes ||
                "Automatic blueprint-to-3D generation is not connected. Your reviewed parts can still be researched."}
            </p>
            {project.demo_id ? (
              <button
                className="secondary"
                disabled={!!busy}
                onClick={() =>
                  void onAction("Loading prepared model…", () =>
                    productApi.model(project.project_id, "prepared_demo"),
                  )
                }
              >
                Use prepared demo model
              </button>
            ) : null}
          </div>
        )}
        {hasModel ? (
          <div className="pf-model-controls">
            <button onClick={() => setSeparation(0)}>Assemble</button>
            <input
              aria-label="Assembly separation"
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={separation}
              onChange={(e) => setSeparation(Number(e.target.value))}
            />
            <button onClick={() => setSeparation(1)}>Explode</button>
          </div>
        ) : null}
        <p className="pf-footnote">
          Geometry is visual context. Your reviewed documents establish
          dimensions, materials and tolerances.
          {sourceUrl(project.model.source_url) ? (
            <a
              href={sourceUrl(project.model.source_url)}
              target="_blank"
              rel="noreferrer"
            >
              {" "}
              Model source <ExternalLink size={12} />
            </a>
          ) : null}
        </p>
        <details className="pf-model-options">
          <summary>Model options & provenance</summary>
          <p>{project.model.notes || "No model attribution supplied."}</p>
          {project.model.license ? (
            <p>License: {project.model.license}</p>
          ) : null}
          <p>
            Generated models will appear here when a generation service is
            configured. Prepared demo assets are labelled separately.
          </p>
          <label>
            Upload a GLB model
            <input
              type="file"
              accept=".glb"
              disabled={!!busy}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file)
                  void onAction("Uploading 3D model…", async () => {
                    const next = await productApi.upload(
                      project.project_id,
                      file,
                      "model",
                    );
                    const document = next.documents.findLast(
                      (d) => d.kind === "model",
                    );
                    return productApi.model(
                      project.project_id,
                      "uploaded",
                      document?.document_id,
                    );
                  });
                e.target.value = "";
              }}
            />
          </label>
          {project.model.origin === "uploaded" &&
          project.model.node_names.length ? (
            <div className="pf-node-mapping">
              <h3>Connect model groups to parts</h3>
              <p>
                Match named groups in your GLB to the reviewed parts. Unmapped
                parts remain selectable in the list.
              </p>
              {project.parts.map((part) => (
                <label key={part.part_id}>
                  {part.name}
                  <select
                    multiple
                    size={Math.min(5, project.model.node_names.length)}
                    value={mappings[part.part_id] ?? []}
                    onChange={(e) =>
                      setMappings({
                        ...mappings,
                        [part.part_id]: Array.from(
                          e.target.selectedOptions,
                          (option) => option.value,
                        ),
                      })
                    }
                  >
                    {project.model.node_names.map((name) => (
                      <option value={name} key={name}>
                        {name}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              <button
                className="secondary"
                disabled={!!busy}
                onClick={() =>
                  void onAction("Saving model mapping…", () =>
                    productApi.parts(
                      project.project_id,
                      project.parts.map((part) => ({
                        ...part,
                        node_names: mappings[part.part_id] ?? [],
                      })),
                      confirmed,
                      project.version,
                    ),
                  )
                }
              >
                Save model mapping
              </button>
            </div>
          ) : null}
        </details>
      </div>
      <aside className="pf-parts">
        <div className="pf-section-heading">
          <h2>Parts</h2>
          <button
            className="text-button"
            onClick={() =>
              onSelected(
                selected.length === project.parts.length
                  ? []
                  : project.parts.map((p) => p.part_id),
              )
            }
          >
            {selected.length === project.parts.length ? "Clear" : "Select all"}
          </button>
        </div>
        {project.parts.map((p) => (
          <button
            className="pf-part-choice"
            key={p.part_id}
            aria-pressed={selected.includes(p.part_id)}
            onClick={() => toggle(p.part_id)}
          >
            <span className="pf-part-check">
              {selected.includes(p.part_id) ? <Check size={13} /> : null}
            </span>
            <span>
              {p.name}
              <small>
                Quantity {p.quantity} · {p.requirements.length} requirements
              </small>
            </span>
          </button>
        ))}
        <div className="pf-research-start">
          <strong>
            {selected.length} {selected.length === 1 ? "part" : "parts"}{" "}
            selected
          </strong>
          <p>
            Investigate selected parts in parallel. Each search keeps its own
            sources and status.
          </p>
          <label>
            Supplier information
            <select
              value={researchMode}
              onChange={(e) =>
                setResearchMode(e.target.value as "demo" | "live")
              }
              disabled={!!busy || pending(project)}
            >
              {project.demo_id ? (
                <option value="demo">Demo suppliers</option>
              ) : null}
              <option value="live">Search real suppliers</option>
            </select>
          </label>
          <p>
            {researchMode === "demo"
              ? "Use labelled sample quotes to explore the workflow."
              : "Search public supplier sources. Prices and conformance still need confirmation."}
          </p>
          <button
            className="primary"
            disabled={
              !!busy || !selected.length || !confirmed || pending(project)
            }
            onClick={() =>
              void onAction(
                "Starting part investigations…",
                () =>
                  productApi.investigate(
                    project.project_id,
                    selected,
                    researchMode,
                  ),
                "research",
              )
            }
          >
            Research selected parts <ArrowRight size={16} />
          </button>
          {!confirmed ? (
            <p>Review and confirm your parts above first.</p>
          ) : null}
          {pending(project) ? (
            <p>
              Research is running below. You can review each result as it
              arrives.
            </p>
          ) : null}
        </div>
      </aside>
    </section>
  );
}
function Approval({
  project,
  busy,
  onAction,
}: {
  project: ProductProject;
  busy: string;
  onAction: ProjectAction;
}) {
  const [ack, setAck] = useState(false);
  const packet = project.package;
  useEffect(() => setAck(false), [packet?.package_id, packet?.input_version]);
  const content = packet
    ? `${project.name} — sourcing package\n\n${packet.notice}\n\n${packet.items.map((item) => `${item.part_name} · ${item.quantity} ${item.quantity === 1 ? "unit" : "units"}\n${item.supplier_name}${item.data_origin === "synthetic_demo" ? " (sample quote)" : ""}\n\n${item.rfq_text}\n\nEvidence gaps:\n${item.evidence_gaps.map((g) => `- ${g}`).join("\n")}`).join("\n\n---\n\n")}`
    : "";
  const download = () => {
    if (!packet) return;
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${project.name.replace(/[^a-z0-9-]/gi, "-")}-rfq.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };
  return (
    <section className="pf-approval">
      <div className="pf-section-heading">
        <div>
          <h2>Review your sourcing package</h2>
          <p>
            Check the selected suppliers, evidence gaps and request before
            approving.
          </p>
        </div>
        {packet ? (
          <button className="secondary" onClick={download}>
            Download RFQ
          </button>
        ) : null}
      </div>
      {!packet ? (
        <div className="pf-empty">
          <h3>
            {Object.keys(project.selections).length
              ? "Your supplier choices are ready."
              : "Choose suppliers first."}
          </h3>
          <p>
            Choose suppliers in the research results above, then prepare the
            package for review.
          </p>
          <button
            className="primary"
            disabled={!!busy || !Object.keys(project.selections).length}
            onClick={() =>
              void onAction("Preparing review package…", () =>
                productApi.package(project.project_id),
              )
            }
          >
            Prepare sourcing package <ArrowRight size={16} />
          </button>
        </div>
      ) : (
        <>
          <p className="pf-package-status">
            {packet.status.replaceAll("_", " ")} · reviewable RFQ
          </p>
          {packet.status === "draft" ? (
            <pre className="pf-rfq">{content}</pre>
          ) : (
            <details className="pf-reviewed-package">
              <summary>Read the approved sourcing package</summary>
              <pre className="pf-rfq">{content}</pre>
            </details>
          )}
          <p>
            Supplier leads are not verified offers. Confirm specifications,
            price, availability and certification directly before procurement.
          </p>
          {!packet.approved_at &&
          packet.status !== "approved" &&
          packet.status !== "simulated" ? (
            <>
              <label className="pf-check">
                <input
                  type="checkbox"
                  checked={ack}
                  onChange={(e) => setAck(e.target.checked)}
                />{" "}
                I reviewed the package and understand the unresolved evidence
                and sample information.
              </label>
              <button
                className="primary"
                disabled={!!busy || !ack}
                onClick={() =>
                  void onAction(
                    "Recording your approval…",
                    () =>
                      productApi.approve(project.project_id, packet.package_id),
                    "approval",
                  )
                }
              >
                Approve reviewed package
              </button>
            </>
          ) : null}
          {packet.status === "approved" ? (
            <div className="pf-simulation" tabIndex={-1}>
              <h3>Approval recorded.</h3>
              <p>
                Finish the demonstration with a simulated receipt. This does not
                send an email, place an order or contact a supplier.
              </p>
              <button
                className="secondary"
                disabled={!!busy}
                onClick={() =>
                  void onAction(
                    "Creating simulated receipt…",
                    () =>
                      productApi.simulate(
                        project.project_id,
                        packet.package_id,
                      ),
                    "approval",
                  )
                }
              >
                Create simulated receipt
              </button>
            </div>
          ) : null}
          {packet.receipt || packet.status === "simulated" ? (
            <div className="pf-simulation" tabIndex={-1} role="status">
              <h3>Simulated receipt</h3>
              <p>
                The demo is complete. No supplier was contacted and no order was
                placed.
              </p>
              {packet.receipt ? (
                <pre>{JSON.stringify(packet.receipt, null, 2)}</pre>
              ) : null}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
