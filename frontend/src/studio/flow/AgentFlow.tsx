import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import {
  Activity, Ban, Box, Check, FileSearch, FileText, ListChecks, LocateFixed, Maximize2, Minimize2, PanelBottom,
  PanelRight, Plus, Radar, RefreshCw, Send, Split, Stamp, Trophy, UserCheck, Workflow, X, Zap, MailCheck, ScanSearch,
} from "lucide-react";
import {
  FLOW_STAGES, NODE, PILL_H, PILL_W, STEPS, buildGraph, liveStep, qualifyStatus, runStatus, stepGroup, stepStatus, thermalAt,
  type FlowEdge, type FlowNode, type FlowSnapshot, type IconName, type NodeStatus,
} from "./model.ts";
import "./flow.css";

type Mode = "scene" | "split" | "full";
type Dir = "v" | "h";
type View = { x: number; y: number; k: number };
type LogEntry = { id: number; t: Date; text: string; node: string; tone: FlowNode["status"] };

const ICONS: Record<IconName, typeof Zap> = {
  zap: Zap, radar: Radar, split: Split, trophy: Trophy, evidence: FileSearch, ban: Ban, activity: Activity,
  recheck: RefreshCw, user: UserCheck, doc: FileText, stamp: Stamp, send: Send, mail: MailCheck, box: Box,
};
const MODE_KEY = "rs-flow-mode";
const HEIGHT_KEY = "rs-flow-height";
const WIDTH_KEY = "rs-flow-width";
const SHARE_KEY = "rs-flow-share";
/** Side-by-side split needs room for the scene's own panels; narrower screens dock at the bottom. */
const WIDE_QUERY = "(min-width: 1100px)";
const MIN_SCENE = 640;
const STATUS_LABEL: Record<NodeStatus, string> = {
  idle: "Not started", running: "Running", waiting: "Waiting for you", done: "Done", alert: "Alert", skipped: "Skipped", error: "Error",
};

function useMedia(query: string) {
  const get = () => typeof matchMedia !== "undefined" && matchMedia(query).matches;
  const [on, setOn] = useState(get);
  useEffect(() => {
    if (typeof matchMedia === "undefined") return;
    const mq = matchMedia(query);
    const fn = () => setOn(mq.matches);
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, [query]);
  return on;
}
const maxWidth = () => Math.max(380, (typeof innerWidth === "number" ? innerWidth : 1440) - MIN_SCENE);
const reduced = () => typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;
const store = {
  get: (k: string) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));

