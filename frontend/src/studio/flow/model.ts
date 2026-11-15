/**
 * Live agent-workflow graph for the sourcing run (n8n-style).
 *
 * The graph is a pure projection of Studio state: every node status is derived
 * from what the demo has actually done (research returned, a candidate's checks
 * landed, the user approved, the simulated supplier replied). Nothing here
 * advances on its own timer.
 */
import { CHECK_ORDER, type Assessed, type CheckStatus, type SourcingNeed } from "../data/checks.ts";
import { DISRUPTION } from "../data/sites.ts";
import type { ProcurementStep } from "../screens/Fulfilment.tsx";
import type { ReassemblyPhase } from "../scene/EngineCanvas.tsx";
import { workflowProviders, type ProviderProject } from "./providers.ts";

export type FlowStage = "intake" | "processing" | "explore" | "need" | "discovery" | "checking" | "shortlist" | "fulfil" | "return";
export const FLOW_STAGES: FlowStage[] = ["discovery", "checking", "shortlist", "fulfil", "return"];

export interface FlowSnapshot {
  stage: FlowStage;
  part: { name: string; partNumber: string; revision: string } | null;
  need: SourcingNeed;
  assessed: Assessed[];
  checked: Set<string>;
  progress: Record<string, number>;
  disrupted: boolean;
  recheck: "idle" | "running" | "done";
  procure: ProcurementStep;
  chosenId: string | null;
  phase: ReassemblyPhase;
  busy: string | null;
  error: string | null;
  project?: ProviderProject | null;
  partId?: string | null;
}

export type NodeStatus = "idle" | "running" | "waiting" | "done" | "alert" | "skipped" | "error";
export type NodeKind = "trigger" | "action" | "router" | "human" | "monitor" | "end" | "candidate";
export type IconName =
  | "zap" | "radar" | "split" | "trophy" | "evidence" | "ban" | "activity" | "recheck"
  | "user" | "doc" | "stamp" | "send" | "mail" | "box";

export interface FlowNode {
  id: string;
  kind: NodeKind;
  x: number;
  y: number;
  title: string;
  railLabel?: string;
  icon: IconName;
  status: NodeStatus;
  /** One-line live status under the title. */
  sub: string;
  /** Short, human-readable lines for the inspector ("output" pane). */
  detail: { k: string; v: string; tone?: "ok" | "wait" | "bad" }[];
  /** Log line written when the node reaches its current status. */
  log?: string;
  simulated?: boolean;
  stub?: boolean; // draws an n8n-style "+" after a terminal node
  candidate?: {
    id: string;
    name: string;
    city: string;
    countryCode: string;
    rank: number | null;
    state: Assessed["state"] | "queued";
    pips: (CheckStatus | "pending" | "running")[];
  };
}

export interface FlowEdge {
  id: string;
  from: string;
  to: string;
  /** Output handle label (router branches). */
  label?: string;
  /** Item count shown on the edge once data has passed. */
  items?: number;
  fromOffset?: number; // vertical handle offset on the source
  loop?: boolean; // drawn top→top as a feedback arc
  state: "idle" | "active" | "done";
}

export const NODE = 84; // square node size
export const PILL_W = 216;
export const PILL_H = 38;
const COL = 210;
const PILL_GAP = 42;

const PROCURE_ORDER: ProcurementStep[] = ["prepared", "approved", "sent", "acknowledged", "confirmed"];
const after = (stage: FlowStage, ...list: FlowStage[]) => list.includes(stage);

