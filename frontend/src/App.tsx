import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { animate, onScroll } from "animejs";
import {
  ArrowRight,
  ArrowUpRight,
  Box,
  ChevronLeft,
  Crosshair,
  FileText,
  GitCompareArrows,
  Layers3,
  RotateCcw,
  Search,
  Settings2,
} from "lucide-react";
import { staleReasonText } from "./api/guards.ts";
import { api, type Command } from "./api/client.ts";
import { useCase, useCommand } from "./api/useCase.ts";
import type { ComponentInstance, EngineView, Schema } from "./api/types.ts";
import {
  Badge,
  Empty,
  ErrorNotice,
  EvidenceDialog,
  Loading,
  Status,
  human,
} from "./components/Primitives.tsx";
import { ProductHome } from "./product/ProductHome.tsx";
import { Intake } from "./components/Intake.tsx";
import { Activity, Research } from "./components/Research.tsx";
import { Documents } from "./components/Documents.tsx";
import { DemoGuide } from "./demo/DemoGuide.tsx";
import {
  readDemoSession,
  saveDemoSession,
  type DemoScreen,
  type DemoSession,
} from "./demo/session.ts";
const InvestigationWorkspace = lazy(() =>
  import("./investigation/InvestigationWorkspace.tsx").then((m) => ({
    default: m.InvestigationWorkspace,
  })),
);
const EngineScene = lazy(() => import("./scene/EngineScene.tsx"));
type Tab = "assembly" | "suppliers" | "documents";
const shortName = (c: ComponentInstance) =>
  c.part_identity === "RS-FN-1001"
    ? "Fuel nozzle"
    : c.part_identity === "RS-NGV-2040"
      ? "NGV segment"
      : c.part_identity === "RS-BD-3110"
        ? "Bleed duct"
        : c.display_name;