export function AgentFlow(props: FlowSnapshot & { caseId?: string | null; focusId?: string | null; onFocusCandidate?: (id: string) => void }) {
  const visible = FLOW_STAGES.includes(props.stage);
  const [mode, setModeState] = useState<Mode>(() => (store.get(MODE_KEY) as Mode | null) ?? "split");
  const [height, setHeight] = useState(() => {
    const vh = typeof innerHeight === "number" && innerHeight > 0 ? innerHeight : 900;
    return Math.round(clamp(Number(store.get(HEIGHT_KEY)) || vh * 0.44, 260, Math.max(260, vh * 0.75)));
  });
  const [width, setWidth] = useState(() => {
    const vw = typeof innerWidth === "number" && innerWidth > 0 ? innerWidth : 1440;
    return Math.round(clamp(Number(store.get(WIDTH_KEY)) || vw * 0.4, 380, maxWidth()));
  });
  const [share, setShare] = useState(() => clamp(Number(store.get(SHARE_KEY)) || 0.44, 0.28, 0.72));
  const dir: Dir = useMedia(WIDE_QUERY) ? "v" : "h";
  // A pinned step overrides the live one until the user goes back to live.
  const [pinned, setPinned] = useState<string | null>(null);
  const setMode = useCallback((m: Mode) => { setModeState(m); store.set(MODE_KEY, m); }, []);

  const { nodes, edges } = useMemo(() => buildGraph(props), [props.stage, props.part?.name, props.part?.partNumber, props.part?.revision, props.need, props.assessed, props.checked, props.progress, props.disrupted, props.recheck, props.procure, props.chosenId, props.phase, props.busy, props.error, props.project, props.partId]);
  const loadingOffers = props.stage === "discovery" && props.busy === "research" && !props.assessed.length && !props.error;
  const status = props.error ? { label: "Error", tone: "bad" as const } : loadingOffers ? { label: "Loading offers", tone: "run" as const } : runStatus(nodes);
  const live = loadingOffers || (props.error && props.stage === "discovery") ? "discover" : liveStep(nodes);
  const focus = pinned && (pinned === "qualify" || nodes.some((n) => n.id === pinned)) ? pinned : live;
  const group = useMemo(() => stepGroup(focus, nodes), [focus, nodes]);

  // The run moved (new step, new screen, disruption): drop any pin and glide to it.
  useEffect(() => { setPinned(null); }, [props.stage, live]);

  // The studio gives up its right edge (side-by-side) or its bottom (docked) in split mode.
  useEffect(() => {
    const root = document.documentElement;
    if (visible) { root.dataset.rsFlow = mode; root.dataset.rsFlowDir = dir; }
    else { delete root.dataset.rsFlow; delete root.dataset.rsFlowDir; }
    return () => { delete root.dataset.rsFlow; delete root.dataset.rsFlowDir; };
  }, [visible, mode, dir]);
  useEffect(() => {
    document.documentElement.style.setProperty("--rs-flow-h", `${height}px`);
  }, [height]);
  useEffect(() => {
    document.documentElement.style.setProperty("--rs-flow-w", `${width}px`);
  }, [width]);
  useEffect(() => {
    const fit = () => setWidth((w) => Math.min(w, maxWidth()));
    addEventListener("resize", fit);
    return () => removeEventListener("resize", fit);
  }, []);

  // Keyboard: W cycles Scene → Split → Workflow; Escape returns to live. Ignored while typing.
  useEffect(() => {
    if (!visible) return;
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (e.metaKey || e.ctrlKey || e.altKey || t?.closest("input, textarea, select, [contenteditable='true']")) return;
      if (e.key === "w" || e.key === "W") setMode(mode === "scene" ? "split" : mode === "split" ? "full" : "scene");
      if (e.key === "Escape") {
        if (pinned) setPinned(null);
        else if (mode === "full") setMode("split");
      }
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [visible, mode, setMode, pinned]);

  // ---- Execution log: written from real status transitions ----
  const [log, setLog] = useState<LogEntry[]>([]);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const seen = useRef(new Map<string, string>());
  const seq = useRef(0);
  const discovering = props.stage === "discovery";
  const wasDiscovering = useRef(false);
  useEffect(() => {
    const newRun = discovering && !wasDiscovering.current;
    wasDiscovering.current = discovering;
    if (!visible) return;
    if (newRun) {
      // New run: start a fresh execution.
      seen.current.clear();
      setLog([]);
      setStartedAt(Date.now());
      setPinned(null);
    }
    const fresh: LogEntry[] = [];
    for (const n of nodes) {
      const key = `${n.status}|${n.log ?? ""}`;
      if (seen.current.get(n.id) === key) continue;
      seen.current.set(n.id, key);
      if (n.log) fresh.push({ id: ++seq.current, t: new Date(), text: n.log, node: n.id, tone: n.status });
    }
    if (fresh.length) {
      setStartedAt((s) => s ?? Date.now());
      setLog((l) => [...l, ...fresh].slice(-80));
    }
  }, [nodes, visible, discovering]);

  const done = status.tone === "ok";
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!visible || done) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [visible, done]);
  const elapsed = startedAt ? Math.max(0, Math.floor(((done ? (log.at(-1)?.t.getTime() ?? now) : now) - startedAt) / 1000)) : 0;
  const clock = `${String(Math.floor(elapsed / 60)).padStart(2, "0")}:${String(elapsed % 60).padStart(2, "0")}`;

  const pin = (id: string | null) => {
    setPinned(id === live ? null : id);
    if (id?.startsWith("cand:")) props.onFocusCandidate?.(id.slice(5));
  };
  const actOn = (id: string) => {
    // Human-gate nodes in full view send the user back to the scene to act.
    const n = nodes.find((x) => x.id === id);
    if (mode === "full" && n?.status === "waiting") setMode("split");
  };

  if (!visible || typeof document === "undefined") return null;
  const latest = log.at(-1);
  const pinnedNode = nodes.find((n) => n.id === pinned) ?? null;
  const side = mode === "split" && dir === "v";
  // Inspector overlay only where there is no output pane (full view, docked split).
  const inspectorNode = side ? null : pinnedNode;
  const canvas = (
    <FlowCanvas
      nodes={nodes}
      edges={edges}
      mode={mode}
      side={side}
      group={group}
      focus={focus}
      pinned={pinned}
      candidateFocus={props.focusId ? `cand:${props.focusId}` : null}
      onSelect={(id) => pin(id)}
      onLive={() => setPinned(null)}
      onAct={actOn}
      insetLeft={mode === "full" ? 300 : 0}
      insetRight={inspectorNode ? 340 : 0}
    />
  );

  return createPortal(
    <>
      <AnimatePresence>
        {mode === "scene" ? (
          <MiniDock key="mini" nodes={nodes} status={status} latest={latest?.text} onOpen={() => setMode("split")} />
        ) : null}
      </AnimatePresence>
      <AnimatePresence>
        {mode !== "scene" ? (
          <motion.section
            key={`pane-${mode}-${dir}`}
            className={`fl-pane is-${mode}${mode === "split" ? ` is-${dir}` : ""}`}
            aria-label="Demo sourcing agent workflow"
            initial={mode === "full" ? { opacity: 0, scale: 0.985 } : side ? { x: "100%" } : { y: "100%" }}
            animate={{ opacity: 1, scale: 1, x: 0, y: 0 }}
            exit={mode === "full" ? { opacity: 0, scale: 0.985 } : side ? { x: "100%" } : { y: "100%" }}
            transition={{ duration: reduced() ? 0 : 0.6, ease: [0.22, 1, 0.36, 1] }}
          >
            {mode === "split" && dir === "h" ? <Resizer height={height} onHeight={(h) => { setHeight(h); store.set(HEIGHT_KEY, String(h)); }} /> : null}
            {side ? <SideResizer width={width} onWidth={(w) => { setWidth(w); store.set(WIDTH_KEY, String(w)); }} /> : null}
            <header className="fl-bar">
              <div className="fl-bar-left">
                <span className="fl-bar-ico"><Workflow size={15} /></span>
                <span className="fl-bar-title">Demo sourcing agent</span>
                <span className={`fl-run is-${status.tone}`}><i />{status.label}</span>
                <span className="fl-clock" aria-label="Elapsed">{clock}</span>
                {props.caseId ? <span className="fl-case">Case {props.caseId.slice(-6)}</span> : null}
              </div>
              <div className="fl-ticker" aria-hidden="true">
                <AnimatePresence mode="popLayout" initial={false}>
                  {latest ? (
                    <motion.span key={latest.id} initial={{ y: 14, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: -14, opacity: 0 }} transition={{ duration: 0.35 }}>
                      <b>{latest.t.toLocaleTimeString("en-GB", { hour12: false })}</b> {latest.text}
                    </motion.span>
                  ) : null}
                </AnimatePresence>
              </div>
              <div className="fl-bar-right">
                <ModeSwitch mode={mode} dir={dir} onMode={setMode} />
              </div>
            </header>
            {mode === "split" ? <StageRail nodes={nodes} focus={focus} live={live} onPick={(id) => pin(id)} /> : null}
            {side ? (
              <StackBody share={share} onShare={(s) => { setShare(s); store.set(SHARE_KEY, String(s)); }}>
                {canvas}
                <div className="fl-lower">
                  <OutputPanel
                    focus={focus}
                    isLive={!pinned || pinned === live}
                    nodes={nodes}
                    edges={edges}
                    log={log}
                    onPick={(id) => pin(id)}
                    onLive={() => setPinned(null)}
                  />
                  <LogPanel log={log} inline focus={focus} onPick={(id) => pin(id)} />
                </div>
              </StackBody>
            ) : (
              <div className="fl-body">
                {mode === "full" ? <LogPanel log={log} focus={focus} onPick={(id) => pin(id)} /> : null}
                {canvas}
                <AnimatePresence>
                  {inspectorNode ? <Inspector key="insp" node={inspectorNode} onClose={() => setPinned(null)} onAct={() => setMode("split")} canAct={mode === "full" && inspectorNode.status === "waiting"} /> : null}
                </AnimatePresence>
              </div>
            )}
          </motion.section>
        ) : null}
      </AnimatePresence>
      <div className="rs-sr-only" aria-live="polite">{latest?.text}</div>
    </>,
    document.body,
  );
}

