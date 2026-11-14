import { useState } from "react";
import { PreparedAssembly } from "./PreparedAssembly.tsx";
import { ArrowDown, ArrowUpRight, FileUp } from "lucide-react";
import type { EngineView } from "../api/types.ts";
import VectorWordmark from "../brand/VectorWordmark.tsx";
import { EngineIntro } from "../scene/EngineIntro.tsx";

export function ProductHome({
  engine,
  onSources,
  onPart,
  connectionFailed,
  onRetry,
}: {
  engine: EngineView | null;
  onSources: () => void;
  onPart: (id: string) => void;
  connectionFailed: boolean;
  onRetry: () => void;
}) {
  const [engineDemo, setEngineDemo] = useState(location.hash === "#engine");
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
      <section className="product-entry" aria-labelledby="product-title">
        <div className="entry-wordmark">
          <h1 id="product-title" className="sr-only">
            ReSource
          </h1>
          <VectorWordmark
            text="ReSource"
            background="#f2f3f5"
            textColor="#17191d"
            shade="#373e49"
            accent="#2251ef99"
            font={{
              fontFamily: "Geist Variable",
              fontWeight: 650,
              fontSize: 235,
              letterSpacing: "-0.035em",
            }}
            handles={{ size: 55, spread: 23, labels: true }}
            style={{ position: "absolute", inset: 0 }}
          />
          <p>From a product’s parts to the people who can supply them.</p>
        </div>
        <div className="entry-actions">
          <h2>Start with what you know.</h2>
          <p>A blueprint. A specification. A part that needs a source.</p>
          <button className="primary" onClick={onSources}>
            <FileUp size={17} /> Upload blueprint <ArrowUpRight size={17} />
          </button>
          <a href="#prepared-assembly">
            Explore a prepared assembly <ArrowDown size={16} />
          </a>
          <p className="entry-scope">
            Source uploads currently use the engine demo.
          </p>
        </div>
      </section>
      <PreparedAssembly
        onEngine={() => {
          setEngineDemo(true);
          history.replaceState(null, "", "#engine");
          window.scrollTo(0, 0);
        }}
      />
    </main>
  );
}