export default function App() {
  const [demo, setDemo] = useState(readDemoSession);
  const [demoSourceBusy, setDemoSourceBusy] = useState(false),
    [demoStartFailed, setDemoStartFailed] = useState(false);
  const [workspaceTab, setWorkspaceTab] = useState<Tab>(() =>
    location.hash === "#demo/suppliers"
      ? "suppliers"
      : location.hash === "#demo/documents"
        ? "documents"
        : "assembly",
  );
  const [engine, setEngine] = useState<EngineView | null>(null),
    [error, setError] = useState(""),
    [entered, setEntered] = useState(
      () => Boolean(readDemoSession()) && location.hash.startsWith("#demo/"),
    );
  const [intro, setIntro] = useState(
      () =>
        location.hash !== "#sources" &&
        !(readDemoSession() && location.hash.startsWith("#demo/")),
    ),
    [initialPart, setInitialPart] = useState<string | null>(
      () => readDemoSession()?.partId ?? null,
    );
  const [intakeVersion, setIntakeVersion] = useState(0);
  const [investigating, setInvestigating] = useState(
    () =>
      location.hash === "#investigations" ||
      location.hash.startsWith("#batch/"),
  );
  const [homeVersion, setHomeVersion] = useState(0);
  const openSources = () => {
    setInvestigating(false);
    history.replaceState(null, "", "#sources");
    setIntro(false);
    setEntered(false);
    window.scrollTo(0, 0);
  };
  const [mode, setMode] = useState<Schema<"Mode">>("seeded"),
    [runBusy, setRunBusy] = useState(false),
    [settings, setSettings] = useState(false);
  const updateDemo = (value: DemoSession | null) => {
    saveDemoSession(value);
    setDemo(value);
  };
  const changeWorkspaceTab = (value: Tab) => {
    setWorkspaceTab(value);
    if (demo) history.replaceState(null, "", `#demo/${value}`);
  };
  const openDemoScreen = (screen: DemoScreen) => {
    if (screen === "sources") {
      openSources();
      return;
    }
    if (screen === "investigations") {
      setInvestigating(true);
      history.replaceState(null, "", "#investigations");
    } else {
      setInvestigating(false);
      setIntro(false);
      setEntered(true);
      changeWorkspaceTab(screen);
    }
    window.scrollTo(0, 0);
  };
  const startingDemo = useRef(false),
    initialConnection = useRef<Promise<EngineView> | null>(null),
    demoRunCommand = useRef<Command<Schema<"ScenarioRunView">> | null>(null);
  const refresh = async () => {
    try {
      const value = await api.engine();
      setEngine(value);
      setMode(value.mode);
      setError("");
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Unable to connect to the recovery service.",
      );
    }
  };
  useEffect(() => {
    // Establish the anonymous visitor session before creating an isolated demo.
    initialConnection.current = api.engine();
    void initialConnection.current
      .then((value) => {
        setEngine(value);
        setMode(value.mode);
        setError("");
      })
      .catch((e: unknown) =>
        setError(
          e instanceof Error
            ? e.message
            : "Unable to connect to the recovery service.",
        ),
      );
  }, []);
  useEffect(() => {
    if (engine && demo && engine.scenario_run_id !== demo.runId) {
      updateDemo(null);
      setInitialPart(null);
      if (location.hash.startsWith("#demo/")) openSources();
    }
  }, [engine?.scenario_run_id, demo?.runId]);
  const startDemo = async () => {
    if (startingDemo.current || demoSourceBusy) return;
    startingDemo.current = true;
    setRunBusy(true);
    setDemoStartFailed(false);
    setSettings(false);
    updateDemo(null);
    openSources();
    try {
      if (!engine) {
        try {
          await initialConnection.current;
        } catch {
          initialConnection.current = api.engine();
          await initialConnection.current;
        }
      }
      demoRunCommand.current ??= api.newRun("seeded");
      const run = await demoRunCommand.current.execute();
      const value = await api.engine(run.scenario_run_id);
      const component = value.components.find(
        (c) => c.part_identity === "RS-FN-1001",
      );
      if (!component)
        throw new Error(
          "The prepared engine profile is unavailable on this server.",
        );
      setEngine(value);
      setMode(value.mode);
      setError("");
      setInitialPart(null);
      setWorkspaceTab("assembly");
      updateDemo({
        runId: value.scenario_run_id,
        componentId: component.component_id,
      });
      setIntakeVersion((version) => version + 1);
      demoRunCommand.current = null;
    } catch (e) {
      setDemoStartFailed(true);
      setError(
        e instanceof Error ? e.message : "Could not start the prepared demo.",
      );
    } finally {
      startingDemo.current = false;
      setRunBusy(false);
    }
  };
  const newRun = async () => {
    setRunBusy(true);
    try {
      await api
        .newRun(mode, mode === "replay" ? engine?.scenario_run_id : undefined)
        .execute();
      await refresh();
      updateDemo(null);
      setInitialPart(null);
      setIntakeVersion((version) => version + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start this run.");
    } finally {
      setRunBusy(false);
    }
  };
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to workspace
      </a>
      <header className="global-header">
        <button
          className="wordmark"
          onClick={() => {
            setInvestigating(false);
            setHomeVersion((v) => v + 1);
            setIntro(true);
            history.replaceState(null, "", location.pathname + location.search);
            window.scrollTo(0, 0);
          }}
          aria-label="Re::Source home"
        >
          <span className="brand-mark">
            <Layers3 size={23} />
          </span>
          Re::Source
        </button>
        <nav aria-label="Main navigation">
          <button
            className={!investigating && !intro && !entered ? "active" : ""}
            onClick={openSources}
          >
            Sources & requirements
          </button>
          <button
            className={!investigating && (intro || entered) ? "active" : ""}
            onClick={() => {
              setInvestigating(false);
              setHomeVersion((v) => v + 1);
              setIntro(true);
              history.replaceState(
                null,
                "",
                location.pathname + location.search,
              );
              window.scrollTo(0, 0);
            }}
          >
            Product workspace
          </button>
          <button
            className={investigating ? "active" : ""}
            onClick={() => {
              setInvestigating(true);
              if (!investigating)
                history.replaceState(null, "", "#investigations");
              window.scrollTo(0, 0);
            }}
          >
            Investigations
          </button>
        </nav>
        <div className="header-end">
          <span className="mode-label">
            {engine
              ? `${engine.mode} · ${engine.mode === "live" ? "public leads + synthetic offers" : "synthetic data"}`
              : error
                ? "Illustrative assembly"
                : "Connecting supplier tools"}
          </span>
          <button
            className="icon-button"
            onClick={() => setSettings(!settings)}
            aria-label="Run settings"
            aria-expanded={settings}
          >
            <Settings2 size={19} />
          </button>
        </div>
      </header>
      {settings && (
        <section className="run-settings">
          <h2>Scenario run</h2>
          <label>
            Mode
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as Schema<"Mode">)}
            >
              <option value="seeded">Seeded</option>
              <option value="live">Live research</option>
              <option value="replay">Replay current run</option>
            </select>
          </label>
          <button
            className="secondary"
            disabled={runBusy || demoSourceBusy || !engine}
            onClick={() => void newRun()}
          >
            <RotateCcw size={15} />
            Start new run
          </button>
          <p className="small muted">
            Previous runs are retained. Live mode requires configured
            integrations; eligibility still depends on evidence.
          </p>
        </section>
      )}
      {error && !intro && (
        <ErrorNotice
          retry={() => void (demoStartFailed ? startDemo() : refresh())}
        >
          {error}
        </ErrorNotice>
      )}
      <div id="main-content">
        {runBusy && startingDemo.current && (
          <Loading>Creating an isolated prepared-demo run…</Loading>
        )}
        {demo &&
          engine?.scenario_run_id === demo.runId &&
          (!intro || investigating) && (
            <DemoGuide
              key={`demo-guide:${demo.runId}`}
              session={demo}
              screen={
                investigating
                  ? "investigations"
                  : !entered
                    ? "sources"
                    : workspaceTab
              }
              onSession={updateDemo}
              onBusyChange={setDemoSourceBusy}
              onSourcesLoaded={() => {
                setIntakeVersion((version) => version + 1);
                openSources();
              }}
              onNavigate={openDemoScreen}
              onExit={() => updateDemo(null)}
            />
          )}
        {investigating ? (
          <Suspense fallback={<Loading>Opening investigations…</Loading>}>
            <InvestigationWorkspace
              engine={engine}
              connectionError={error}
              onReconnect={() => void refresh()}
              onPart={(id) => {
                setInitialPart(id);
                if (demo) updateDemo({ ...demo, partId: id });
                setWorkspaceTab(demo ? "suppliers" : "assembly");
                if (demo) history.replaceState(null, "", "#demo/suppliers");
                setEntered(true);
                setIntro(false);
                setInvestigating(false);
                window.scrollTo(0, 0);
              }}
            />
          </Suspense>
        ) : intro ? (
          <ProductHome
            key={homeVersion}
            engine={engine}
            connectionFailed={Boolean(error)}
            onRetry={() => void refresh()}
            onSources={openSources}
            {...{ onStartDemo: () => void startDemo() }}
            onPart={(id) => {
              setInitialPart(id);
              setWorkspaceTab("assembly");
              setEntered(true);
              setIntro(false);
              window.scrollTo(0, 0);
            }}
          />
        ) : !entered ? (
          <Intake
            key={intakeVersion}
            engine={engine}
            onExplore={() => setEntered(true)}
            onActivated={refresh}
          />
        ) : !engine ? (
          <Loading>Connecting to the engine workspace…</Loading>
        ) : (
          <Workspace
            key={engine.scenario_run_id}
            engine={engine}
            initialPart={initialPart}
            tab={workspaceTab}
            onTabChange={changeWorkspaceTab}
            onPartChosen={(id) => {
              setInitialPart(id);
              if (demo) updateDemo({ ...demo, partId: id });
            }}
            autoInvestigate={!demo}
          />
        )}
      </div>
    </>
  );
}
function Workspace({
  engine,
  initialPart,
  tab,
  onTabChange,
  onPartChosen,
  autoInvestigate,
}: {
  engine: EngineView;
  initialPart: string | null;
  tab: Tab;
  onTabChange: (value: Tab) => void;
  onPartChosen: (id: string) => void;
  autoInvestigate: boolean;
}) {
  const [selected, setSelected] = useState<string | null>(initialPart),
    [explosion, setExplosion] = useState(0),
    [focus, setFocus] = useState(0);
  const [reduced, setReduced] = useState(
      () => matchMedia("(prefers-reduced-motion: reduce)").matches,
    ),
    [scrollMotion, setScrollMotion] = useState(true);
  const stage = useRef<HTMLElement>(null),
    [evidence, setEvidence] = useState<string | null>(null);
  const component = engine.components.find((c) => c.component_id === selected);
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => setReduced(media.matches);
    media.addEventListener("change", change);
    return () => media.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    if (reduced || !scrollMotion || tab !== "assembly" || !stage.current)
      return;
    const progress = { value: 0 };
    const observer = onScroll({
      target: stage.current,
      enter: "top top+=76",
      leave: "bottom bottom",
      sync: true,
      // Read the scroll observer itself: animation onUpdate can omit seek(0).
      // That left the mesh exploded after a fast reverse scroll to the top.
      onUpdate: (self) => setExplosion(self.progress),
    });
    const animation = animate(progress, {
      value: [0, 1],
      ease: "linear",
      autoplay: observer,
    });
    return () => {
      observer.revert();
      animation.revert();
    };
  }, [tab, reduced, scrollMotion, selected]);
  const choose = (id: string) => {
    setSelected(id);
    onPartChosen(id);
  };
  const direct = (n: number) => {
    setScrollMotion(false);
    setExplosion(n);
  };
  const changeTab = (value: Tab) => {
    onTabChange(value);
    window.scrollTo({ top: 0, behavior: "instant" });
  };
  const scene = (visual?: Schema<"VisualState">) => (
    <section
      ref={stage}
      className={`assembly-scroll ${reduced || !scrollMotion ? "direct" : ""}`}
    >
      <div className="assembly-sticky">
        <div className="scene-title">
          <div>
            <h1>Every part has a way forward.</h1>
            <p>RS-TF2 · Representative turbofan</p>
          </div>
          <Badge>
            {typeof engine.engine.asset.glb_path === "string"
              ? engine.engine.asset.provider === "uploaded_glb"
                ? "Uploaded mesh · validated nodes"
                : human(engine.engine.asset.kind)
              : "Prepared cutaway"}
          </Badge>
        </div>
        <div
          className="engine-canvas"
          aria-label="Interactive exploded jet-engine model"
        >
          <Suspense fallback={<Loading>Loading the 3D renderer…</Loading>}>
            <EngineScene
              engine={engine}
              selected={selected}
              explosion={explosion}
              visualState={visual}
              reducedMotion={reduced}
              focusToken={focus}
              onSelect={choose}
            />
          </Suspense>
          <div className="scene-orientation">
            Intake <span /> Exhaust
          </div>
        </div>
        <div className="scene-controls">
          <div className="segmented">
            <button aria-pressed={explosion < 0.05} onClick={() => direct(0)}>
              Assemble
            </button>
            <button aria-pressed={explosion > 0.95} onClick={() => direct(1)}>
              Explode
            </button>
          </div>
          <label className="explode-range">
            <span className="sr-only">Assembly separation</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={explosion}
              onChange={(e) => direct(Number(e.target.value))}
            />
          </label>
          <button
            className="icon-button"
            aria-label="Focus selected component"
            disabled={!selected}
            onClick={() => setFocus((f) => f + 1)}
          >
            <Crosshair size={19} />
          </button>
        </div>
        <div className="scene-hints">
          <span>Drag to orbit · Choose a numbered part</span>
          <label>
            <input
              type="checkbox"
              checked={scrollMotion && !reduced}
              disabled={reduced}
              onChange={(e) => setScrollMotion(e.target.checked)}
            />
            {reduced ? "Reduced motion enabled" : "Scroll to explode"}
          </label>
        </div>
        <div className="component-list" aria-label="Engine components">
          {engine.components.map((c, i) => (
            <button
              key={c.component_id}
              className={selected === c.component_id ? "selected" : ""}
              onClick={() => choose(c.component_id)}
              aria-pressed={selected === c.component_id}
            >
              <span className="component-number">{i + 1}</span>
              <span>
                <strong>{shortName(c)}</strong>
                <small>
                  {c.part_identity} · Rev {c.revision}
                </small>
              </span>
              <ArrowUpRight size={16} />
            </button>
          ))}
        </div>
        <p className="geometry-note">
          Illustrative geometry. Requirements and engineering compatibility come
          from source evidence.{" "}
          {typeof engine.engine.asset.glb_path !== "string" && (
            <a
              href="/models/licenses/engine-sources.txt"
              target="_blank"
              rel="noopener noreferrer"
            >
              Model sources & attribution
            </a>
          )}
        </p>
      </div>
    </section>
  );
  return (
    <>
      <div className="workspace-toolbar">
        <div className="breadcrumb">
          <Box size={17} />
          <span>Engine recovery</span>
          {component && (
            <>
              <span>/</span>
              <strong>{shortName(component)}</strong>
            </>
          )}
        </div>
        <nav className="workspace-tabs" aria-label="Workspace views">
          {(
            [
              ["assembly", "Assembly", Box],
              ["suppliers", "Suppliers", Search],
              ["documents", "Approval pack", FileText],
            ] as const
          ).map(([id, name, Icon]) => (
            <button
              key={id}
              className={tab === id ? "active" : ""}
              onClick={() => changeTab(id)}
              aria-current={tab === id ? "page" : undefined}
            >
              <Icon size={16} />
              {name}
            </button>
          ))}
        </nav>
      </div>
      {component ? (
        <CaseWorkspace
          key={`${engine.scenario_run_id}:${component.case_id}`}
          engine={engine}
          component={component}
          tab={tab}
          setTab={changeTab}
          scene={scene}
          onEvidence={setEvidence}
          autoInvestigate={autoInvestigate}
        />
      ) : (
        <div className={tab === "assembly" ? "engine-layout" : "content-width"}>
          {tab === "assembly" ? (
            <>
              {scene()}
              <aside className="inspector">
                <div className="inspector-empty">
                  <Box size={30} />
                  <h2>Select a part to begin.</h2>
                  <p>
                    Choose a component in the engine or the list. Its supplier
                    investigation, evidence and recovery options will stay
                    connected here.
                  </p>
                  <div className="small muted">
                    Three component cases are available in this seeded
                    workspace.
                  </div>
                </div>
              </aside>
            </>
          ) : (
            <Empty title="Select an engine component first">
              Open the assembly and choose a part to investigate its suppliers
              and prepare a review pack.
            </Empty>
          )}
        </div>
      )}
      {evidence && (
        <EvidenceDialog
          key={evidence}
          id={evidence}
          onClose={() => setEvidence(null)}
        />
      )}
    </>
  );
}
function CaseWorkspace({
  engine,
  component,
  tab,
  setTab,
  scene,
  onEvidence,
  autoInvestigate,
}: {
  engine: EngineView;
  component: ComponentInstance;
  tab: Tab;
  setTab: (t: Tab) => void;
  scene: (v?: Schema<"VisualState">) => React.ReactNode;
  onEvidence: (id: string) => void;
  autoInvestigate: boolean;
}) {
  const state = useCase(component.case_id, engine.scenario_run_id),
    command = useCommand(state.refresh),
    started = useRef(false);
  const [diff, setDiff] = useState<Schema<"DecisionDiff"> | null>(null),
    [diffError, setDiffError] = useState("");
  const { view, decision, documents, events, connection } = state;
  useEffect(() => {
    if (view && !started.current) {
      started.current = true;
      if (autoInvestigate && view.state === "ready" && view.mode !== "replay")
        void command.execute(api.investigate(view));
    }
  }, [view, autoInvestigate]);
  useEffect(() => {
    setDiff(null);
    if (
      view?.initial_decision_id &&
      view.current_decision_id &&
      view.initial_decision_id !== view.current_decision_id
    ) {
      const abort = new AbortController();
      api
        .diff(
          view.case_id,
          view.initial_decision_id,
          view.current_decision_id,
          view.scenario_run_id,
          abort.signal,
        )
        .then(setDiff)
        .catch((e) => {
          if (!abort.signal.aborted) setDiffError(e.message);
        });
      return () => abort.abort();
    }
  }, [view?.current_decision_id]);
  const messages = (
    <>
      {state.loadError && (
        <ErrorNotice retry={() => void state.refresh()}>
          {state.loadError}
        </ErrorNotice>
      )}
      {command.error && (
        <ErrorNotice
          retry={command.canRetry ? () => void command.retry() : undefined}
        >
          {command.error}
        </ErrorNotice>
      )}
    </>
  );
  const stale =
    !!view &&
    (view.pending_change_ids.length > 0 || view.stale_reasons.length > 0);
  const inspector = (
    <aside className="inspector">
      <div className="inspector-heading">
        <span className="muted small">
          {component.part_identity} · Rev {component.revision}
        </span>
        <h2>{shortName(component)}</h2>
        <p>{component.position}</p>
      </div>
      <p>{component.short_description}</p>
      {messages}
      {!view ? (
        <Loading>Loading this component…</Loading>
      ) : (
        <>
          <div className="inline">
            <Status value={view.state} />
            <Badge>{human(view.data_origin)}</Badge>
          </div>
          <div className="failure-finding">
            <h3>Inspection finding</h3>
            <p>
              {String(component.failure_story.finding ?? "No finding supplied")}
            </p>
          </div>
          {stale && (
            <div className="warning-box">
              {view.pending_change_ids.length
                ? "New evidence is being reconciled."
                : "The previous result needs review."}{" "}
              {view.stale_reasons
                .map(staleReasonText)
                .filter(Boolean)
                .join(" ")}
            </div>
          )}
          {decision ? (
            <button className="primary" onClick={() => setTab("suppliers")}>
              Review {decision.candidates.length} recovery options{" "}
              <ArrowRight size={16} />
            </button>
          ) : (
            <button
              className="primary"
              disabled={
                command.busy ||
                !!view.active_generation_id ||
                view.mode === "replay"
              }
              onClick={() => void command.execute(api.investigate(view))}
            >
              <Search size={16} />
              {view.active_generation_id
                ? "Investigation running"
                : "Investigate suppliers"}
            </button>
          )}
          <p className="small muted">
            Source requirements: {component.requirement_set_id}. No requirements
            are inferred from the model.
          </p>
          <div className="task-list">
            {view.tasks.map((t) => (
              <div key={t.task_id}>
                <span>{t.name}</span>
                <Status value={t.status} />
              </div>
            ))}
          </div>
          {view.current_selection && (
            <div className="selected-recovery">
              <h3>Selected recovery</h3>
              <p>{view.current_selection.candidate_id}</p>
              <Status value={view.current_selection.status} />
              <button
                className="text-button"
                onClick={() => setTab("documents")}
              >
                Review approval pack <ArrowRight size={15} />
              </button>
            </div>
          )}
          <details className="recovery-controls">
            <summary>Repair visualization · {human(view.visual_state)}</summary>
            <p className="small muted">
              These actions follow the server’s selected recovery and simulated
              receipt.
            </p>
            <div className="inline">
              {(["show_failure", "remove", "install", "restore"] as const).map(
                (action) => (
                  <button
                    className="secondary compact"
                    key={action}
                    disabled={
                      command.busy ||
                      !view.allowed_visual_actions.includes(action)
                    }
                    onClick={() =>
                      void command.execute(api.visual(view.case_id, action))
                    }
                  >
                    {human(action)}
                  </button>
                ),
              )}
            </div>
          </details>
          <Activity
            events={events}
            connection={connection}
            onEvidence={onEvidence}
          />
        </>
      )}
    </aside>
  );
  if (tab === "assembly")
    return (
      <div className="engine-layout">
        {scene(view?.visual_state)}
        {inspector}
      </div>
    );
  if (!view) return <Loading>Loading recovery workspace…</Loading>;
  return (
    <main className="content-width">
      {messages}
      <div className="case-page-heading">
        <div>
          <h1>{shortName(component)}</h1>
          <p>
            {component.part_identity} · Rev {component.revision} ·{" "}
            {component.requirement_set_id}
          </p>
        </div>
        <div className="inline">
          <Status value={view.state} />
          <Badge>{view.mode} · synthetic offers</Badge>
          <button
            className="secondary compact"
            onClick={() => setTab("assembly")}
          >
            <ChevronLeft size={15} />
            Assembly
          </button>
        </div>
      </div>
      {stale && (
        <div className="warning-box">
          Evidence has changed. Selection and submission stay blocked until the
          current decision is ready.{" "}
          {view.stale_reasons.map(staleReasonText).filter(Boolean).join(" ")}
        </div>
      )}
      {tab === "suppliers" ? (
        <>
          <div className="scenario-controls">
            <span>Scenario controls</span>
            <button
              className="secondary compact"
              disabled={command.busy || !decision || view.mode === "replay"}
              onClick={() =>
                void command.execute(
                  api.injectSignal(view.scenario_run_id, "SIG-RTM-CLOSURE"),
                )
              }
            >
              Introduce port closure
            </button>
            <button
              className="secondary compact"
              disabled={command.busy || !decision || view.mode === "replay"}
              onClick={() =>
                void command.execute(
                  api.evidenceChange(view.scenario_run_id, "EVC-SB-0042-REVB"),
                )
              }
            >
              Update service bulletin
            </button>
            <button
              className="text-button"
              disabled={command.busy}
              onClick={() =>
                void command.execute(
                  api.monitoring(
                    view,
                    view.monitoring_status === "active" ? "paused" : "active",
                  ),
                )
              }
            >
              {view.monitoring_status === "active"
                ? "Pause monitoring"
                : "Resume monitoring"}
            </button>
            <span className="small muted">Synthetic events</span>
          </div>
          {diff && (
            <details className="decision-diff" open>
              <summary>
                <GitCompareArrows size={18} />
                What changed since the initial decision
              </summary>
              <p>{diff.explanation}</p>
              <p className="small muted">
                {diff.rerun_check_ids.length} checks rerun ·{" "}
                {diff.reused_check_ids.length} reused
              </p>
              {diff.user_action_needed && <p>{diff.user_action_needed}</p>}
              {diff.changed_fields.map((f, i) => (
                <p className="small" key={i}>
                  {human(f)}
                </p>
              ))}
            </details>
          )}
          {diffError && <ErrorNotice>{diffError}</ErrorNotice>}
          <Research
            view={view}
            decision={decision}
            events={events}
            connection={connection}
            busy={command.busy}
            onEvidence={onEvidence}
            onSelect={async (c) => {
              if (
                decision &&
                (await command.execute(
                  api.select(view, decision, c.candidate.candidate_id),
                ))
              )
                setTab("documents");
            }}
          />
        </>
      ) : (
        <Documents
          view={view}
          documents={documents}
          busy={command.busy}
          execute={command.execute}
          onEvidence={onEvidence}
        />
      )}
    </main>
  );
}
