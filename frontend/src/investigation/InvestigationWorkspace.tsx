import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { ArrowRight, Check, Search } from "lucide-react";
import { api, type Command } from "../api/client.ts";
import type { EngineView, Schema } from "../api/types.ts";
import {
  EvidenceDialog,
  EvidenceLink,
  ErrorNotice,
  Loading,
  Status,
  human,
} from "../components/Primitives.tsx";
import { Activity } from "../components/Research.tsx";
import { useBatch } from "./useBatch.ts";
import { knownLocation, supplierFindings } from "./findings.ts";
const ResearchGlobe = lazy(() => import("./ResearchGlobe.tsx"));
export function InvestigationWorkspace({
  engine,
  onPart,
  connectionError,
  onReconnect,
}: {
  engine: EngineView | null;
  onPart: (id: string) => void;
  connectionError?: string;
  onReconnect?: () => void;
}) {
  const [id, setId] = useState(() =>
    location.hash.startsWith("#batch/")
      ? decodeURIComponent(location.hash.slice(7))
      : "",
  );
  const [selected, setSelected] = useState<string[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const command = useRef<Command<Schema<"BatchInvestigation">> | null>(null),
    locked = useRef(false);
  useEffect(() => {
    setSelected([]);
    command.current = null;
  }, [engine?.scenario_run_id]);
  const start = async (retry = false) => {
    if (!engine || locked.current) return;
    locked.current = true;
    setBusy(true);
    setError("");
    try {
      if (!retry || !command.current)
        command.current = api.startBatch({
          assembly_id: "engine-demo-001",
          component_ids: selected,
          mode: engine.mode,
        });
      const b = await command.current.execute();
      command.current = null;
      setId(b.batch_id);
      history.replaceState(
        history.state,
        "",
        `#batch/${encodeURIComponent(b.batch_id)}`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start research.");
    } finally {
      locked.current = false;
      setBusy(false);
    }
  };
  if (id)
    return (
      <BatchView
        key={id}
        id={id}
        engine={engine}
        onPart={onPart}
        onBack={() => {
          setId("");
          history.replaceState(history.state, "", "#investigations");
        }}
      />
    );
  return (
    <main className="batch-start">
      <div>
        <h1>
          Choose the parts.
          <br />
          Follow the evidence.
        </h1>
        <p>
          Select one or several components to investigate concurrently. Each
          keeps its own sources, checks and decision.
        </p>
      </div>
      <section className="batch-start-form">
        <h2>Engine demo components</h2>
        <p>
          The engine is the enabled research profile. Other prepared assemblies
          need reviewed requirements and isolated supplier rules.
        </p>
        {!engine ? (
          connectionError ? (
            <ErrorNotice retry={onReconnect}>{connectionError}</ErrorNotice>
          ) : (
            <Loading>Connecting to the current run…</Loading>
          )
        ) : (
          <>
            <div className="batch-part-options">
              {engine.components.map((c) => (
                <button
                  key={c.component_id}
                  aria-pressed={selected.includes(c.component_id)}
                  disabled={busy}
                  onClick={() => {
                    command.current = null;
                    setSelected((s) =>
                      s.includes(c.component_id)
                        ? s.filter((i) => i !== c.component_id)
                        : [...s, c.component_id],
                    );
                  }}
                >
                  <span className="part-checkbox">
                    {selected.includes(c.component_id) && <Check size={12} />}
                  </span>
                  <span>
                    {c.display_name}
                    <small>{c.part_identity}</small>
                  </span>
                </button>
              ))}
            </div>
            <button
              className="primary"
              disabled={busy || !selected.length}
              onClick={() => void start(command.current !== null)}
            >
              <Search size={16} />
              {busy
                ? "Starting research…"
                : `Investigate ${selected.length || ""} ${selected.length === 1 ? "part" : "parts"}`}
              <ArrowRight size={16} />
            </button>
            <p className="small">
              {engine.mode} mode · offers and reliability metrics are synthetic
              demo data. Public leads do not establish eligibility.
            </p>
          </>
        )}
        {error && (
          <ErrorNotice retry={() => void start(true)}>{error}</ErrorNotice>
        )}
      </section>
    </main>
  );
}
function BatchView({
  id,
  engine,
  onPart,
  onBack,
}: {
  id: string;
  engine: EngineView | null;
  onPart: (id: string) => void;
  onBack: () => void;
}) {
  const { batch, events, changedCases, connections, error, refresh } =
    useBatch(id);
  const [filter, setFilter] = useState("all"),
    [selected, setSelected] = useState<string | null>(null),
    [evidence, setEvidence] = useState<string | null>(null);
  const findings = supplierFindings(events).filter(
    (f) => filter === "all" || f.component_id === filter,
  );
  const focused = findings.find((f) => f.event_id === selected);
  const name = (cid: string) =>
    engine?.components.find((c) => c.component_id === cid)?.display_name ?? cid;
  const connected =
    Object.values(connections).length > 0 &&
    Object.values(connections).every((s) => s === "connected");
  return (
    <main className="batch-workspace">
      <div className="batch-title">
        <div>
          <button className="text-button" onClick={onBack}>
            ← Choose parts
          </button>
          <h1>
            {batch
              ? `Investigating ${batch.components.length} components`
              : "Component investigation"}
          </h1>
          <p>
            {batch
              ? `${batch.components.length} components · ${batch.mode} mode · independent research`
              : error
                ? "This investigation is unavailable."
                : "Opening investigation…"}
          </p>
        </div>
        <span className={`stream-state ${connected ? "connected" : ""}`}>
          {connected
            ? "Live event connections"
            : error
              ? "Connection unavailable"
              : "Connecting / replaying"}
        </span>
      </div>
      {error && <ErrorNotice retry={() => void refresh()}>{error}</ErrorNotice>}
      {!batch ? (
        error ? null : (
          <Loading>Loading investigation…</Loading>
        )
      ) : (
        <>
          <div className="batch-filters">
            <button
              aria-pressed={filter === "all"}
              onClick={() => {
                setFilter("all");
                setSelected(null);
              }}
            >
              All parts
            </button>
            {batch.components.map((c) => (
              <button
                key={c.component_id}
                aria-pressed={filter === c.component_id}
                onClick={() => {
                  setFilter(c.component_id);
                  setSelected(null);
                }}
              >
                {name(c.component_id)}
              </button>
            ))}
          </div>
          <div className="batch-research-top">
            <Suspense fallback={<Loading>Loading research globe…</Loading>}>
              <ResearchGlobe
                findings={findings}
                selected={selected}
                onSelect={setSelected}
              />
            </Suspense>
            <Activity
              eventLabel={(event) =>
                name(
                  batch.components.find((c) => c.case_id === event.case_id)
                    ?.component_id ?? event.case_id,
                )
              }
              events={events.filter(
                (e) =>
                  filter === "all" ||
                  batch.components.some(
                    (c) => c.component_id === filter && c.case_id === e.case_id,
                  ),
              )}
              connection={connected ? "connected" : "reconnecting"}
              onEvidence={setEvidence}
            />
          </div>
          <section className="batch-tasks">
            <div className="section-heading">
              <h2>Component research</h2>
              <span>Recorded task states · no estimated percentage</span>
            </div>
            <div className="batch-task-grid">
              {batch.components
                .filter((c) => filter === "all" || filter === c.component_id)
                .map((c) => (
                  <article key={c.component_id}>
                    <header>
                      <h3>{name(c.component_id)}</h3>
                      <Status value={c.generation_status ?? c.status} />
                    </header>
                    {changedCases.includes(c.case_id) && (
                      <p className="scope-note">
                        New activity exists outside this batch. Open the
                        component to inspect its current decision; the tasks and
                        evidence here remain from this batch.
                      </p>
                    )}
                    {!c.tasks.length ? (
                      <p>
                        {c.status === "duplicate"
                          ? "This part already has a decision. No new research was started; open the component to review it."
                          : "Accepted. Waiting for the first recorded task."}
                      </p>
                    ) : (
                      <ul>
                        {c.tasks.map((t) => (
                          <li key={t.task_id}>
                            <div>
                              <strong>{t.name}</strong>
                              <Status value={t.status} />
                            </div>
                            {t.summary && <p>{t.summary}</p>}
                            {t.latest_tool && (
                              <p className="task-tool">
                                {human(t.latest_tool.name)} ·{" "}
                                {t.latest_tool.status}
                                <br />
                                {t.latest_tool.summary}
                              </p>
                            )}
                            {t.evidence_refs?.length > 0 && (
                              <details>
                                <summary>
                                  {t.evidence_refs.length} evidence references
                                </summary>
                                <div className="citations">
                                  {t.evidence_refs.map((ref) => (
                                    <EvidenceLink
                                      key={ref}
                                      id={ref}
                                      onOpen={setEvidence}
                                    />
                                  ))}
                                </div>
                              </details>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                    <button
                      className="secondary"
                      disabled={engine?.scenario_run_id !== batch.run_id}
                      onClick={() => onPart(c.component_id)}
                    >
                      Review options & decision <ArrowRight size={14} />
                    </button>
                    {engine?.scenario_run_id !== batch.run_id && (
                      <p>
                        Historical run: current-run actions are unavailable.
                      </p>
                    )}
                  </article>
                ))}
            </div>
          </section>
          <section className="batch-findings">
            <div className="section-heading">
              <h2>Supplier findings</h2>
              <span>
                {findings.length} candidates ·{" "}
                {findings.filter((f) => !knownLocation(f)).length} unknown
                locations
              </span>
            </div>
            <p>
              Discovery is not eligibility. Candidate documents below are
              evidence for supplier checks, not proof of coordinates.
            </p>
            {!findings.length ? (
              <div className="empty-state">
                Supplier findings appear when a tool publishes them.
              </div>
            ) : (
              <div className="finding-layout">
                <div className="finding-list">
                  {findings.map((f) => (
                    <button
                      key={f.event_id}
                      aria-pressed={selected === f.event_id}
                      onClick={() => setSelected(f.event_id)}
                    >
                      <strong>{f.supplier_id}</strong>
                      <span>
                        {name(f.component_id)} · {f.route}
                      </span>
                      <small>
                        {f.location.country ?? "Country unknown"} ·{" "}
                        {knownLocation(f)
                          ? `${f.location.precision ?? "unspecified precision"} location`
                          : "Location unknown"}
                      </small>
                    </button>
                  ))}
                </div>
                <aside>
                  {focused ? (
                    <>
                      <h3>{focused.supplier_id}</h3>
                      <p>
                        {focused.candidate_id} · {focused.route}
                      </p>
                      <dl>
                        <dt>Location source</dt>
                        <dd>{focused.location.source ?? "Unknown"}</dd>
                        <dt>Precision / confidence</dt>
                        <dd>
                          {focused.location.precision ?? "Unknown"} /{" "}
                          {focused.location.confidence ?? "Unknown"}
                        </dd>
                        <dt>Data origin</dt>
                        <dd>{human(focused.location.data_origin)}</dd>
                      </dl>
                      <div className="citations">
                        {focused.evidence_refs.map((ref) => (
                          <EvidenceLink
                            key={ref}
                            id={ref}
                            onOpen={setEvidence}
                          />
                        ))}
                      </div>
                    </>
                  ) : (
                    <p>
                      Select a finding to inspect its source and candidate
                      evidence.
                    </p>
                  )}
                </aside>
              </div>
            )}
          </section>
        </>
      )}
      {evidence && (
        <EvidenceDialog id={evidence} onClose={() => setEvidence(null)} />
      )}
    </main>
  );
}