export function buildGraph(s: FlowSnapshot): { nodes: FlowNode[]; edges: FlowEdge[] } {
  const nodes: FlowNode[] = [];
  const edges: FlowEdge[] = [];
  const n = s.assessed.length;
  const allChecked = n > 0 && s.assessed.every((a) => s.checked.has(a.candidate.candidate_id));
  const pastChecks = after(s.stage, "shortlist", "fulfil", "return");
  const classified = allChecked || pastChecks;
  const eligible = s.assessed.filter((a) => a.state === "eligible");
  const awaiting = s.assessed.filter((a) => a.state === "awaiting");
  const excluded = s.assessed.filter((a) => a.state === "excluded");
  const ranked = s.assessed.filter((a) => a.rank != null).sort((a, b) => a.rank! - b.rank!);
  const chosen = s.assessed.find((a) => a.candidate.candidate_id === s.chosenId) ?? null;
  const pIdx = PROCURE_ORDER.indexOf(s.procure);
  const inFulfil = after(s.stage, "fulfil", "return");
  const part = s.part;
  const provider = workflowProviders(s.project, s.partId);

  // ---- 0 · trigger ----
  nodes.push({
    id: "trigger",
    kind: "trigger",
    x: 0,
    y: 0,
    title: provider.lakebase ? "Lakebase · Save case" : "Save sourcing case",
    railLabel: provider.lakebase ? "Databricks Lakebase" : "Save case",
    icon: "zap",
    status: "done",
    sub: provider.storage,
    detail: [
      { k: "Case store", v: provider.storage },
      { k: "Saved", v: "Confirmed parts, supplier results, selections and approval history" },
      { k: "Job runner", v: provider.execution },
      { k: "Document AI", v: "Databricks ai_parse_document · document text and layout extraction" },
      { k: "This intake", v: provider.parsing },
      ...(part ? [
          { k: "Part", v: part.name },
          { k: "Number", v: `${part.partNumber} · Rev ${part.revision}` },
          { k: "Quantity", v: String(s.need.quantity) },
          { k: "Required by", v: s.need.requiredBy },
          { k: "Deliver to", v: s.need.destination },
          { k: "Reason", v: s.need.reason === "faulty" ? "Replace faulty part" : "Change supplier" },
        ] : []),
    ],
    log: part ? `Triggered for ${part.partNumber} Rev ${part.revision} · qty ${s.need.quantity}` : "Triggered",
  });

  // ---- 1 · discover ----
  const discovering = s.stage === "discovery" && n === 0;
  nodes.push({
    id: "discover",
    kind: "action",
    x: COL,
    y: 0,
    title: "Linkup · Web Search",
    icon: "radar",
    status: provider.searchStatus,
    sub: provider.searchSummary,
    detail: [
      { k: "Feature", v: "Linkup Search · standard search with source URLs" },
      { k: "This run", v: provider.demo ? "Prepared demo offers; Linkup was not called" : provider.searchSummary },
      { k: "Input", v: "Confirmed part number, revision and requirements" },
      { k: "Output", v: provider.demo ? "Prepared supplier names, offers and site locations" : "Supplier page titles, snippets and citations" },
      { k: "Coverage", v: "UK & EU stockists, distributors, build-to-print" },
      { k: "Sites found", v: discovering ? "—" : String(n) },
      { k: "Pins", v: "Stock, production or dispatch sites" },
    ],
    log: provider.demo ? "Linkup Search skipped · using prepared supplier offers" : provider.searchSummary,
  });
  edges.push({ id: "e-trigger-discover", from: "trigger", to: "discover", state: discovering ? "active" : "done", items: 1 });

  nodes.push({
    id: "extract", kind: "action", x: COL * 2, y: 0,
    title: "Databricks · ai_extract", icon: "evidence",
    status: provider.extractStatus, sub: provider.extractSummary,
    detail: [
      { k: "Feature", v: "Databricks AI Functions · ai_extract on a SQL warehouse" },
      { k: "This run", v: provider.demo ? "Prepared demo claims; ai_extract was not called" : provider.extractSummary },
      { k: "Input", v: "Cited supplier snippets returned by Linkup" },
      { k: "Fields", v: "Supplier name, country, materials and certification claims" },
      { k: "Evidence", v: provider.demo ? "Fixture evidence drives this demo's checks" : "Extracted claims remain unverified; source citations are retained" },
      { k: "Fallback", v: "If extraction is unavailable, keep the original source snippets" },
    ],
    log: provider.demo ? "Databricks ai_extract skipped · using prepared claims" : provider.extractSummary,
  });
  edges.push({ id: "e-discover-extract", from: "discover", to: "extract", state: provider.extractStatus === "running" ? "active" : discovering ? "idle" : "done" });

  // ---- 2 · per-candidate qualification column ----
  const colX = COL * 3 + 60;
  s.assessed.forEach((a, i) => {
    const id = a.candidate.candidate_id;
    const done = s.checked.has(id) || pastChecks;
    const prog = done ? CHECK_ORDER.length : (s.progress[id] ?? 0);
    const running = !done && prog > 0;
    const affected = s.disrupted && DISRUPTION.affects(id);
    const rechecking = affected && s.recheck === "running";
    const pips = CHECK_ORDER.map((cid, ci) => {
      const check = a.checks.find((c) => c.id === cid);
      if (rechecking && (DISRUPTION.rerun as readonly string[]).includes(cid)) return "running" as const;
      if (ci < prog) return check?.status ?? "pending";
      if (running && ci === prog) return "running" as const;
      return "pending" as const;
    });
    const status: NodeStatus = rechecking ? "running" : done ? "done" : running ? "running" : "idle";
    nodes.push({
      id: `cand:${id}`,
      kind: "candidate",
      x: colX,
      y: (i - (n - 1) / 2) * PILL_GAP,
      title: a.candidate.supplier_name,
      icon: "box",
      status,
      sub: done ? a.reason : running ? `Check ${prog}/${CHECK_ORDER.length}` : "Queued",
      detail: [
        { k: "Checks", v: "Re::Source rules · prepared site evidence" },
        { k: "Site", v: `${a.site.siteType} · ${a.site.city}` },
        { k: "Source", v: a.site.sourceLabel },
        ...a.checks.map((c) => ({
          k: c.label,
          v: done || CHECK_ORDER.indexOf(c.id) < prog ? c.note : "Pending",
          tone: !(done || CHECK_ORDER.indexOf(c.id) < prog) ? undefined : c.status === "pass" ? ("ok" as const) : c.status === "fail" ? ("bad" as const) : c.status === "unknown" ? ("wait" as const) : undefined,
        })),
      ],
      log: done ? `${a.candidate.supplier_name} → ${a.state}${a.state !== "eligible" ? ` · ${a.reason}` : ""}` : running ? `Checking ${a.candidate.supplier_name}, ${a.site.city}` : undefined,
      candidate: {
        id,
        name: a.candidate.supplier_name,
        city: a.site.city,
        countryCode: a.site.countryCode,
        rank: a.rank,
        state: done ? a.state : "queued",
        pips,
      },
    });
    edges.push({ id: `e-extract-${id}`, from: "extract", to: `cand:${id}`, state: running ? "active" : done ? "done" : discovering ? "idle" : "done" });
    edges.push({ id: `e-${id}-router`, from: `cand:${id}`, to: "router", state: done ? (classified ? "done" : "active") : "idle" });
  });

  // ---- 3 · router ----
  const routerX = colX + PILL_W / 2 + 170;
  const checkedCount = s.assessed.filter((a) => s.checked.has(a.candidate.candidate_id)).length;
  nodes.push({
    id: "router",
    kind: "router",
    x: routerX,
    y: 0,
    title: "Classify",
    icon: "split",
    status: classified ? "done" : s.stage === "checking" ? "running" : "idle",
    sub: classified ? `${eligible.length} · ${awaiting.length} · ${excluded.length}` : s.stage === "checking" ? `${checkedCount}/${n} qualified` : "Waiting for checks",
    detail: [
      { k: "Engine", v: "Re::Source eligibility rules" },
      { k: "Hard failure", v: "Excluded with reason" },
      { k: "Missing mandatory evidence", v: "Awaiting verification" },
      { k: "Eligible", v: String(eligible.length), tone: "ok" },
      { k: "Awaiting evidence", v: String(awaiting.length), tone: "wait" },
      { k: "Excluded", v: String(excluded.length), tone: "bad" },
    ],
    log: classified ? `Classified ${n}: ${eligible.length} eligible, ${awaiting.length} awaiting, ${excluded.length} excluded` : undefined,
  });

  // ---- 4 · branches ----
  const brX = routerX + COL + 20;
  const rankRunning = s.recheck === "running";
  nodes.push({
    id: "rank",
    kind: "action",
    x: brX,
    y: 0,
    title: "Rank shortlist",
    icon: "trophy",
    status: !classified ? "idle" : rankRunning ? "running" : "done",
    sub: !classified ? "—" : rankRunning ? "Re-ranking…" : ranked[0] ? `#1 ${ranked[0].candidate.supplier_name}` : "No eligible sites",
    detail: [
      { k: "Engine", v: "Re::Source weighted scoring" },
      { k: "Weights", v: "Delivery 50% · cost 35% · evidence 15%" },
      ...ranked.map((a) => ({ k: `#${a.rank} ${a.candidate.supplier_name}`, v: `${a.site.city} · score ${a.score}`, tone: "ok" as const })),
    ],
    log: classified && !rankRunning && ranked[0] ? `Recommended ${ranked[0].candidate.supplier_name} (${ranked[0].site.city})` : undefined,
  });
  nodes.push({
    id: "evidence",
    kind: "action",
    x: brX,
    y: 150,
    title: "Request evidence",
    icon: "evidence",
    status: !classified ? "idle" : awaiting.length ? "done" : "skipped",
    sub: !classified ? "—" : awaiting.length ? `${awaiting.length} awaiting verification` : "Nothing to request",
    detail: awaiting.map((a) => ({ k: a.candidate.supplier_name, v: a.reason, tone: "wait" as const })),
    log: classified && awaiting.length ? `Evidence requests queued for ${awaiting.length} sites` : undefined,
    stub: true,
  });
  nodes.push({
    id: "excluded",
    kind: "end",
    x: brX,
    y: 290,
    title: "Excluded · logged",
    icon: "ban",
    status: !classified ? "idle" : excluded.length ? "done" : "skipped",
    sub: !classified ? "—" : `${excluded.length} with reasons`,
    detail: excluded.map((a) => ({ k: a.candidate.supplier_name, v: a.reason, tone: "bad" as const })),
    stub: true,
  });
  const routeState = (count: number): FlowEdge["state"] => (classified ? (count ? "done" : "idle") : s.stage === "checking" ? "idle" : "idle");
  edges.push({ id: "e-router-rank", from: "router", to: "rank", fromOffset: -22, label: "eligible", items: classified ? eligible.length : undefined, state: rankRunning ? "active" : routeState(eligible.length) });
  edges.push({ id: "e-router-evidence", from: "router", to: "evidence", fromOffset: 0, label: "awaiting", items: classified ? awaiting.length : undefined, state: routeState(awaiting.length) });
  edges.push({ id: "e-router-excluded", from: "router", to: "excluded", fromOffset: 22, label: "excluded", items: classified ? excluded.length : undefined, state: routeState(excluded.length) });

  // ---- 5 · disruption monitor + selective recheck loop ----
  const monX = brX + COL;
  const monitoring = s.stage === "shortlist" || inFulfil;
  const affected = s.assessed.find((a) => DISRUPTION.affects(a.candidate.candidate_id)) ?? null;
  nodes.push({
    id: "monitor",
    kind: "monitor",
    x: monX,
    y: 0,
    title: "Disruption watch",
    icon: "activity",
    status: !monitoring ? "idle" : s.disrupted && s.recheck !== "done" ? "alert" : s.disrupted ? "done" : "running",
    sub: !monitoring ? "Demo signal replay" : s.disrupted ? (s.recheck === "done" ? "Signal handled" : DISRUPTION.title) : "Ready for demo signal",
    detail: s.disrupted
      ? [
          { k: "Mode", v: "Prepared disruption replay · no live web monitoring" },
          { k: "Signal", v: DISRUPTION.id },
          { k: "Source", v: DISRUPTION.source },
          { k: "Event", v: DISRUPTION.detail, tone: "bad" },
          { k: "Affected", v: affected ? `${affected.candidate.supplier_name} · ${affected.site.city}` : "None in shortlist" },
        ]
      : [{ k: "Mode", v: "Prepared disruption replay · no live web monitoring" }, { k: "Signals", v: "Supplier notices, route and stock changes" }],
    log: s.disrupted ? `Demo signal ${DISRUPTION.id}: ${DISRUPTION.title}` : monitoring ? "Ready to replay a demo disruption" : undefined,
  });
  nodes.push({
    id: "recheck",
    kind: "action",
    x: monX,
    y: -180,
    title: "Selective recheck",
    icon: "recheck",
    status: s.recheck === "running" ? "running" : s.recheck === "done" ? "done" : "idle",
    sub: s.recheck === "idle" ? "Only on disruption" : s.recheck === "running" ? "Availability · arrival" : "Ranking revised",
    detail: [
      { k: "Re-run", v: "Availability, arrival feasibility" },
      { k: "Kept", v: "Unaffected evidence and earlier comparison" },
      ...(s.recheck === "done" && ranked[0] ? [{ k: "New #1", v: `${ranked[0].candidate.supplier_name} · ${ranked[0].site.city}`, tone: "ok" as const }] : []),
    ],
    log: s.recheck === "running" ? "Re-running availability and arrival for affected site" : s.recheck === "done" ? `Ranking revised${ranked[0] ? ` · new #1 ${ranked[0].candidate.supplier_name}` : ""}` : undefined,
  });
  edges.push({ id: "e-rank-monitor", from: "rank", to: "monitor", items: ranked.length || undefined, state: monitoring ? "done" : "idle" });
  edges.push({ id: "e-monitor-recheck", from: "monitor", to: "recheck", label: "signal", state: s.recheck === "running" ? "active" : s.recheck === "done" ? "done" : "idle", loop: false });
  edges.push({ id: "e-recheck-rank", from: "recheck", to: "rank", loop: true, state: s.recheck === "running" ? "active" : s.recheck === "done" ? "done" : "idle" });

  // ---- 6 · human selection → RFQ → approval → send → reply → reassembly ----
  let x = monX + COL;
  const choose: NodeStatus = inFulfil ? "done" : s.stage === "shortlist" ? (s.busy === "select" ? "running" : s.recheck === "running" ? "idle" : "waiting") : "idle";
  nodes.push({
    id: "choose",
    kind: "human",
    x,
    y: 0,
    title: "Choose supplier",
    icon: "user",
    status: choose,
    sub: choose === "waiting" ? "Waiting for you" : chosen ? chosen.candidate.supplier_name : "Human decision",
    detail: chosen
      ? [
          { k: "Selected", v: chosen.candidate.supplier_name, tone: "ok" },
          { k: "Site", v: `${chosen.site.siteType} · ${chosen.site.city}` },
        ]
      : [{ k: "Decision", v: "Buyer picks from the ranked shortlist" }],
    log: choose === "waiting" ? "Waiting for buyer to choose a supplier" : chosen && inFulfil ? `Buyer selected ${chosen.candidate.supplier_name}` : undefined,
  });
  edges.push({ id: "e-monitor-choose", from: "monitor", to: "choose", label: s.disrupted ? "resolved" : "clear", state: choose === "waiting" || choose === "running" ? "active" : inFulfil ? "done" : "idle" });

  x += COL;
  nodes.push({
    id: "rfq",
    kind: "action",
    x,
    y: 0,
    title: "Draft RFQ",
    icon: "doc",
    status: inFulfil ? "done" : s.busy === "select" ? "running" : "idle",
    sub: inFulfil ? "Enquiry prepared" : "—",
    detail: [{ k: "Drafting", v: "Re::Source RFQ template · reviewed requirements" }, { k: "Case store", v: provider.storage }, ...(part ? [{ k: "Item", v: `${part.partNumber} Rev ${part.revision} × ${s.need.quantity}` }, { k: "Required by", v: s.need.requiredBy }, { k: "Deliver to", v: s.need.destination }] : [])],
    log: inFulfil ? "RFQ drafted for review" : undefined,
  });
  edges.push({ id: "e-choose-rfq", from: "choose", to: "rfq", items: inFulfil ? 1 : undefined, state: s.busy === "select" ? "active" : inFulfil ? "done" : "idle" });

  x += COL;
  const approved = inFulfil && pIdx >= 1;
  const approve: NodeStatus = approved ? "done" : s.stage === "fulfil" ? (s.busy === "approve" ? "running" : "waiting") : "idle";
  nodes.push({
    id: "approve",
    kind: "human",
    x,
    y: 0,
    title: "Approve RFQ",
    icon: "stamp",
    status: approve,
    sub: approve === "waiting" ? "Waiting for you" : approved ? "Approved by buyer" : "Human approval",
    detail: [{ k: "Gate", v: "Nothing leaves without buyer approval" }, { k: "Approval store", v: provider.storage }, { k: "Record", v: "Approval is tied to this exact RFQ package" }],
    log: approve === "waiting" ? "Waiting for buyer approval" : approved ? "RFQ approved" : undefined,
  });
  edges.push({ id: "e-rfq-approve", from: "rfq", to: "approve", state: approve === "waiting" || approve === "running" ? "active" : approved ? "done" : "idle" });

  x += COL;
  const sent = inFulfil && pIdx >= 2;
  nodes.push({
    id: "send",
    kind: "action",
    x,
    y: 0,
    title: "Send to supplier",
    icon: "send",
    simulated: true,
    status: sent ? "done" : s.busy === "send" ? "running" : approved && s.stage === "fulfil" ? "waiting" : "idle",
    sub: sent ? "Delivered · simulated" : approved && s.stage === "fulfil" ? "Waiting for you" : "Simulated outbound",
    detail: [{ k: "Channel", v: "Demo mailbox · external message simulated" }, ...(chosen ? [{ k: "To", v: chosen.candidate.supplier_name }] : [])],
    log: sent ? `Enquiry sent to ${chosen?.candidate.supplier_name ?? "supplier"} (simulated)` : undefined,
  });
  edges.push({ id: "e-approve-send", from: "approve", to: "send", state: s.busy === "send" && !sent ? "active" : sent ? "done" : "idle" });

  x += COL;
  const replyStatus: NodeStatus = !sent ? "idle" : s.procure === "confirmed" ? "done" : "running";
  nodes.push({
    id: "reply",
    kind: "action",
    x,
    y: 0,
    title: "Supplier reply",
    icon: "mail",
    simulated: true,
    status: replyStatus,
    sub: s.procure === "confirmed" ? "Order confirmed" : s.procure === "acknowledged" ? "Acknowledged…" : sent ? "Awaiting reply…" : "—",
    detail: [
      { k: "Acknowledged", v: pIdx >= 3 ? "Yes · simulated" : "—", tone: pIdx >= 3 ? "ok" : undefined },
      { k: "Confirmed", v: pIdx >= 4 ? "Yes · simulated" : "—", tone: pIdx >= 4 ? "ok" : undefined },
    ],
    log: s.procure === "acknowledged" ? "Supplier acknowledged (simulated)" : s.procure === "confirmed" ? "Order confirmed (simulated)" : undefined,
  });
  edges.push({ id: "e-send-reply", from: "send", to: "reply", state: replyStatus === "running" ? "active" : replyStatus === "done" ? "done" : "idle" });

  x += COL;
  const re: NodeStatus = s.stage === "return" ? (s.phase === "done" ? "done" : "running") : s.stage === "fulfil" && s.procure === "confirmed" ? "waiting" : "idle";
  nodes.push({
    id: "reassemble",
    kind: "end",
    x,
    y: 0,
    title: "Reassembly preview",
    icon: "box",
    status: re,
    sub: re === "done" ? "Part seated · preview" : re === "running" ? (s.phase === "remove" ? "Removing faulty part…" : "Inserting replacement…") : re === "waiting" ? "Waiting for you" : "—",
    detail: [{ k: "Note", v: "Preview only — not proof of physical fit or airworthiness" }],
    log: re === "done" ? "Reassembly preview complete" : re === "running" ? "Reassembly preview started" : undefined,
    stub: true,
  });
  edges.push({ id: "e-reply-reassemble", from: "reply", to: "reassemble", state: re === "running" ? "active" : re === "done" ? "done" : s.procure === "confirmed" ? "done" : "idle" });

  return { nodes, edges };
}