// ---------------------------------------------------------------- canvas

function FlowCanvas({
  nodes, edges, mode, side, group, focus, pinned, candidateFocus, onSelect, onLive, onAct, insetLeft, insetRight,
}: {
  nodes: FlowNode[];
  edges: FlowEdge[];
  mode: Mode;
  side: boolean;
  /** Node ids framed by the follow camera (the focused step and its neighbours). */
  group: string[];
  focus: string;
  pinned: string | null;
  candidateFocus: string | null;
  onSelect: (id: string | null) => void;
  onLive: () => void;
  onAct: (id: string) => void;
  insetLeft: number;
  insetRight: number;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [view, setView] = useState<View>({ x: 0, y: 0, k: 0.8 });
  // Camera: "follow" tracks the live frontier, "fit" holds the whole graph, "free" is user-driven.
  const [cam, setCam] = useState<"follow" | "fit" | "free">("follow");
  const follow = cam === "follow";
  const setFollow = (on: boolean) => setCam(on ? "follow" : "free");
  const [animating, setAnimating] = useState(true);
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  const minX = Math.min(...nodes.map((n) => n.x)) - 60;
  const maxX = Math.max(...nodes.map((n) => n.x)) + 60;
  const accent = (n: FlowNode) => thermalAt((n.x - minX) / (maxX - minX));

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Camera target: the live frontier of the run plus one hop of context.
  const frame = useCallback(
    (group: FlowNode[]): View | null => {
      if (!size.w || !group.length) return null;
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (const n of group) {
        const hw = n.kind === "candidate" ? PILL_W / 2 : 80;
        const top = n.kind === "candidate" ? PILL_H / 2 : NODE / 2 + 30;
        const bottom = n.kind === "candidate" ? PILL_H / 2 : NODE / 2 + 52;
        x0 = Math.min(x0, n.x - hw); x1 = Math.max(x1, n.x + hw);
        y0 = Math.min(y0, n.y - top); y1 = Math.max(y1, n.y + bottom);
      }
      const w = size.w - insetLeft - insetRight;
      const pad = mode === "full" ? 80 : side ? 44 : 36;
      const maxK = mode === "full" ? 1.15 : side ? 0.95 : 0.95;
      const k = clamp(Math.min((w - pad * 2) / (x1 - x0), (size.h - pad * 2) / (y1 - y0)), 0.3, maxK);
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      return { k, x: insetLeft + w / 2 - cx * k, y: size.h / 2 - cy * k };
    },
    [size, mode, side, insetLeft, insetRight],
  );

  // Follow camera: glide from step to step as the run (or the pinned step) moves.
  const groupKey = `${group.join(",")}|${nodes.length}`;
  const target = useMemo(() => frame(group.map((id) => byId.get(id)!).filter(Boolean)), [groupKey, frame]); // eslint-disable-line react-hooks/exhaustive-deps
  // A new focus step always re-engages follow, even after the user panned away.
  useEffect(() => { setCam("follow"); }, [focus]);

  useEffect(() => {
    if (follow && target) {
      setAnimating(true);
      setView(target);
    }
  }, [follow, target]);
  const fitView = useMemo(() => frame(nodes), [frame, nodes.length]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (cam === "fit" && fitView) {
      setAnimating(true);
      setView(fitView);
    }
  }, [cam, fitView]);

  const fitAll = () => setCam("fit");

  // Pan (drag / two-finger scroll) and zoom (pinch / ctrl+wheel).
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      setFollow(false);
      setAnimating(false);
      const r = el.getBoundingClientRect();
      const px = e.clientX - r.left, py = e.clientY - r.top;
      setView((v) => {
        if (e.ctrlKey || e.metaKey) {
          const k = clamp(v.k * Math.exp(-e.deltaY * 0.01), 0.25, 2);
          return { k, x: px - ((px - v.x) * k) / v.k, y: py - ((py - v.y) * k) / v.k };
        }
        return { ...v, x: v.x - e.deltaX, y: v.y - e.deltaY };
      });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const paths = useMemo(() => edges.map((e) => ({ e, ...edgePath(e, byId) })).filter((p) => p.d), [edges, byId]);
  const anim = !reduced();
  const t = animating && anim ? "transform 1.15s cubic-bezier(0.22, 1, 0.36, 1)" : "none";
  const dot = 22 * view.k;

  return (
    <div
      ref={box}
      className={`fl-canvas${drag.current ? " is-dragging" : ""}`}
      style={{
        backgroundSize: `${dot}px ${dot}px`,
        backgroundPosition: `${view.x}px ${view.y}px`,
        transition: animating && anim ? "background-position 1.15s cubic-bezier(0.22, 1, 0.36, 1), background-size 1.15s cubic-bezier(0.22, 1, 0.36, 1)" : "none",
      }}
      onPointerDown={(e) => {
        if ((e.target as HTMLElement).closest("button")) return;
        (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
        drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y };
        setFollow(false);
        setAnimating(false);
      }}
      onPointerMove={(e) => {
        const d = drag.current;
        if (d) setView((v) => ({ ...v, x: d.vx + e.clientX - d.x, y: d.vy + e.clientY - d.y }));
      }}
      onPointerUp={() => { drag.current = null; }}
      onPointerCancel={() => { drag.current = null; }}
      onDoubleClick={(e) => { if (!(e.target as HTMLElement).closest("button")) fitAll(); }}
    >
      <div className="fl-world" style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})`, transition: t }}>
        <svg className="fl-edges" width="1" height="1" aria-hidden="true">
          <defs>
            <linearGradient id="fl-thermal" gradientUnits="userSpaceOnUse" x1={minX} y1="0" x2={maxX} y2="0">
              <stop offset="0" stopColor="#38bdf8" />
              <stop offset="0.38" stopColor="#8b5cf6" />
              <stop offset="0.7" stopColor="#ec4899" />
              <stop offset="1" stopColor="#fb923c" />
            </linearGradient>
          </defs>
          {paths.map(({ e, d }) => (
            <g key={e.id} className={`fl-edge is-${e.state}`}>
              <path d={d} className="fl-edge-base" />
              {e.state === "done" ? <path d={d} className="fl-edge-done" pathLength={1} /> : null}
              {e.state === "active" ? (
                <>
                  <path d={d} className="fl-edge-flow" />
                  {anim ? [0, 0.5].map((b) => (
                    <circle key={b} r={3.2} className="fl-particle">
                      <animateMotion dur="1.3s" begin={`${b * 1.3}s`} repeatCount="indefinite" path={d} />
                    </circle>
                  )) : null}
                </>
              ) : null}
            </g>
          ))}
        </svg>
        {paths.map(({ e, sx, sy, mx, my }) => (
          <EdgeLabels key={e.id} e={e} sx={sx} sy={sy} mx={mx} my={my} />
        ))}
        {nodes.map((n) =>
          n.kind === "candidate" ? (
            <Pill key={n.id} n={n} accent={accent(n)} focused={focus === n.id} selected={pinned === n.id || candidateFocus === n.id} onSelect={() => onSelect(pinned === n.id ? null : n.id)} />
          ) : (
            <Node key={n.id} n={n} accent={accent(n)} focused={focus === n.id} selected={pinned === n.id} onSelect={() => { onSelect(pinned === n.id ? null : n.id); onAct(n.id); }} />
          ),
        )}
      </div>
      <div className="fl-tools">
        <button
          type="button"
          className={`fl-tool${follow && !pinned ? " is-on" : ""}`}
          onClick={() => { onLive(); setFollow(true); }}
          aria-pressed={follow && !pinned}
          title="Follow the demo run"
        >
          <LocateFixed size={14} /> <span>Follow run</span>
        </button>
        <button type="button" className="fl-tool" onClick={fitAll} title="Fit the whole workflow (double-click canvas)">
          <ScanSearch size={14} /> <span>Fit</span>
        </button>
      </div>
    </div>
  );
}

function handle(n: FlowNode, side: "in" | "out", offset = 0) {
  if (n.kind === "candidate") return { x: n.x + (side === "in" ? -PILL_W / 2 : PILL_W / 2), y: n.y };
  return { x: n.x + (side === "in" ? -NODE / 2 - 4 : NODE / 2 + 4), y: n.y + offset };
}

function edgePath(e: FlowEdge, byId: Map<string, FlowNode>) {
  const a = byId.get(e.from), b = byId.get(e.to);
  if (!a || !b) return { d: "", sx: 0, sy: 0, mx: 0, my: 0 };
  if (e.loop) {
    // Feedback arc: left side of the recheck node back down into the top of the ranker.
    const s = { x: a.x - NODE / 2 - 4, y: a.y }, t = { x: b.x, y: b.y - NODE / 2 - 4 };
    const d = `M ${s.x} ${s.y} C ${s.x - 120} ${s.y}, ${t.x} ${t.y - 120}, ${t.x} ${t.y}`;
    return { d, sx: s.x, sy: s.y, ...mid(s, { x: s.x - 120, y: s.y }, { x: t.x, y: t.y - 120 }, t) };
  }
  if (a.x === b.x) {
    // Vertical branch (monitor → recheck): out of the top, into the bottom.
    const s = { x: a.x, y: a.y - NODE / 2 - 4 }, t = { x: b.x, y: b.y + NODE / 2 + 48 };
    const d = `M ${s.x} ${s.y} L ${t.x} ${t.y}`;
    return { d, sx: s.x, sy: s.y, mx: s.x, my: (s.y + t.y) / 2 };
  }
  const s = handle(a, "out", e.fromOffset), t = handle(b, "in");
  const dx = Math.max(48, Math.abs(t.x - s.x) * 0.5);
  const c1 = { x: s.x + dx, y: s.y }, c2 = { x: t.x - dx, y: t.y };
  return { d: `M ${s.x} ${s.y} C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${t.x} ${t.y}`, sx: s.x, sy: s.y, ...mid(s, c1, c2, t) };
}
// Item-count badge sits at t = 0.62 along the curve, clear of branch labels at the source.
const mid = (p0: { x: number; y: number }, p1: { x: number; y: number }, p2: { x: number; y: number }, p3: { x: number; y: number }, t = 0.62) => {
  const u = 1 - t;
  const b = (a: number, b1: number, c: number, d: number) => u * u * u * a + 3 * u * u * t * b1 + 3 * u * t * t * c + t * t * t * d;
  return { mx: b(p0.x, p1.x, p2.x, p3.x), my: b(p0.y, p1.y, p2.y, p3.y) };
};

function EdgeLabels({ e, sx, sy, mx, my }: { e: FlowEdge; sx: number; sy: number; mx: number; my: number }) {
  return (
    <>
      {e.label ? (
        <span className={`fl-edge-label is-${e.state}`} style={{ left: sx + 10, top: sy - (e.from === "monitor" && e.to === "recheck" ? 0 : 17), ...(e.from === "monitor" && e.to === "recheck" ? { left: sx + 8, top: sy - 40 } : {}) }}>
          {e.label}
        </span>
      ) : null}
      {e.items != null && e.state === "done" ? (
        <span className="fl-items" style={{ left: mx, top: my }}>
          {e.items} {e.items === 1 ? "item" : "items"}
        </span>
      ) : null}
    </>
  );
}

// ---------------------------------------------------------------- nodes

function StatusPip({ s }: { s: FlowNode["status"] }) {
  if (s === "done") return <span className="fl-pip is-done"><Check size={11} strokeWidth={3} /></span>;
  if (s === "running") return <span className="fl-pip is-running" />;
  if (s === "alert" || s === "error") return <span className="fl-pip is-alert">!</span>;
  return null;
}

function Node({ n, accent, selected, focused, onSelect }: { n: FlowNode; accent: string; selected: boolean; focused: boolean; onSelect: () => void }) {
  const Icon = ICONS[n.icon];
  return (
    <div className="fl-node" data-kind={n.kind} data-status={n.status} data-selected={selected || undefined} data-focus={focused || undefined} style={{ left: n.x - 80, top: n.y - NODE / 2, "--accent": accent } as CSSProperties}>
      {n.status === "waiting" ? <span className="fl-tag">Your move</span> : null}
      {n.simulated ? <span className="fl-sim" title="External message simulated in the demo">SIM</span> : null}
      <button type="button" className="fl-box" onClick={onSelect} aria-label={`${n.title}: ${n.sub} (${n.status})`} aria-pressed={selected}>
        <span className="fl-box-fill" />
        <Icon className="fl-icon" size={30} strokeWidth={1.6} />
        <span className="fl-burst" />
      </button>
      {n.kind !== "trigger" ? <span className="fl-handle in" /> : <Zap className="fl-bolt" size={18} />}
      {n.kind !== "end" || n.stub ? <span className="fl-handle out" /> : null}
      {n.stub ? (
        <span className="fl-stub" aria-hidden="true"><i /><Plus size={12} /></span>
      ) : null}
      {n.id === "router" ? (
        <>
          <span className="fl-handle out" style={{ top: NODE / 2 - 22 - 6 }} />
          <span className="fl-handle out" style={{ top: NODE / 2 + 22 - 6 }} />
        </>
      ) : null}
      <StatusPip s={n.status} />
      <span className="fl-title">{n.title}</span>
      <span className="fl-sub">{n.sub}</span>
    </div>
  );
}

function Pill({ n, accent, selected, focused, onSelect }: { n: FlowNode; accent: string; selected: boolean; focused: boolean; onSelect: () => void }) {
  const c = n.candidate!;
  return (
    <button
      type="button"
      className="fl-pill"
      data-status={n.status}
      data-state={c.state}
      data-selected={selected || focused || undefined}
      style={{ left: n.x - PILL_W / 2, top: n.y - PILL_H / 2, width: PILL_W, height: PILL_H, "--accent": accent } as CSSProperties}
      onClick={onSelect}
      aria-label={`${c.name}, ${c.city}: ${n.sub}`}
    >
      <span className="fl-pill-cc">{c.countryCode}</span>
      <span className="fl-pill-name">
        <b>{c.name}</b>
        <small>{c.city}</small>
      </span>
      <span className="fl-pips">
        {c.pips.map((p, i) => <i key={i} data-p={p} />)}
      </span>
      {c.rank ? <span className="fl-rank">#{c.rank}</span> : null}
    </button>
  );
}

// ---------------------------------------------------------------- chrome

function ModeSwitch({ mode, dir, onMode }: { mode: Mode; dir: Dir; onMode: (m: Mode) => void }) {
  const opts: { m: Mode; label: string; icon: ReactNode }[] = [
    { m: "scene", label: "Scene", icon: <Minimize2 size={13} /> },
    { m: "split", label: "Split", icon: dir === "v" ? <PanelRight size={13} /> : <PanelBottom size={13} /> },
    { m: "full", label: "Workflow", icon: <Maximize2 size={13} /> },
  ];
  return (
    <div className="fl-modes" role="group" aria-label="Workflow view (W)">
      {opts.map((o) => (
        <button key={o.m} type="button" aria-pressed={mode === o.m} onClick={() => onMode(o.m)} title={`${o.label} view · press W to cycle`}>
          <span className="fl-mode-in">{o.icon}{o.label}</span>
        </button>
      ))}
    </div>
  );
}

function Resizer({ height, onHeight }: { height: number; onHeight: (h: number) => void }) {
  const start = useRef<{ y: number; h: number } | null>(null);
  return (
    <div
      className="fl-resizer"
      role="separator"
      aria-orientation="horizontal"
      aria-label="Resize workflow panel"
      aria-valuenow={height}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "ArrowUp") onHeight(clamp(height + 24, 220, innerHeight * 0.75));
        if (e.key === "ArrowDown") onHeight(clamp(height - 24, 220, innerHeight * 0.75));
      }}
      onPointerDown={(e) => {
        e.currentTarget.setPointerCapture(e.pointerId);
        start.current = { y: e.clientY, h: height };
        document.documentElement.dataset.rsFlowResizing = "1";
      }}
      onPointerMove={(e) => {
        if (start.current) onHeight(Math.round(clamp(start.current.h - (e.clientY - start.current.y), 220, innerHeight * 0.75)));
      }}
      onPointerUp={() => { start.current = null; delete document.documentElement.dataset.rsFlowResizing; }}
    >
      <i />
    </div>
  );
}

/** Width handle on the left edge of the side-by-side pane. */
function SideResizer({ width, onWidth }: { width: number; onWidth: (w: number) => void }) {
  const start = useRef<{ x: number; w: number } | null>(null);
  return (
    <div
      className="fl-resizer is-side"
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize workflow panel"
      aria-valuenow={width}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") onWidth(clamp(width + 32, 380, maxWidth()));
        if (e.key === "ArrowRight") onWidth(clamp(width - 32, 380, maxWidth()));
      }}
      onPointerDown={(e) => {
        e.currentTarget.setPointerCapture(e.pointerId);
        start.current = { x: e.clientX, w: width };
        document.documentElement.dataset.rsFlowResizing = "1";
      }}
      onPointerMove={(e) => {
        if (start.current) onWidth(Math.round(clamp(start.current.w - (e.clientX - start.current.x), 380, maxWidth())));
      }}
      onPointerUp={() => { start.current = null; delete document.documentElement.dataset.rsFlowResizing; }}
    >
      <i />
    </div>
  );
}

/** Canvas above, stage output + execution log below, with a draggable divider. */
function StackBody({ share, onShare, children }: { share: number; onShare: (s: number) => void; children: [ReactNode, ReactNode] }) {
  const ref = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);
  const set = (clientY: number) => {
    const r = ref.current?.getBoundingClientRect();
    if (r) onShare(clamp((clientY - r.top) / r.height, 0.28, 0.72));
  };
  return (
    <div ref={ref} className="fl-body is-stack" style={{ gridTemplateRows: `minmax(180px, ${share}fr) 12px minmax(200px, ${1 - share}fr)` }}>
      {children[0]}
      <div
        className="fl-row-resizer"
        role="separator"
        aria-orientation="horizontal"
        aria-label="Resize workflow canvas"
        aria-valuenow={Math.round(share * 100)}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "ArrowUp") onShare(clamp(share - 0.04, 0.28, 0.72));
          if (e.key === "ArrowDown") onShare(clamp(share + 0.04, 0.28, 0.72));
        }}
        onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); dragging.current = true; }}
        onPointerMove={(e) => { if (dragging.current) set(e.clientY); }}
        onPointerUp={() => { dragging.current = false; }}
      >
        <i />
      </div>
      {children[1]}
    </div>
  );
}

/** Horizontal step rail: where the run is, what's done, and a jump target for each step. */
function StageRail({ nodes, focus, live, onPick }: { nodes: FlowNode[]; focus: string; live: string; onPick: (id: string) => void }) {
  const ref = useRef<HTMLOListElement>(null);
  // Map branch / candidate focus back onto the trunk step that owns it.
  const railFocus = focus.startsWith("cand:") ? "qualify" : focus === "recheck" ? "monitor" : focus === "evidence" || focus === "excluded" ? "router" : focus;
  const railLive = live === "recheck" ? "monitor" : live;
  useEffect(() => {
    const ol = ref.current;
    const li = ol?.querySelector<HTMLElement>(`[data-step="${railFocus}"]`);
    if (!ol || !li) return;
    ol.scrollTo({ left: li.offsetLeft - (ol.clientWidth - li.offsetWidth) / 2, behavior: reduced() ? "auto" : "smooth" });
  }, [railFocus]);
  return (
    <nav className="fl-rail" aria-label="Workflow steps">
      <ol ref={ref}>
        {STEPS.map((s, i) => {
          const st = s.id === "monitor" && stepStatus("recheck", nodes) === "running" ? "running" : stepStatus(s.id, nodes);
          const label = nodes.find((n) => n.id === s.id)?.railLabel ?? s.label;
          return (
            <li key={s.id} data-step={s.id}>
              <button
                type="button"
                data-status={st}
                aria-current={railFocus === s.id ? "step" : undefined}
                onClick={() => onPick(s.id)}
                style={{ "--accent": thermalAt(i / (STEPS.length - 1)) } as CSSProperties}
                title={`${label} · ${STATUS_LABEL[st]}`}
              >
                <i>{st === "done" ? <Check size={9} strokeWidth={3.5} /> : null}</i>
                <span>{label}</span>
                {railLive === s.id && railFocus !== s.id ? <b className="fl-rail-live" aria-label="live" /> : null}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/** Stage output: whatever the focused step produced, updating live as it runs. */
function OutputPanel({
  focus, isLive, nodes, edges, log, onPick, onLive,
}: {
  focus: string;
  isLive: boolean;
  nodes: FlowNode[];
  edges: FlowEdge[];
  log: LogEntry[];
  onPick: (id: string) => void;
  onLive: () => void;
}) {
  const node = nodes.find((n) => n.id === focus) ?? null;
  const cands = nodes.filter((n) => n.kind === "candidate");
  const isQualify = focus === "qualify";
  const stIdx = STEPS.findIndex((s) => s.id === (focus.startsWith("cand:") ? "qualify" : focus === "recheck" ? "monitor" : focus));
  const status: NodeStatus = isQualify ? qualifyStatus(nodes) : node?.status ?? "idle";
  const Icon = isQualify ? ListChecks : node ? ICONS[node.icon] : Box;
  const title = isQualify ? "Re::Source · Supplier checks" : node?.kind === "candidate" ? `${node.candidate!.name}` : node?.title ?? focus;
  const doneCount = cands.filter((c) => c.status === "done" || c.status === "alert").length;
  const sub = isQualify ? (cands.length ? `${doneCount}/${cands.length} sites checked · 6 checks each` : "Waiting for discovered sites") : node?.sub ?? "";
  const events = log.filter((l) => (isQualify ? l.node.startsWith("cand:") : l.node === focus)).slice(-6);
  const inbound = edges.filter((e) => e.to === focus && e.items != null && e.state === "done");
  const outbound = edges.filter((e) => e.from === focus && e.items != null && e.state === "done");
  const nameOf = (id: string) => nodes.find((n) => n.id === id)?.title ?? id;

  return (
    <section className="fl-out" aria-label="Stage output" aria-live="polite">
      <div className="fl-panel-head">
        <span>Stage output</span>
        {isLive ? (
          <span className="fl-live-pill"><i />Demo run</span>
        ) : (
          <button type="button" className="fl-live-btn" onClick={onLive}><LocateFixed size={12} /> Follow run</button>
        )}
      </div>
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={focus}
          className="fl-out-body"
          initial={{ opacity: 0, x: 18 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -18 }}
          transition={{ duration: reduced() ? 0 : 0.32, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="fl-out-head" data-status={status}>
            <span className="fl-out-ico"><Icon size={17} /></span>
            <div style={{ minWidth: 0 }}>
              <div className="fl-out-title">
                {title}
                {node?.simulated ? <span className="fl-sim is-inline">SIM</span> : null}
              </div>
              <div className="fl-out-sub">{sub}</div>
            </div>
            <div className="fl-out-meta">
              <span className={`fl-insp-status is-${status}`}>{STATUS_LABEL[status]}</span>
              {stIdx >= 0 ? <span className="fl-muted">Step {stIdx + 1}/{STEPS.length}</span> : null}
            </div>
          </div>

          {inbound.length || outbound.length ? (
            <div className="fl-io">
              {inbound.map((e) => <span key={e.id}><b>In</b> {e.items} from {nameOf(e.from)}</span>)}
              {outbound.map((e) => <span key={e.id}><b>Out</b> {e.items} → {e.label ?? nameOf(e.to)}</span>)}
            </div>
          ) : null}

          {isQualify ? (
            cands.length ? (
              <ul className="fl-cands">
                {cands.map((c) => {
                  const k = c.candidate!;
                  return (
                    <li key={c.id}>
                      <button type="button" onClick={() => onPick(c.id)} data-status={c.status} data-state={k.state}>
                        <span className="fl-pill-cc">{k.countryCode}</span>
                        <span className="fl-cand-name"><b>{k.name}</b><small>{c.status === "done" ? c.sub : k.city}</small></span>
                        <span className="fl-pips">{k.pips.map((p, i) => <i key={i} data-p={p} />)}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : <p className="fl-empty">Sites appear here as discovery returns them.</p>
          ) : node && node.detail.length ? (
            <dl className="fl-kv">
              {node.detail.map((d, i) => (
                <div key={i} data-tone={d.tone}>
                  <dt>{d.k}</dt>
                  <dd>{d.v}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="fl-empty">{status === "idle" ? "This step hasn't run yet." : "No output fields for this step."}</p>
          )}

          {events.length ? (
            <div className="fl-out-events">
              <div className="fl-subhead">Events from this step</div>
              <ol>
                {events.map((l) => (
                  <li key={l.id}>
                    <i data-tone={l.tone} />
                    <time>{l.t.toLocaleTimeString("en-GB", { hour12: false })}</time>
                    <span>{l.text}</span>
                  </li>
                ))}
              </ol>
            </div>
          ) : null}
        </motion.div>
      </AnimatePresence>
    </section>
  );
}

function LogPanel({ log, onPick, focus, inline }: { log: LogEntry[]; onPick: (node: string) => void; focus?: string; inline?: boolean }) {
  const ref = useRef<HTMLOListElement>(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: reduced() ? "auto" : "smooth" });
  }, [log.length]);
  const mine = (node: string) => !!focus && (focus === "qualify" ? node.startsWith("cand:") : node === focus);
  return (
    <aside className={`fl-log${inline ? " is-inline" : ""}`} aria-label="Execution log">
      <div className="fl-panel-head"><span>Execution log</span><span className="fl-muted">{log.length} events</span></div>
      <ol ref={ref}>
        {log.length === 0 ? <li className="fl-empty">Events stream here as each step runs.</li> : null}
        <AnimatePresence initial={false}>
          {log.map((l) => (
            <motion.li key={l.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.35 }}>
              <button type="button" onClick={() => onPick(l.node)} data-mine={mine(l.node) || undefined}>
                <i data-tone={l.tone} />
                <time>{l.t.toLocaleTimeString("en-GB", { hour12: false })}</time>
                <span>{l.text}</span>
              </button>
            </motion.li>
          ))}
        </AnimatePresence>
      </ol>
    </aside>
  );
}

function Inspector({ node, onClose, onAct, canAct }: { node: FlowNode; onClose: () => void; onAct: () => void; canAct: boolean }) {
  const Icon = ICONS[node.icon];
  return (
    <motion.aside
      className="fl-inspector"
      aria-label={`${node.title} details`}
      initial={{ x: 24, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 24, opacity: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="fl-insp-head">
        <span className="fl-insp-ico"><Icon size={18} /></span>
        <div>
          <div className="fl-insp-title">{node.title}</div>
          <div className={`fl-insp-status is-${node.status}`}>{node.status === "waiting" ? "Waiting for you" : node.status}{node.simulated ? " · simulated" : ""}</div>
        </div>
        <button type="button" className="fl-icon-btn" onClick={onClose} aria-label="Close details"><X size={15} /></button>
      </div>
      <div className="fl-panel-head"><span>Output</span><span className="fl-muted">{node.detail.length} fields</span></div>
      <dl className="fl-kv">
        {node.detail.map((d, i) => (
          <div key={i} data-tone={d.tone}>
            <dt>{d.k}</dt>
            <dd>{d.v}</dd>
          </div>
        ))}
      </dl>
      {canAct ? <button type="button" className="rs-btn rs-btn-sm fl-act" onClick={onAct}>Open the scene to act</button> : null}
    </motion.aside>
  );
}

function MiniDock({ nodes, status, latest, onOpen }: { nodes: FlowNode[]; status: ReturnType<typeof runStatus>; latest?: string; onOpen: () => void }) {
  const trunk = nodes.filter((n) => n.kind !== "candidate" && n.y === 0);
  const cands = nodes.filter((n) => n.kind === "candidate");
  const candStatus: FlowNode["status"] = cands.some((c) => c.status === "running") ? "running" : cands.length && cands.every((c) => c.status === "done" || c.status === "alert") ? "done" : "idle";
  const dots = [...trunk.slice(0, 2).map((n) => n.status), candStatus, ...trunk.slice(2).map((n) => n.status)];
  return (
    <motion.button
      type="button"
      className="fl-mini"
      onClick={onOpen}
      initial={{ y: 30, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: 30, opacity: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      aria-label={`Open the demo workflow. ${status.label}. ${latest ?? ""}`}
    >
      <span className={`fl-run is-${status.tone}`}><i />{status.label}</span>
      <span className="fl-mini-track">
        {dots.map((s, i) => <i key={i} data-status={s} style={{ "--accent": thermalAt(i / (dots.length - 1)) } as CSSProperties} />)}
      </span>
      <span className="fl-mini-text">{latest ?? "Agent workflow"}</span>
      <span className="fl-mini-open"><Workflow size={13} /> Workflow <kbd>W</kbd></span>
    </motion.button>
  );
}
