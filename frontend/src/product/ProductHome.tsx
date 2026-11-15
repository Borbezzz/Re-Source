import { useRef, useState } from "react";
import { PreparedAssembly } from "./PreparedAssembly.tsx";
import { ArrowDown, ArrowUpRight, FileUp, Play } from "lucide-react";
import type { EngineView } from "../api/types.ts";
import VectorWordmark from "../brand/VectorWordmark.tsx";
import { EngineIntro } from "../scene/EngineIntro.tsx";
import PatternWaves from "../theme/PatternWaves.tsx";

export function ProductHome({
  engine,
  onSources,
  onPart,
  connectionFailed,
  onRetry,
  onStartDemo,
}: {
  engine: EngineView | null;
  onSources: () => void;
  onPart: (id: string) => void;
  connectionFailed: boolean;
  onRetry: () => void;
  onStartDemo?: () => void;
}) {
  const [engineDemo, setEngineDemo] = useState(location.hash === "#engine");
  const heroRef = useRef<HTMLElement>(null);
  const openEngineDemo = () => {
    setEngineDemo(true);
    history.replaceState(null, "", "#engine");
    window.scrollTo(0, 0);
  };
  if (engineDemo)
    return (
      <div className="prepared-entry">
        <button
          className="text-button"
          onClick={() => {
            setEngineDemo(false);
            history.replaceState(null, "", location.pathname);
          }}
        >
          Back to product explorer
        </button>
        <EngineIntro
          engine={engine}
          onSources={onSources}
          onPart={onPart}
          connectionFailed={connectionFailed}
          onRetry={onRetry}
        />
      </div>
    );
  return (
    <main className="product-home">
      <section
        ref={heroRef}
        className="product-entry"
        aria-labelledby="product-title"
      >
        <div className="entry-wave-field" aria-hidden="true">
          <PatternWaves
            preset="silk"
            color="#ffffff"
            backgroundColor="#000000"
            fade="edges"
            interactive
            cursorSize={50}
            cursorStrength={1}
          />
        </div>
        <div className="entry-wordmark">
          <h1 id="product-title" className="sr-only">
            Re::Source
          </h1>
          <VectorWordmark
            interactionRef={heroRef}
            text="Re::Source"
            background="transparent"
            textColor="#ffffff"
            shade="#bdc6d4"
            accent="#82a9ffcc"
            glass
            font={{
              fontFamily: "Geist Variable",
              fontWeight: 650,
              fontSize: 210,
              letterSpacing: "-0.035em",
            }}
            handles={{ size: 55, spread: 23, labels: true }}
            style={{ position: "absolute", inset: 0 }}
          />
        </div>
        <div className="entry-actions">
          <h2>From a product’s parts to the people who can supply them.</h2>
          <p>Start with a blueprint. Explore every part. Find its source.</p>
          <div className="entry-cta-group">
            <button
              className="primary entry-demo"
              onClick={onStartDemo ?? openEngineDemo}
            >
              <Play size={15} fill="currentColor" /> Start demo{" "}
              <ArrowUpRight size={17} />
            </button>
            <button className="secondary entry-upload" onClick={onSources}>
              <FileUp size={17} /> Upload blueprint
            </button>
          </div>
          <p className="entry-scope">
            Choose a prepared product, or bring your own blueprint.
          </p>
        </div>
        <a className="entry-explore" href="#prepared-assembly">
          Explore a prepared assembly <ArrowDown size={15} />
        </a>
      </section>
      <PreparedAssembly onEngine={onStartDemo ?? openEngineDemo} />
    </main>
  );
}