// ---------------------------------------------------------------- steps
// The trunk of the run as the step rail and the output pane read it. "qualify"
// is a virtual step: the per-candidate column taken as one stage.

export const STEPS: { id: string; label: string }[] = [
  { id: "trigger", label: "Save case" },
  { id: "discover", label: "Linkup Search" },
  { id: "extract", label: "Databricks ai_extract" },
  { id: "qualify", label: "Re::Source checks" },
  { id: "router", label: "Classify" },
  { id: "rank", label: "Rank" },
  { id: "monitor", label: "Watch" },
  { id: "choose", label: "Choose" },
  { id: "rfq", label: "RFQ" },
  { id: "approve", label: "Approve" },
  { id: "send", label: "Send" },
  { id: "reply", label: "Reply" },
  { id: "reassemble", label: "Reassemble" },
];

export function qualifyStatus(nodes: FlowNode[]): NodeStatus {
  const c = nodes.filter((n) => n.kind === "candidate");
  if (!c.length) return "idle";
  if (c.some((n) => n.status === "running")) return "running";
  if (c.every((n) => n.status === "done" || n.status === "alert")) return "done";
  return c.some((n) => n.status === "done") ? "running" : "idle";
}

export function stepStatus(id: string, nodes: FlowNode[]): NodeStatus {
  if (id === "qualify") return qualifyStatus(nodes);
  return nodes.find((n) => n.id === id)?.status ?? "idle";
}

