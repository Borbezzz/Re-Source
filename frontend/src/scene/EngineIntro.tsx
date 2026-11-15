import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { animate, onScroll } from "animejs";
import { ArrowDown, ArrowRight, FileUp, RotateCcw } from "lucide-react";
import manifest from "../../../data/manifests/engine-demo-001.json";
import type { EngineView } from "../api/types.ts";
import { demoModules } from "./model.ts";
const EngineScene = lazy(() => import("./EngineScene.tsx"));

// The same explicitly synthetic manifest as the server. This only lets the
// illustration render during connection; it creates no run or supplier result.
const illustration = {
  engine: manifest.engine,
  components: manifest.components,
  visual_states: manifest.visual_states,
  operating_story: manifest.engine.operating_story,
  cases: [],
  scenario_run_id: "illustration-only",
  mode: "seeded",
} as unknown as EngineView;
const moduleParts: Record<string, string[]> = {
  Module_HPC: ["component-secondary-b"],
  Module_Combustor: ["component-primary"],
  Module_HPT: ["component-secondary-a"],
};
const descriptions: Record<string, string> = {
  Module_Fan:
    "The front of the flow. A large fan draws air into the engine and around its core.",
  Module_LPC:
    "The first compression stages feed air into the high-pressure core.",
  Module_HPC:
    "Successive blade rows compress the core airflow. Explore the bleed-air duct in this module.",
  Module_Combustor:
    "Fuel meets compressed air. Explore the fuel nozzle and its source requirements.",
  Module_HPT:
    "The hottest turbine stage extracts energy to drive the high-pressure compressor.",
  Module_LPT:
    "Downstream turbine stages drive the fan and low-pressure compressor.",
  Module_Exhaust: "The final passage directs the engine's exhaust flow.",
};
export function EngineIntro({
  engine,
  onSources,
  onPart,
  connectionFailed,
  onRetry,
}: {
  engine: EngineView | null;
  connectionFailed: boolean;
  onRetry: () => void;
  onSources: () => void;
  onPart: (id: string) => void;
}) {
  const view = engine ?? illustration;
  const [detailsOpen, setDetailsOpen] = useState(false);
  const chooseModule = (id: string) => {
    setModule(id);
    setDetailsOpen(true);
  };
  const [progress, setProgress] = useState(0),
    [module, setModule] = useState<string | null>(null);
  const [direct, setDirect] = useState(false),
    [reduced, setReduced] = useState(
      () => matchMedia("(prefers-reduced-motion: reduce)").matches,
    );
  const stage = useRef<HTMLElement>(null);
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => setReduced(media.matches);
    media.addEventListener("change", change);
    return () => media.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    if (reduced || direct || !stage.current) return;
    const value = { p: 0 };
    const observer = onScroll({
      target: stage.current,
      enter: "top top+=76",
      leave: "bottom bottom",
      sync: true,
      onUpdate: (self) => setProgress(self.progress),
    });
    const animation = animate(value, {
      p: [0, 1],
      ease: "linear",
      autoplay: observer,
    });
    return () => {
      observer.revert();
      animation.revert();
    };
  }, [reduced, direct]);
  const parts = module
    ? view.components.filter((c) =>
        moduleParts[module]?.includes(c.component_id),
      )
    : view.components;
  const choosePart = (id: string) => {
    if (engine) onPart(id);
    else
      setModule(
        Object.keys(moduleParts).find((key) => moduleParts[key].includes(id)) ??
          null,
      );
  };
  const setSeparation = (n: number) => {
    setDirect(true);
    setProgress(n);
  };
  return (
    <main className="engine-intro">
      <section
        ref={stage}
        className={`intro-scroll ${reduced || direct ? "direct" : ""}`}
        aria-label="Explore the jet engine"
      >
        <div className="intro-sticky">
          <div className="intro-stage">
            <div className="intro-heading">
              <h1>
                Understand the part.
                <br />
                Find a way forward.
              </h1>
              <p className="intro-caption">
                {progress < 0.2
                  ? "Scroll to reveal the assembly."
                  : progress < 0.75
                    ? "Seven modules. Every part connected."
                    : "Choose a module. Investigate a part."}
              </p>
            </div>
            <div className="intro-canvas" aria-label="Interactive jet engine">
              <span className="engine-designation">
                RS–TF2{" "}
                <span>
                  {view.engine.asset.glb_path
                    ? "Uploaded assembly"
                    : "Prepared cutaway"}
                </span>
              </span>
              <Suspense
                fallback={
                  <div className="scene-loading">
                    Preparing the interactive assembly…
                  </div>
                }
              >
                <EngineScene
                  engine={view}
                  selected={null}
                  explosion={progress}
                  reducedMotion={reduced}
                  focusToken={0}
                  onSelect={choosePart}
                  selectedModule={module}
                  onSelectModule={chooseModule}
                  hero
                />
              </Suspense>
            </div>
            <nav className="module-strip" aria-label="Engine modules">
              {demoModules.map((m, i) => (
                <button
                  key={m.node_name}
                  aria-pressed={module === m.node_name}
                  onClick={() => chooseModule(m.node_name)}
                >
                  <span>0{i + 1}</span>
                  {m.label}
                </button>
              ))}
            </nav>
            <button
              className="mobile-details-toggle"
              aria-expanded={detailsOpen}
              aria-controls="intro-details"
              onClick={() => setDetailsOpen(!detailsOpen)}
            >
              Parts, requirements & source upload <ArrowRight size={15} />
            </button>
            <div className="intro-motion">
              <span className="scroll-instruction">
                <ArrowDown size={15} />
                {reduced
                  ? "Explore at your pace"
                  : "Scroll to explode · reverse to reassemble"}
              </span>
              <div className="intro-direct">
                <button onClick={() => setSeparation(0)}>Assemble</button>
                <input
                  aria-label="Assembly separation"
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={progress}
                  onChange={(e) => setSeparation(Number(e.target.value))}
                />
                <button onClick={() => setSeparation(1)}>Explode</button>
                {direct && !reduced && (
                  <button
                    aria-label="Restore scroll animation"
                    onClick={() => setDirect(false)}
                  >
                    <RotateCcw size={14} />
                  </button>
                )}
              </div>
            </div>
          </div>
          <aside
            id="intro-details"
            className={`intro-inspector ${detailsOpen ? "is-open" : ""}`}
          >
            <button
              className="mobile-details-close"
              onClick={() => setDetailsOpen(false)}
            >
              Close details ×
            </button>
            <div className="intro-upload">
              <FileUp size={23} />
              <h2>
                Your engine.
                <br />
                Your requirements.
              </h2>
              <p>
                Connect a blueprint and part specification to the parts you
                need.
              </p>
              <button className="primary" onClick={onSources}>
                Upload source documents <ArrowRight size={16} />
              </button>
            </div>
            <div className="intro-module-detail" aria-live="polite">
              <p className="eyebrow">
                {module ? "SELECTED MODULE" : "EXPLORE THE ASSEMBLY"}
              </p>
              <h2>
                {demoModules.find((m) => m.node_name === module)?.label ??
                  "Find your starting point."}
              </h2>
              <p>
                {module
                  ? descriptions[module]
                  : "Choose an engine module or one of the three example parts to open its sourcing workspace."}
              </p>
              <div className="intro-parts">
                {parts.map((c) => (
                  <button
                    key={c.component_id}
                    onClick={() => choosePart(c.component_id)}
                    disabled={!engine}
                  >
                    <span>
                      <strong>
                        {c.part_identity === "RS-FN-1001"
                          ? "Fuel nozzle"
                          : c.part_identity === "RS-NGV-2040"
                            ? "NGV segment"
                            : "Bleed duct"}
                      </strong>
                      <small>
                        {c.part_identity} · Rev {c.revision}
                      </small>
                    </span>
                    <ArrowRight size={16} />
                  </button>
                ))}
              </div>
              {module && !parts.length && (
                <p className="small">
                  No supplier case is mapped to this module yet. Upload source
                  documents to define its parts.
                </p>
              )}
              {!engine && (
                <p className="connection-note" role="status">
                  {connectionFailed
                    ? "Supplier tools are temporarily unavailable. You can still explore the assembly."
                    : "The assembly is ready to explore. Supplier tools are connecting."}
                  {connectionFailed && (
                    <button className="connection-retry" onClick={onRetry}>
                      Retry connection
                    </button>
                  )}
                </p>
              )}
            </div>
            <div className="intro-requirements">
              <h3>Defined by your sources</h3>
              <dl>
                {["Dimensions", "Material", "Tolerance", "Certifications"].map(
                  (name) => (
                    <div key={name}>
                      <dt>{name}</dt>
                      <dd>Source required</dd>
                    </div>
                  ),
                )}
              </dl>
              <p>
                {view.engine.asset.glb_path
                  ? "Uploaded geometry."
                  : "Prepared demonstration geometry."}{" "}
                Engineering requirements come from reviewed documents.{" "}
                {!view.engine.asset.glb_path && (
                  <a
                    href="/models/licenses/engine-sources.txt"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Model sources
                  </a>
                )}
              </p>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
