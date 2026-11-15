import { useEffect, useRef, useState } from "react";
import { ArrowRight, Download, X } from "lucide-react";
import { api, type Command } from "../api/client.ts";
import { watchEvents } from "../api/events.ts";
import type { Schema } from "../api/types.ts";
import { ErrorNotice } from "../components/Primitives.tsx";
import {
  DEMO_BLUEPRINT,
  DEMO_REQUIREMENTS,
  sampleFile,
  saveDemoIntake,
  type DemoScreen,
  type DemoSession,
} from "./session.ts";
import "./demo.css";

const screens = [
  ["sources", "Sources & review"],
  ["assembly", "Assembly"],
  ["investigations", "Part investigation"],
  ["suppliers", "Comparison & evidence"],
  ["documents", "Approval pack"],
] as const;

export function DemoGuide({
  session,
  screen,
  onSession,
  onBusyChange,
  onSourcesLoaded,
  onNavigate,
  onExit,
}: {
  session: DemoSession;
  screen: DemoScreen;
  onSession: (value: DemoSession) => void;
  onBusyChange: (value: boolean) => void;
  onSourcesLoaded: () => void;
  onNavigate: (screen: DemoScreen) => void;
  onExit: () => void;
}) {
  const [draft, setDraft] = useState<Schema<"PartRequirementDraft"> | null>(
    null,
  );
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [expanded, setExpanded] = useState(true);
  const locked = useRef(false),
    current = useRef(session),
    alive = useRef(true);
  const extraction = useRef<Command<Schema<"PartRequirementDraft">> | null>(
    null,
  );
  const uploadAbort = useRef<AbortController | null>(null);
  current.current = session;
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      uploadAbort.current?.abort();
      onBusyChange(false);
    };
  }, []);
  useEffect(() => {
    const abort = new AbortController();
    const refresh = async () => {
      try {
        let value = current.current;
        // Also follow files uploaded with the normal form rather than the shortcut.
        const saved: Partial<DemoSession> = JSON.parse(
          sessionStorage.getItem(`resource:intake:v1:${session.runId}`) ?? "{}",
        );
        if (
          !value.draftId &&
          typeof saved.draftId === "string" &&
          typeof saved.componentId === "string"
        ) {
          value = { ...value, ...saved };
          current.current = value;
          if (!abort.signal.aborted) onSession(value);
        }
        if (!value.draftId) {
          setDraft(null);
          return;
        }
        const result = await api.requirementDraft(value.draftId, abort.signal);
        if (!abort.signal.aborted) {
          setDraft(result);
          setError("");
        }
      } catch (e) {
        if (!abort.signal.aborted)
          setError(
            e instanceof Error ? e.message : "Could not check source review.",
          );
      }
    };
    void refresh();
    const stop = watchEvents({
      caseId: "__run__",
      runId: session.runId,
      streamPath: `/api/v1/scenario-runs/${encodeURIComponent(session.runId)}/events`,
      onConnection: () => {},
      onSnapshotRequired: () => void refresh(),
      onEvent: (event) => {
        if (event.type.startsWith("intake.")) void refresh();
      },
    });
    return () => {
      abort.abort();
      stop();
    };
  }, [session.runId, session.draftId]);

  const uploadSamples = async () => {
    if (locked.current) return;
    locked.current = true;
    const abort = new AbortController();
    uploadAbort.current = abort;
    setBusy(true);
    onBusyChange(true);
    setError("");
    const save = (patch: Partial<DemoSession>) => {
      const next = { ...current.current, ...patch };
      // Persist the normal intake record before navigating or reporting success.
      saveDemoIntake(next);
      current.current = next;
      if (alive.current) onSession(next);
      return next;
    };
    try {
      let value = current.current;
      if (!value.blueprintId) {
        const uploaded = await api
          .upload(sampleFile("blueprint"), "blueprint")
          .execute(abort.signal);
        value = save({ blueprintId: uploaded.upload_id });
      }
      if (!value.requirementsId) {
        const uploaded = await api
          .upload(
            sampleFile("requirements"),
            "part_requirements",
            value.componentId,
          )
          .execute(abort.signal);
        value = save({ requirementsId: uploaded.upload_id });
      }
      if (!value.draftId) {
        extraction.current ??= api.extractRequirements(
          value.requirementsId!,
          value.componentId,
        );
        const result = await extraction.current.execute(abort.signal);
        save({ draftId: result.draft_id });
      }
      if (alive.current) onSourcesLoaded();
    } catch (e) {
      if (alive.current)
        setError(
          e instanceof Error
            ? e.message
            : "Could not upload the sample sources.",
        );
    } finally {
      locked.current = false;
      onBusyChange(false);
      if (alive.current) setBusy(false);
    }
  };
  const confirmed = draft?.status === "confirmed";
  return (
    <aside
      className="demo-guide"
      aria-label="Prepared demo guide"
      aria-busy={busy}
    >
      <div className="demo-guide-heading">
        <div>
          <strong>Prepared engine demo</strong>
          <span>Sample data · simulated orders</span>
        </div>
        <div className="inline">
          <button
            className="text-button compact"
            aria-expanded={expanded}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "Hide guide" : "Show guide"}
          </button>
          <button
            className="icon-button"
            aria-label="Exit demo guide"
            disabled={busy}
            onClick={onExit}
          >
            <X size={16} />
          </button>
        </div>
      </div>
      {expanded && (
        <>
          <ol aria-label="Demo screens">
            {screens.map(([id, label], index) => (
              <li key={id}>
                <button
                  aria-current={screen === id ? "step" : undefined}
                  disabled={
                    busy ||
                    (id === "assembly" || id === "investigations"
                      ? !confirmed
                      : id === "suppliers" || id === "documents"
                        ? !session.partId
                        : false)
                  }
                  onClick={() => onNavigate(id)}
                >
                  <span>{index + 1}</span>
                  {label}
                </button>
              </li>
            ))}
          </ol>
          <div className="demo-guide-content">
            {screen === "sources" ? (
              <>
                {!session.draftId ? (
                  <>
                    <p>
                      Use the sample blueprint and fuel-nozzle specification in
                      the upload screen below, or upload them together here.
                      Then inspect the cited fields, save any corrections and
                      confirm them yourself.
                    </p>
                    <div className="demo-guide-actions">
                      <button
                        className="primary compact"
                        disabled={busy}
                        onClick={() => void uploadSamples()}
                      >
                        {busy
                          ? "Uploading & requesting extraction…"
                          : "Upload & extract sample sources"}
                        <ArrowRight size={15} />
                      </button>
                      <SampleDownload kind="blueprint" />
                      <SampleDownload kind="requirements" />
                    </div>
                  </>
                ) : confirmed ? (
                  <>
                    <p>
                      Requirements are confirmed by the intake service. The
                      assembly is a prepared visual asset. “Generate assembly”
                      below exposes the real missing-provider state; it does not
                      produce new geometry.
                    </p>
                    <button
                      className="secondary compact"
                      onClick={() => onNavigate("assembly")}
                    >
                      Explore the prepared assembly
                      <ArrowRight size={15} />
                    </button>
                  </>
                ) : (
                  <p>
                    Review the extracted fields against the original source
                    below. Save corrections first, then use{" "}
                    <strong>Confirm requirements</strong>. The guide waits for
                    the server’s confirmed draft.
                  </p>
                )}
              </>
            ) : screen === "assembly" ? (
              <>
                <p>
                  Explode and reassemble the real model, then select a
                  component. To test concurrent research, continue to the
                  existing part selector and choose one or several components.
                </p>
                <button
                  className="secondary compact"
                  disabled={!confirmed}
                  onClick={() => onNavigate("investigations")}
                >
                  Choose parts for investigation
                  <ArrowRight size={15} />
                </button>
              </>
            ) : screen === "investigations" ? (
              <p>
                Select parts and start the investigation. Tasks, findings and
                map connections follow backend events. Open a source citation,
                then use <strong>Review options & decision</strong> on a
                component to compare its results.
              </p>
            ) : screen === "suppliers" ? (
              <p>
                Review candidates and their checks. Open a citation to inspect
                the evidence, then select an eligible option to prepare the
                existing approval pack. Selection still uses the current server
                decision and evidence.
              </p>
            ) : (
              <p>
                Review and edit the versioned pack. Approval is your action;
                editing a field invalidates it. Submission stays explicitly
                simulated and requires an approved current package.
              </p>
            )}
          </div>
          <details className="demo-scope">
            <summary>What this demo processes</summary>
            <p>
              Offers, supplier evidence, prices and reliability metrics are
              examples. Configured OpenAI, Databricks and Linkup integrations
              may still make actual processing calls with demo data. Extraction
              reports its source; validation and ranking use deterministic
              rules.
            </p>
            <p>
              Only uploaded part identity and revision currently enter automatic
              checks. Uploaded dimensions, material, tolerances and
              certifications require manual evidence review. The prepared model
              is illustrative; generic-product research and arbitrary
              blueprint-to-3D generation remain unavailable.
            </p>
            <p className="small muted">Run {session.runId}</p>
          </details>
          {error && <ErrorNotice>{error}</ErrorNotice>}
        </>
      )}
    </aside>
  );
}

function SampleDownload({ kind }: { kind: "blueprint" | "requirements" }) {
  const file = sampleFile(kind);
  const text = kind === "blueprint" ? DEMO_BLUEPRINT : DEMO_REQUIREMENTS;
  return (
    <a
      className="text-button compact"
      download={file.name}
      href={`data:text/plain;charset=utf-8,${encodeURIComponent(text)}`}
    >
      <Download size={14} />
      Sample {kind === "blueprint" ? "blueprint" : "specification"}
    </a>
  );
}