/** The step the run is on right now: alert > running > waiting for a human > last finished. */
export function liveStep(nodes: FlowNode[]): string {
  const st = (id: string) => stepStatus(id, nodes);
  const bad = nodes.find((n) => n.kind !== "candidate" && (n.status === "error" || n.status === "alert"));
  if (st("recheck") === "running") return "recheck";
  if (bad) return bad.id;
  if (st("qualify") === "running") return "qualify";
  const trunk = STEPS.map((s) => s.id).filter((id) => id !== "monitor");
  const running = trunk.find((id) => st(id) === "running");
  if (running) return running;
  const waiting = trunk.find((id) => st(id) === "waiting");
  if (waiting) return waiting;
  const done = [...STEPS].reverse().find((s) => st(s.id) === "done");
  return done?.id ?? "trigger";
}

/** Node ids the camera frames for a step: the step plus one hop either side. */
export function stepGroup(id: string, nodes: FlowNode[]): string[] {
  const cands = nodes.filter((n) => n.kind === "candidate");
  const mid = [...cands].sort((a, b) => Math.abs(a.y) - Math.abs(b.y)).slice(0, 2).map((n) => n.id);
  const has = new Set(nodes.map((n) => n.id));
  const keep = (ids: string[]) => ids.filter((x) => has.has(x));
  if (id === "qualify") return keep(["extract", ...cands.map((n) => n.id), "router"]);
  if (id.startsWith("cand:")) return keep([id, "extract", "router"]);
  if (id === "recheck") return keep(["rank", "monitor", "recheck"]);
  if (id === "evidence" || id === "excluded") return keep(["router", "rank", "evidence", "excluded"]);
  if (id === "router") return keep([...mid, "router", "rank", "evidence", "excluded"]);
  if (id === "monitor") return keep(["rank", "monitor", "recheck", "choose"]);
  const i = STEPS.findIndex((s) => s.id === id);
  if (i < 0) return keep([id]);
  const around = [STEPS[i - 1]?.id, id, STEPS[i + 1]?.id].filter(Boolean) as string[];
  return keep(around.flatMap((x) => (x === "qualify" ? mid : [x])));
}

