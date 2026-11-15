import { useRef, useState } from "react";
import { motion } from "motion/react";
import { ArrowRight, FilePlus2 } from "lucide-react";

export function Intake({ onFiles, onSample, error }: { onFiles: (files: File[]) => void; onSample: () => void; error: string | null }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const folderRef = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const take = (list: FileList | null) => {
    const files = list ? [...list] : [];
    if (files.length) onFiles(files);
  };
  return (
    <motion.main
      className="rs-intake"
      id="main-content"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="rs-intake-inner">
        <motion.div className="rs-intake-title" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}>
          <span className="rs-eyebrow">Workspace / New assembly</span>
          <h1 className="rs-h1">
            Start with your <span className="rs-grad-text">design files.</span>
          </h1>
          <p className="rs-lede">Add an assembly and its supporting documents.</p>
        </motion.div>

        <motion.div
          className={`rs-drop${over ? " is-over" : ""}`}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.18, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          onDragOver={(e) => {
            e.preventDefault();
            setOver(true);
          }}
          onDragLeave={() => setOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setOver(false);
            take(e.dataTransfer.files);
          }}
        >
          <span className="rs-drop-icon" aria-hidden="true">
            <FilePlus2 size={34} strokeWidth={1.4} />
          </span>
          <span className="rs-drop-copy">
            <strong>Add design package</strong>
            <span>CAD assembly or prepared model, parts list and specifications</span>
          </span>
          <button type="button" className="rs-btn rs-btn-solid" onClick={() => fileRef.current?.click()}>
            Choose files
          </button>
          <input
            ref={fileRef}
            type="file"
            multiple
            accept=".zip,.glb,.json,.csv,.md,.txt"
            hidden
            onChange={(e) => take(e.target.files)}
          />
          <input
            ref={folderRef}
            type="file"
            hidden
            multiple
            {...({ webkitdirectory: "" } as Record<string, string>)}
            onChange={(e) => take(e.target.files)}
          />
        </motion.div>

        <motion.p className="rs-intake-help" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3, duration: 0.6 }}>
          Drop files here, or choose a <button type="button" onClick={() => folderRef.current?.click()}>folder</button>.
          <br />
          Your documents stay together as one assembly. We only ask about missing essentials.
        </motion.p>

        {error ? (
          <p className="rs-intake-error" role="alert">
            {error}
          </p>
        ) : null}

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4, duration: 0.6 }} style={{ marginTop: 18 }}>
          <button type="button" className="rs-link" onClick={onSample}>
            Explore a sample assembly <ArrowRight size={18} strokeWidth={1.6} />
          </button>
          <div className="rs-tiny" style={{ marginTop: 6 }}>Prepared Mechanica turbofan package · fictional demo data</div>
        </motion.div>
      </div>
    </motion.main>
  );
}
