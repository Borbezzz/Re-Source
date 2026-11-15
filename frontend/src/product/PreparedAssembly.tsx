import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { animate, onScroll } from "animejs";
import { ArrowRight, Check, X } from "lucide-react";
import assembly from "./toy-car.json";
const ProductScene = lazy(() => import("./ProductScene.tsx"));
export function PreparedAssembly({ onEngine }: { onEngine: () => void }) {
  const [selected, setSelected] = useState<string[]>([]),
    [progress, setProgress] = useState(0),
    [direct, setDirect] = useState(false),
    [reduced, setReduced] = useState(
      () => matchMedia("(prefers-reduced-motion: reduce)").matches,
    );
  const track = useRef<HTMLElement>(null);
  const [active, setActive] = useState(assembly.components[0].component_id);
  useEffect(() => {
    const q = matchMedia("(prefers-reduced-motion: reduce)"),
      change = () => setReduced(q.matches);
    q.addEventListener("change", change);
    return () => q.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    if (reduced || direct || !track.current) return;
    const v = { p: 0 };
    const observer = onScroll({
      target: track.current,
      enter: "top+=72 top",
      leave: "bottom bottom",
      sync: true,
      onUpdate: (s) => setProgress(s.progress),
    });
    const a = animate(v, { p: [0, 1], ease: "linear", autoplay: observer });
    return () => {
      observer.revert();
      a.revert();
    };
  }, [reduced, direct]);
  const toggle = (id: string) => {
    setActive(id);
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };
  const part = assembly.components.find((p) => p.component_id === active)!;
  const separate = (value: number) => {
    setDirect(true);
    setProgress(value);
  };
  return (
    <section
      id="prepared-assembly"
      ref={track}
      className={`assembly-track ${reduced || direct ? "direct" : ""}`}
      aria-label="Explore the prepared assembly"
    >
      <div className="assembly-sticky">
        <div className="assembly-stage">
          <div className="assembly-title">
            <div>
              <h2>Toy car, taken apart.</h2>
              <p>Choose one part or build a selection.</p>
            </div>
            <span className="asset-status">
              Prepared model · 8 visual groups
            </span>
          </div>
          <Suspense
            fallback={<div className="model-loading">Preparing the model…</div>}
          >
            <ProductScene
              selected={selected}
              separation={progress}
              reduced={reduced}
              onSelect={toggle}
            />
          </Suspense>
          <div className="assembly-controls">
            <span>
              {reduced || direct
                ? "Direct controls"
                : "Scroll to separate · reverse to reassemble"}
            </span>
            <div>
              <button onClick={() => separate(0)}>Assemble</button>
              <input
                aria-label="Assembly separation"
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={progress}
                onChange={(e) => separate(Number(e.target.value))}
              />
              <button onClick={() => separate(1)}>Explode</button>
            </div>
          </div>
          <p className="asset-credit">
            Curated model by Guido Odendahl & Eric Chadwick · CC0.{" "}
            <a href={assembly.source_url} target="_blank" rel="noreferrer">
              Model source ↗
            </a>
          </p>
        </div>
        <aside className="part-sidebar">
          <div className="part-list-heading">
            <h3>Parts</h3>
            <button
              className="text-button compact"
              onClick={() =>
                setSelected(
                  selected.length === assembly.components.length
                    ? []
                    : assembly.components.map((p) => p.component_id),
                )
              }
            >
              {selected.length === assembly.components.length
                ? "Clear selection"
                : "Select all"}
            </button>
          </div>
          <div className="prepared-part-list" aria-label="Selectable parts">
            {assembly.components.map((p) => (
              <button
                key={p.component_id}
                aria-pressed={selected.includes(p.component_id)}
                onClick={() => toggle(p.component_id)}
              >
                <span className="part-checkbox">
                  {selected.includes(p.component_id) && <Check size={12} />}
                </span>
                {p.label}
              </button>
            ))}
          </div>
          <section className="part-source-detail" aria-live="polite">
            <h3>{part.label}</h3>
            <dl>
              <div>
                <dt>Geometry</dt>
                <dd>Prepared visual group</dd>
              </div>
              <div>
                <dt>Dimensions</dt>
                <dd>Source required</dd>
              </div>
              <div>
                <dt>Material & tolerance</dt>
                <dd>Source required</dd>
              </div>
            </dl>
            <p>
              Geometry helps you explore. Documents establish the requirements.
            </p>
            <p>
              Continue with the toy-car demo to review its sample specification.
            </p>
          </section>
          <div className="selection-tray">
            <strong>
              {selected.length} {selected.length === 1 ? "part" : "parts"}{" "}
              selected
            </strong>
            <div className="selection-chips">
              {selected.map((id) => (
                <button
                  key={id}
                  onClick={() => toggle(id)}
                  aria-label={`Remove ${assembly.components.find((p) => p.component_id === id)?.label}`}
                >
                  {
                    assembly.components.find((p) => p.component_id === id)
                      ?.label
                  }
                  <X size={12} />
                </button>
              ))}
            </div>
            <p>
              Take this product through source review, supplier research and a
              reviewable sourcing package.
            </p>
            <button className="secondary" onClick={onEngine}>
              Choose a demo product <ArrowRight size={15} />
            </button>
          </div>
        </aside>
      </div>
    </section>
  );
}