/** Overall run status for the header pill. */
export function runStatus(nodes: FlowNode[]): { label: string; tone: "run" | "wait" | "ok" | "bad" } {
  if (nodes.some((n) => n.status === "error")) return { label: "Error", tone: "bad" };
  if (nodes.some((n) => n.status === "alert")) return { label: "Disruption", tone: "bad" };
  if (nodes.some((n) => n.status === "running" && n.id !== "monitor")) return { label: "Running", tone: "run" };
  if (nodes.some((n) => n.status === "waiting")) return { label: "Waiting for you", tone: "wait" };
  if (nodes.find((n) => n.id === "reassemble")?.status === "done") return { label: "Succeeded", tone: "ok" };
  return { label: "Ready", tone: "run" };
}

/** Thermal brand gradient sampled along the run (cyan → violet → magenta → amber). */
const STOPS: [number, [number, number, number]][] = [
  [0, [56, 189, 248]],
  [0.38, [139, 92, 246]],
  [0.7, [236, 72, 153]],
  [1, [251, 146, 60]],
];
export function thermalAt(t: number): string {
  const u = Math.max(0, Math.min(1, t));
  for (let i = 1; i < STOPS.length; i++) {
    const [t1, c1] = STOPS[i];
    const [t0, c0] = STOPS[i - 1];
    if (u <= t1) {
      const k = (u - t0) / (t1 - t0);
      const c = c0.map((v, j) => Math.round(v + (c1[j] - v) * k));
      return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
    }
  }
  return "rgb(251, 146, 60)";
}
