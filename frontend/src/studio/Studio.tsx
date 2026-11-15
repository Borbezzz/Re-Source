import { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import "@fontsource-variable/geist-mono";
import "./studio.css";
import { Logo } from "./brand/Logo.tsx";
import { EngineCanvas, type ReassemblyPhase } from "./scene/EngineCanvas.tsx";
import type { MapMode } from "./map/SupplierMap.tsx";

const loadMap = () => import("./map/SupplierMap.tsx");
const SupplierMap = lazy(() => loadMap().then((m) => ({ default: m.SupplierMap })));
import { PROFILE_FOR_PACKAGE, SAMPLE_PACKAGE_URL, readDesignPackage, type DesignPackage, type StepId, type PackageComponent } from "./data/package.ts";
import { CHECK_ORDER, assess, counts, defaultNeed, rankAll, type Assessed, type SourcingNeed } from "./data/checks.ts";
import { DESTINATION, DISRUPTION } from "./data/sites.ts";
import { journeyApi } from "./api.ts";
import type { ProductCandidate, ProductProject } from "../product-flow/types.ts";
import { Intake } from "./screens/Intake.tsx";
import { Processing, type StepState } from "./screens/Processing.tsx";
import { ContextCard, SceneControls } from "./screens/Explore.tsx";
import { AssemblyBrowser, InspectionCard } from "./screens/AssemblyBrowser.tsx";
import { indexAssembly, type AssemblyItem } from "./data/assembly.ts";
import { AnchorCard } from "./screens/Anchor.tsx";
import { CheckPanel } from "./screens/Checks.tsx";
import { ShortlistDrawer, DisruptionAlert } from "./screens/Shortlist.tsx";
import { Fulfilment, type ProcurementStep } from "./screens/Fulfilment.tsx";
import { ReturnPanel } from "./screens/Return.tsx";
import { AgentFlow } from "./flow/AgentFlow.tsx";

export type Stage = "intake" | "processing" | "explore" | "need" | "discovery" | "checking" | "shortlist" | "fulfil" | "return";

const STEP_IDS: StepId[] = ["read", "verify", "identify", "map", "link", "scene"];
const EMPTY_COMPONENTS: PackageComponent[] = [];
const reduceMotion = () => typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;
const wait = (ms: number) => new Promise((r) => setTimeout(r, reduceMotion() ? 0 : ms));

export function Studio() {
  const [stage, setStage] = useState<Stage>("intake");
  const [error, setError] = useState<string | null>(null);
  const [steps, setSteps] = useState<Record<StepId, StepState>>(() => Object.fromEntries(STEP_IDS.map((s) => [s, { status: "pending" }])) as Record<StepId, StepState>);
  const [glbUrl, setGlbUrl] = useState<string | null>(null);
  const [pkg, setPkg] = useState<DesignPackage | null>(null);
  const [project, setProject] = useState<ProductProject | null>(null);
  const [backendState, setBackendState] = useState<"idle" | "connected" | "error">("idle");
  const [solid, setSolid] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [inspectedId, setInspectedId] = useState<string | null>(null);
  const [hovered, setHovered] = useState<AssemblyItem | null>(null);
  const [exploded, setExploded] = useState(false);
  const [cutaway, setCutaway] = useState(false);
  const [spin, setSpin] = useState(false);
  const [resetKey, setResetKey] = useState(0);
  const [need, setNeed] = useState<SourcingNeed>(() => defaultNeed());
  const [candidates, setCandidates] = useState<ProductCandidate[]>([]);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const [checkProgress, setCheckProgress] = useState<Record<string, number>>({});
  const [focusId, setFocusId] = useState<string | null>(null);
  const [disrupted, setDisrupted] = useState(false);
  const [recheck, setRecheck] = useState<"idle" | "running" | "done">("idle");
  const [previousTop, setPreviousTop] = useState<Assessed | null>(null);
  const [procure, setProcure] = useState<ProcurementStep>("prepared");
  const [invalidated, setInvalidated] = useState(false);
  const [phase, setPhase] = useState<ReassemblyPhase>("idle");
  const [busy, setBusy] = useState<string | null>(null);
  const [discoveredAt, setDiscoveredAt] = useState<Date | null>(null);
  const runRef = useRef(0);
  const sceneReady = useRef<() => void>(() => {});
  const sceneIsReady = useRef(false);

  const assemblyIndex = useMemo(() => indexAssembly(pkg?.assemblyTree ?? []), [pkg]);
  const inspection = inspectedId ? assemblyIndex.get(inspectedId) ?? null : null;
  const sourceComponent = pkg?.components.find((c) => c.componentId === selected) ?? null;
  const component = useMemo(() => sourceComponent && inspection ? { ...sourceComponent, name: inspection.children.length ? sourceComponent.name : inspection.name, nodeIds: inspection.nodeIds } : sourceComponent, [sourceComponent, inspection]);
  const clearSelection = () => { setSelected(null); setInspectedId(null); setHovered(null); };
  const inspectPart = (item: AssemblyItem) => {
    setInspectedId(item.id); setSelected(item.componentId); setHovered(null);
    if (stage === "need") setStage("explore");
  };
  const selectComponent = (id: string | null) => {
    const item = [...assemblyIndex.values()].find(item => item.componentId === id);
    if (id && item) inspectPart(item); else clearSelection();
  };
  const partId = component?.componentId.toLowerCase() ?? null;
  const requirement = pkg?.requirements.find((r) => r.componentId === selected) ?? null;

  const assessed = useMemo(() => {
    if (!component) return [];
    const req = { partNumber: component.partNumber, revision: component.revision, condition: requirement?.condition === "new" ? "New" : (requirement?.condition ?? "New") };
    const list = candidates.map((c) => assess(c, req, need, { disrupted })).filter(Boolean) as Assessed[];
    return rankAll(list, need);
  }, [candidates, component, requirement, need, disrupted]);
  const visibleCounts = useMemo(() => counts(assessed.filter((a) => checked.has(a.candidate.candidate_id))), [assessed, checked]);
  const top = assessed.find((a) => a.rank === 1) ?? null;
  useEffect(() => {
    if (stage === "explore" || stage === "need") void loadMap(); // warm the map chunk before it is needed
  }, [stage]);

  // ---------- 1 → 2: read the package ----------
  const startPackage = useCallback(async (input: File[] | "sample") => {
    const run = ++runRef.current;
    setError(null);
    setStage("processing");
    setSteps(Object.fromEntries(STEP_IDS.map((s) => [s, { status: "pending" }])) as Record<StepId, StepState>);
    setPkg(null);
    setProject(null);
    setSolid(0);
    setSelected(null);
    setInspectedId(null);
    setHovered(null);
    sceneIsReady.current = false;
    sceneReady.current = () => {};
    try {
      const bytes = input === "sample" ? new Uint8Array(await (await fetch(SAMPLE_PACKAGE_URL)).arrayBuffer()) : input;
      let projectPromise: Promise<ProductProject> | null = null;
      const parsed = await readDesignPackage(
        bytes,
        (e) => {
          if (run !== runRef.current) return;
          setSteps((s) => ({ ...s, [e.step]: { status: e.status, detail: e.detail, at: new Date() } }));
        },
        ({ packageId, glbUrl: url }) => {
          setGlbUrl(url);
          const profile = PROFILE_FOR_PACKAGE[packageId];
          if (profile) projectPromise = journeyApi.create(profile);
        },
      );
      if (run !== runRef.current) return;
      // Scene step: the model is prepared in the scene (real GLB parse + material setup).
      setSteps((s) => ({ ...s, scene: { status: "running" } }));
      await new Promise<void>((resolve) => {
        if (sceneIsReady.current) resolve();
        else sceneReady.current = resolve;
      });
      await wait(400);
      setSteps((s) => ({ ...s, scene: { status: "done", detail: `${parsed.geometry.meshOccurrences.toLocaleString()} meshes ready`, at: new Date() } }));
      if (!projectPromise) throw new Error("This package verified, but no prepared model profile exists for it. Automatic CAD-to-model generation needs a configured provider.");
      try {
        const p = await (projectPromise as Promise<ProductProject>);
        const mismatch = parsed.components.find((c) => !p.parts.some((x) => x.part_number === c.partNumber));
        if (mismatch) throw new Error(`${mismatch.name} does not match the prepared profile.`);
        setProject(p);
        setBackendState("connected");
      } catch (e) {
        setBackendState("error");
        throw e instanceof Error ? e : new Error("The Re::Source API is unavailable.");
      }
      setPkg(parsed);
    } catch (e) {
      if (run !== runRef.current) return;
      setError(e instanceof Error ? e.message : "The package could not be read.");
    }
  }, []);

  useEffect(() => {
    const clear = () => setHovered(null);
    window.addEventListener("blur", clear);
    document.addEventListener("visibilitychange", clear);
    return () => { window.removeEventListener("blur", clear); document.removeEventListener("visibilitychange", clear); };
  }, []);

  const onSceneReady = useCallback(() => {
    sceneIsReady.current = true;
    sceneReady.current();
  }, []);

  // ---------- 2 → 3: confirm identity, reveal metal ----------
  const confirmIdentity = useCallback(async () => {
    if (!project) return;
    setBusy("confirm");
    try {
      const p = await journeyApi.confirmParts(project);
      setProject(p);
      const start = performance.now();
      const dur = reduceMotion() ? 1 : 1700;
      await new Promise<void>((resolve) => {
        // Timer-driven so the reveal completes even when frames are throttled.
        const id = setInterval(() => {
          const t = Math.min(1, (performance.now() - start) / dur);
          setSolid(t);
          if (t >= 1) {
            clearInterval(id);
            resolve();
          }
        }, 16);
      });
      setStage("explore");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Confirmation failed.");
    } finally {
      setBusy(null);
    }
  }, [project]);

  // ---------- 4 → 5/6: research + per-candidate checks ----------
  const findSuppliers = useCallback(async () => {
    if (!project || !partId) return;
    const run = ++runRef.current;
    setBusy("research");
    setError(null);
    setCandidates([]);
    setChecked(new Set());
    setCheckProgress({});
    setDisrupted(false);
    setRecheck("idle");
    setPreviousTop(null);
    setInvalidated(false);
    setProcure("prepared");
    setStage("discovery");
    try {
      const p = await journeyApi.research(project.project_id, partId);
      if (run !== runRef.current) return;
      setProject(p);
      const r = p.research.find((x) => x.part_id === partId);
      if (!r || r.status !== "complete") throw new Error(r?.error ?? "Supplier research failed.");
      setCandidates(r.candidates);
      setDiscoveredAt(new Date(r.completed_at ?? Date.now()));
      await wait(1500);
      if (run !== runRef.current) return;
      setStage("checking");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Supplier research failed.");
    } finally {
      setBusy(null);
    }
  }, [project, partId]);

  // Animated, per-candidate qualification. Candidate discovery precedes checks;
  // up to two candidates are checked in parallel; pins update as results land.
  useEffect(() => {
    if (stage !== "checking" || !assessed.length) return;
    const run = runRef.current;
    let cancelled = false;
    const ids = assessed.map((a) => a.candidate.candidate_id).filter((id) => !checked.has(id));
    const fast = reduceMotion();
    (async () => {
      const lanes = 2;
      let next = 0;
      const worker = async () => {
        while (!cancelled && next < ids.length) {
          const id = ids[next++];
          setCheckingId(id);
          setFocusId(id);
          for (let i = 1; i <= CHECK_ORDER.length; i++) {
            if (cancelled || run !== runRef.current) return;
            setCheckProgress((cp) => ({ ...cp, [id]: i }));
            await new Promise((r) => setTimeout(r, fast ? 0 : 150));
          }
          setChecked((s) => new Set(s).add(id));
        }
      };
      await Promise.all(Array.from({ length: lanes }, (_, i) => wait(i * 260).then(worker)));
      if (cancelled || run !== runRef.current) return;
      setCheckingId(null);
    })();
    return () => {
      cancelled = true;
    };
  }, [stage]); // eslint-disable-line react-hooks/exhaustive-deps

  const skipChecks = () => {
    setChecked(new Set(assessed.map((a) => a.candidate.candidate_id)));
    setCheckProgress(Object.fromEntries(assessed.map((a) => [a.candidate.candidate_id, CHECK_ORDER.length])));
    setCheckingId(null);
  };
  const toShortlist = () => {
    setStage("shortlist");
    setFocusId(assessed.find((a) => a.rank === 1)?.candidate.candidate_id ?? null);
  };

  // ---------- 8: disruption → selective recheck → revised ranking ----------
  const injectDisruption = async () => {
    setPreviousTop(top);
    setRecheck("running");
    setDisrupted(true);
    if (project?.package && project.package.status !== "draft") setInvalidated(true);
    const affected = assessed.find((a) => DISRUPTION.affects(a.candidate.candidate_id));
    if (affected) setFocusId(affected.candidate.candidate_id);
    await wait(2200);
    setRecheck("done");
  };
  useEffect(() => {
    if (recheck === "done") setFocusId(assessed.find((a) => a.rank === 1)?.candidate.candidate_id ?? null);
  }, [recheck]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------- 9: select supplier → reviewable RFQ ----------
  const selectSupplier = async (candidateId: string) => {
    if (!project || !partId || !component) return;
    setBusy("select");
    try {
      await journeyApi.select(project.project_id, partId, candidateId);
      const p = await journeyApi.package(project.project_id, {
        part_id: partId,
        selected_item: component.name,
        quantity: need.quantity,
        required_by: need.requiredBy,
        delivery_destination: DESTINATION.site,
        buyer_company: "Aldbury Aero Maintenance Ltd",
        buyer_contact: "Procurement desk",
      });
      setProject(p);
      setProcure("prepared");
      setInvalidated(false);
      setStage("fulfil");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not prepare the enquiry.");
    } finally {
      setBusy(null);
    }
  };
  const approve = async () => {
    if (!project?.package) return;
    setBusy("approve");
    try {
      setProject(await journeyApi.approve(project.project_id, project.package.package_id));
      setProcure("approved");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approval failed.");
    } finally {
      setBusy(null);
    }
  };
  const send = async () => {
    if (!project?.package) return;
    setBusy("send");
    try {
      setProject(await journeyApi.simulate(project.project_id, project.package.package_id));
      setProcure("sent");
      await wait(1300);
      setProcure("acknowledged");
      await wait(1500);
      setProcure("confirmed");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sending failed.");
    } finally {
      setBusy(null);
    }
  };

  // ---------- 10: reassembly preview ----------
  const toReturn = async () => {
    setStage("return");
    setExploded(false);
    setPhase("idle");
    await wait(700);
    setPhase("remove");
    await wait(1500);
    setPhase("insert");
    await wait(1800);
    setPhase("done");
  };

  const resetAll = () => {
    runRef.current++;
    setStage("intake");
    setPkg(null);
    setGlbUrl(null);
    setProject(null);
    setSelected(null);
    setInspectedId(null);
    setHovered(null);
    setCandidates([]);
    setError(null);
    setSolid(0);
    setPhase("idle");
    setExploded(false);
    setCutaway(false);
    setNeed(defaultNeed());
  };

  const sceneMode = stage === "processing" ? "scan" : stage === "explore" || stage === "need" || stage === "return" ? "explore" : "hidden";
  const scanProgress = STEP_IDS.reduce((n, s) => n + (steps[s].status === "done" ? 1 : steps[s].status === "running" ? 0.5 : 0), 0) / STEP_IDS.length;
  const onMap = stage === "discovery" || stage === "checking" || stage === "shortlist";
  const mapMode: MapMode = stage === "shortlist" ? (disrupted ? "disruption" : "shortlist") : stage === "checking" ? "checking" : "discovery";
  const mapChecked = stage === "discovery" ? new Set<string>() : checked;
  const disruptedId = disrupted ? (assessed.find((a) => DISRUPTION.affects(a.candidate.candidate_id))?.candidate.candidate_id ?? null) : null;
  const procurementDone = procure === "confirmed";

  return (
    <div className="rs-studio" data-stage={stage}>
      <div className="rs-aurora" />
      <div className="rs-grain" />
      <header className={`rs-header${sceneMode !== "hidden" || onMap ? " is-floating" : ""}`}>
        <button type="button" className="rs-logo" onClick={resetAll} aria-label="Re::Source — start a new assembly" style={{ background: "none", border: 0, cursor: "pointer", padding: 0 }}>
          <Logo size={30} />
        </button>
        <div className="rs-header-right">
          {backendState !== "idle" ? (
            <span className="rs-tiny rs-provenance" title={backendState === "connected" ? "State persisted by the Re::Source API" : "API unavailable"}>
              <i className={`rs-live-dot${backendState === "connected" ? "" : " off"}`} />
              {backendState === "connected" ? `Case ${project?.project_id.slice(-6) ?? ""}` : "API offline"}
            </span>
          ) : null}
          <a className="rs-header-link" href="#investigations">Saved work</a>
          <a className="rs-header-link" href="#help" onClick={(e) => (e.preventDefault(), window.open("https://github.com/Borbezzz/Re-Source/blob/main/frontend%20improve/DESIGN-FLOW.md", "_blank", "noopener"))}>
            Help
          </a>
          <span className="rs-avatar" aria-hidden="true">B</span>
        </div>
      </header>

      {/* Persistent model layer: one asset identity across processing, explore, need and return. */}
      {glbUrl && pkg !== undefined ? (
        <div className="rs-scene-layer" style={{ opacity: sceneMode === "hidden" ? 0 : 1, transition: "opacity .7s var(--rs-ease)", top: "var(--rs-header)" }} aria-hidden={sceneMode === "hidden"}>
          <EngineCanvas
            url={glbUrl}
            mode={sceneMode}
            scan={stage === "processing" ? scanProgress : 1}
            solid={stage === "processing" ? solid : 1}
            components={pkg?.components ?? EMPTY_COMPONENTS}
            selected={selected}
            inspection={inspection}
            hovered={stage === "explore" ? hovered : null}
            onInspect={(id) => { const item = assemblyIndex.get(id); if (stage === "explore" && item) inspectPart(item); }}
            exploded={exploded}
            cutaway={cutaway}
            isolate={stage !== "return" || phase !== "done"}
            spin={spin}
            phase={phase}
            showHotspots={stage === "explore" && !!inspection}
            resetKey={resetKey}
            onSelect={(id) => {
              if (stage !== "explore") return;
              selectComponent(id);
            }}
            rightInset={stage === "explore" ? 360 : stage === "return" ? 420 : 0}
            wide={stage === "return"}
            leftInset={(stage === "explore" || stage === "need") && inspection ? 440 : 0}
            onReady={onSceneReady}
          />
        </div>
      ) : null}

      <AnimatePresence>
        {onMap ? (
          <motion.div key="map" className="rs-stage" initial={{ opacity: 0, scale: 1.03 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}>
            <Suspense fallback={<div className="rs-loading">Loading map…</div>}>
            <SupplierMap
              list={assessed}
              mode={mapMode}
              checked={mapChecked}
              checkingId={checkingId}
              selectedId={focusId}
              onSelect={(id) => setFocusId(id)}
              disruptedId={disruptedId}
              insetRight={stage === "shortlist" ? 0.34 : 0.3}
            />
            </Suspense>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <LayoutGroup>
        <AnimatePresence mode="wait">
          {stage === "intake" ? (
            <Intake key="intake" onFiles={(f) => void startPackage(f)} error={error} />
          ) : null}
        </AnimatePresence>

        {stage === "processing" ? (
          <Processing steps={steps} pkg={pkg} project={project} error={error} busy={busy === "confirm"} onConfirm={confirmIdentity} onRetry={resetAll} solid={solid} />
        ) : null}

        {(stage === "explore" || stage === "need") && pkg && glbUrl ? (
          <div className="rs-ui-layer">
            <div className="rs-crumb rs-eyebrow">{project?.name ?? pkg.displayName} / Assembly</div>
            <AssemblyBrowser items={pkg.assemblyTree} selected={inspectedId} onSelect={inspectPart} onHover={setHovered} />
            {stage === "explore" && !inspection ? <SceneControls spin={spin} exploded={exploded} cutaway={cutaway} onCutaway={() => setCutaway(v => !v)} onSpin={() => setSpin((v) => !v)} onExplode={() => setExploded((v) => !v)} onReset={() => { setExploded(false); setCutaway(false); clearSelection(); setResetKey((k) => k + 1); }} /> : null}
            {inspection && !component ? <InspectionCard item={inspection} onClose={clearSelection} /> : null}
            <AnimatePresence mode="wait">
              {component && requirement ? (
                <ContextCard
                  key={component.componentId}
                  glbUrl={glbUrl}
                  component={component}
                  requirement={requirement}
                  mode={stage === "need" ? "need" : "context"}
                  need={need}
                  onNeed={setNeed}
                  onStart={(reason) => { setNeed((n) => ({ ...n, reason })); setStage("need"); }}
                  onBack={() => setStage("explore")}
                  onClose={() => { clearSelection(); setStage("explore"); }}
                  onSubmit={() => void findSuppliers()}
                  busy={busy === "research"}
                />
              ) : null}
            </AnimatePresence>
          </div>
        ) : null}

        {onMap && component && glbUrl ? (
          <div className="rs-ui-layer">
            <AnchorCard
              glbUrl={glbUrl}
              component={component}
              need={need}
              onReturn={() => setStage("explore")}
              status={stage === "discovery" ? (candidates.length ? `${candidates.length} sites found` : "Discovering sites…") : undefined}
            />
            {stage === "discovery" ? (
              <motion.div className="rs-check-panel rs-panel" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} style={{ maxWidth: 440 }}>
                <h2 className="rs-h2">{candidates.length ? "Supplier sites found" : "Discovering supplier sites"}</h2>
                <p className="rs-small" style={{ margin: 0 }}>
                  {candidates.length
                    ? `${candidates.length} supplying sites found for ${component.partNumber} Rev ${component.revision}. Pins mark stock, production or dispatch sites — not company headquarters.`
                    : "Searching supplier sources for stock, production and dispatch sites."}
                </p>
                <div className="rs-progress"><i style={{ width: candidates.length ? "100%" : "38%" }} /></div>
                <span className="rs-tiny">
                  Coverage: UK & EU stockists, distributors, build-to-print shops · {discoveredAt ? `sourced ${discoveredAt.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}` : "in progress"}
                </span>
                {error ? <p className="rs-intake-error">{error}</p> : null}
              </motion.div>
            ) : null}
            {stage === "checking" ? (
              <CheckPanel
                list={assessed}
                checked={checked}
                checkingId={checkingId}
                progress={checkProgress}
                focusId={focusId}
                onFocus={setFocusId}
                counts={visibleCounts}
                total={assessed.length}
                onSkip={skipChecks}
                onDone={toShortlist}
              />
            ) : null}
            {stage === "shortlist" ? (
              <>
                {disrupted ? <DisruptionAlert recheck={recheck} affected={assessed.find((a) => a.candidate.candidate_id === disruptedId) ?? null} need={need} /> : null}
                <ShortlistDrawer
                  list={assessed}
                  focusId={focusId}
                  onFocus={setFocusId}
                  need={need}
                  disrupted={disrupted}
                  recheck={recheck}
                  previousTop={previousTop}
                  invalidated={invalidated}
                  onDisrupt={() => void injectDisruption()}
                  onSelect={(id) => void selectSupplier(id)}
                  busy={busy === "select"}
                />
              </>
            ) : null}
          </div>
        ) : null}
      </LayoutGroup>

      {onMap ? (
        <div className="rs-legend" aria-hidden="true">
          <span><svg width="12" height="16" viewBox="-10 -27 20 28"><path d="M0 0 C -6 -8 -9 -11 -9 -16 A 9 9 0 1 1 9 -16 C 9 -11 6 -8 0 0 Z" fill="#4ade9c" /></svg>Eligible</span>
          <span><svg width="12" height="16" viewBox="-10 -27 20 28"><path d="M0 0 C -6 -8 -9 -11 -9 -16 A 9 9 0 1 1 9 -16 C 9 -11 6 -8 0 0 Z" fill="none" stroke="#fbbf24" strokeWidth="2" /></svg>Awaiting evidence</span>
          <span><svg width="16" height="16" viewBox="-10 -10 20 20"><circle r="8" fill="none" stroke="#8a857d" strokeWidth="1.6" /><line x1="-5" y1="5" x2="5" y2="-5" stroke="#8a857d" strokeWidth="1.6" /></svg>Excluded</span>
          <span><svg width="12" height="12" viewBox="-7 -7 14 14"><rect x="-6" y="-6" width="12" height="12" fill="#f4f1ea" /></svg>Destination</span>
        </div>
      ) : null}

      {stage === "fulfil" && project?.package && component && glbUrl ? (
        <Fulfilment
          glbUrl={glbUrl}
          component={component}
          need={need}
          project={project}
          chosen={assessed.find((a) => a.candidate.candidate_id === project.selections[partId!]) ?? null}
          step={procure}
          busy={busy}
          onApprove={() => void approve()}
          onSend={() => void send()}
          onBack={() => setStage("shortlist")}
          onFinish={() => void toReturn()}
          done={procurementDone}
        />
      ) : null}

      {stage === "return" && component && project ? (
        <ReturnPanel
          component={component}
          project={project}
          chosen={assessed.find((a) => a.candidate.candidate_id === project.selections[partId!]) ?? null}
          phase={phase}
          onReplay={() => void toReturn()}
          onAssembly={() => { setPhase("idle"); setStage("explore"); }}
          onNew={resetAll}
        />
      ) : null}

      {error && stage !== "intake" && stage !== "processing" && stage !== "discovery" ? (
        <div className="rs-alert" role="alert" style={{ top: "auto", bottom: 24 }}>
          <span className="rs-alert-ico">!</span>
          <div className="rs-small" style={{ color: "var(--rs-text)" }}>{error}</div>
          <button type="button" className="rs-btn rs-btn-sm" onClick={() => setError(null)}>Dismiss</button>
        </div>
      ) : null}

      {/* Live n8n-style agent workflow (portal; Scene / Split / Workflow views). */}
      <AgentFlow
        project={project}
        partId={partId}
        stage={stage}
        part={component ? { name: component.name, partNumber: component.partNumber, revision: component.revision } : null}
        need={need}
        assessed={assessed}
        checked={checked}
        progress={checkProgress}
        disrupted={disrupted}
        recheck={recheck}
        procure={procure}
        chosenId={partId ? (project?.selections[partId] ?? null) : null}
        phase={phase}
        busy={busy}
        error={error}
        caseId={project?.project_id ?? null}
        focusId={focusId}
        onFocusCandidate={setFocusId}
      />
    </div>
  );
}
