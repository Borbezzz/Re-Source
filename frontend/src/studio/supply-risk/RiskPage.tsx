import { useEffect, useRef, useState } from "react";
import type { ProductProject } from "../../product-flow/types.ts";
import { journeyApi } from "../api.ts";
import { riskApi } from "./client.ts";
import { NeedsForm } from "./NeedsForm.tsx";
import { RiskOverview, RiskPanel } from "./RiskPanel.tsx";
import type { NeedsDraft, RiskEvidence, RiskScan } from "./types.ts";
import "../studio.css";

export function RiskPage({ projectId }: { projectId: string }) {
  return <ProjectRiskPage key={projectId} projectId={projectId} />;
}

function ProjectRiskPage({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<ProductProject | null>(null);
  const [scan, setScan] = useState<RiskScan | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [needsProject, setNeedsProject] = useState<ProductProject | null>(null);
  const needsLocked = useRef(false);
  const needsRequest = useRef(0);
  const initialized = useRef(false);
  const activePage = useRef(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const accept = (next: RiskScan) => {
    if (!activePage.current || next.project_id !== projectId) return;
    setScan((old) => old && (
      old.project_version > next.project_version ||
      (old.project_version === next.project_version && old.version > next.version)
    ) ? old : next);
  };
  useEffect(() => {
    let active = true;
    activePage.current = true;
    const load = async () => {
      try {
        const [p, s] = await Promise.all([journeyApi.project(projectId), riskApi.get(projectId)]);
        if (active) {
          setProject((old) => old && old.version > p.version ? old : p);
          accept(s);
          if (!initialized.current) {
            initialized.current = true;
            if (s.status === "not_started" && !needsLocked.current) {
              needsLocked.current = true;
              setNeedsProject(p);
            }
          }
        }
      } catch (e) { if (active) setError(e instanceof Error ? e.message : "Could not open this saved scan."); }
    };
    void load();
    const timer = setInterval(() => { if (document.visibilityState === "visible") void load(); }, 20000);
    window.addEventListener("focus", load);
    return () => {
      active = false;
      activePage.current = false;
      needsRequest.current++;
      clearInterval(timer);
      window.removeEventListener("focus", load);
    };
  }, [projectId]);
  const closeNeeds = () => {
    needsRequest.current++;
    needsLocked.current = false;
    setNeedsProject(null);
    setEditing(false);
  };
  const openNeeds = async () => {
    if (needsLocked.current) return;
    needsLocked.current = true;
    const request = ++needsRequest.current;
    const current = () => activePage.current && request === needsRequest.current;
    setError(null);
    try {
      const fresh = await journeyApi.project(projectId);
      if (!current()) return;
      if (fresh.project_id !== projectId) throw new Error("Could not open this project's needs. Try again.");
      setNeedsProject(fresh);
      setEditing(true);
    } catch (e) {
      if (!current()) return;
      needsLocked.current = false;
      setError(e instanceof Error ? e.message : "Could not load current project needs. Try again.");
    }
  };
  const refresh = async () => {
    setBusy(true); setError(null);
    try { accept(await riskApi.refresh(projectId)); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not refresh sources."); }
    finally { setBusy(false); }
  };
  const confirm = async (draft: NeedsDraft) => {
    if (!needsProject) return;
    const request = needsRequest.current;
    const current = () => activePage.current && request === needsRequest.current;
    setBusy(true); setError(null);
    try {
      const reviewed = await journeyApi.confirmParts(needsProject, draft);
      if (!current()) return;
      setProject((old) => old && old.version > reviewed.version ? old : reviewed);
      const confirmed = await riskApi.confirm(projectId, reviewed.version, draft.parts.map((p) => ({ part_id: p.part_id, quantity: p.quantity, destination: draft.destination, need_by: draft.need_by })));
      if (!current()) return;
      accept(confirmed);
      closeNeeds();
      await refresh();
    } catch (e) { if (current()) setError(e instanceof Error ? e.message : "Confirmation failed. Your edits are still here."); }
    finally { if (activePage.current) setBusy(false); }
  };
  const save = async (evidence: RiskEvidence) => {
    if (!scan) return;
    setBusy(true);
    try { accept(await riskApi.evidence(projectId, scan.version, evidence)); }
    finally { setBusy(false); }
  };
  const part = scan?.parts.find((p) => p.part_id === selected);
  return <div className="rs-studio rs-risk-page">
    <header className="rs-risk-page-header"><div><a href={`#project/${projectId}`}>Back to investigation</a><h1>{project?.name ?? "Saved project"} · Supply risk</h1></div><a className="rs-btn" href={`#quotes/${projectId}`}>Supplier quotes</a></header>
    {!scan || !project ? <p className="rs-risk-page-loading" role={error ? "alert" : "status"}>{error ?? "Opening the saved supply-risk scan…"}</p> : needsProject ? <main className="rs-risk-page-needs rs-panel">
      {editing ? <button className="rs-btn rs-btn-sm" disabled={busy} onClick={closeNeeds}>Back to scan</button> : null}
      <NeedsForm project={needsProject} scan={scan.status === "not_started" ? null : scan} busy={busy} onConfirm={(draft) => void confirm(draft)} />
      {error ? <p role="alert" className="rs-risk-error">{error}</p> : null}
    </main> : <main className={`rs-risk-page-grid${part ? " has-selection" : ""}`}>
      <RiskOverview scan={scan} busy={busy} error={error} onSelect={setSelected} onRefresh={() => void refresh()} onEdit={() => void openNeeds()} />
      {part ? <RiskPanel key={part.part_id} part={part} scan={scan} busy={busy} error={error} onClose={() => setSelected(null)} onFind={() => { location.hash = `#project/${projectId}`; }} onSave={save} onRefresh={() => void refresh()} onEdit={() => void openNeeds()} /> : <div className="rs-risk-page-empty"><h2>Select a part to inspect its delivery evidence.</h2><p>Quotes and receipts stay with the project. Reopening this scan evaluates the latest evidence against the confirmed deadline.</p></div>}
    </main>}
  </div>;
}
