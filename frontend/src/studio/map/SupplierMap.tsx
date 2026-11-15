import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { geoMercator, geoGraticule10, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import countries from "world-atlas/countries-50m.json";
import type { Topology, GeometryCollection } from "topojson-specification";
import { Crosshair, Minus, Plus, Scan, X } from "lucide-react";
import { fmtDay, money, type Assessed } from "../data/checks.ts";
import { DESTINATION } from "../data/sites.ts";
import "./map.css";

const W = 1600;
const H = 1000;
const world = feature(countries as unknown as Topology, countries.objects.countries as GeometryCollection);
// A global projection keeps overseas demo sites legible as discovery widens.
const projection = geoMercator().scale(W / (2 * Math.PI)).translate([W / 2, H / 2]);
const path = geoPath(projection);
const landPaths = (world.features as { id?: string; geometry: unknown }[]).map((f, i) => ({ key: `${f.id ?? "x"}-${i}`, iso: String(f.id ?? ""), d: path(f as never) ?? "" }));
const grat = path(geoGraticule10()) ?? "";
/** ISO 3166 alpha-2 → the numeric ids world-atlas uses, for countries that host supplier sites. */
const ISO_NUM: Record<string, string> = {
  GB: "826", IE: "372", FR: "250", DE: "276", ES: "724", IT: "380", PL: "616", NO: "578", CZ: "203",
  NL: "528", BE: "056", AT: "040", CH: "756", SE: "752", DK: "208", PT: "620",
  CA: "124", SG: "702",
};
/** svg units per km around the delivery site (conformal projection: same in every direction locally). */
const unitsPerKm = (() => {
  const a = projection([-2.5, 51.5])!;
  const b = projection([-1.5, 51.5])!;
  return Math.hypot(b[0] - a[0], b[1] - a[1]) / (111.32 * Math.cos((51.5 * Math.PI) / 180));
})();
const NICE_KM = [10, 20, 50, 100, 200, 300, 500, 1000, 2000, 5000];

/** Static base map: ocean texture, graticule, coast glow, land. Memoised so pan/zoom never re-diffs 240 country paths. */
const BaseMap = memo(function BaseMap({ hosts }: { hosts: string }) {
  const hostSet = new Set(hosts.split(","));
  return (
    <>
      <rect x={-W * 2} y={-H * 2} width={W * 5} height={H * 5} fill="#09090c" />
      <rect x={-W * 2} y={-H * 2} width={W * 5} height={H * 5} fill="url(#rs-ocean)" />
      <path d={grat} className="rs-graticule" />
      <g className="rs-coast-glow" aria-hidden="true">
        {landPaths.map((l) => <path key={l.key} d={l.d} />)}
      </g>
      <g className="rs-landmass">
        {landPaths.map((l) => <path key={l.key} d={l.d} className={hostSet.has(l.iso) ? "rs-land is-host" : "rs-land"} />)}
      </g>
    </>
  );
});

/** Independent paint layer: animated pins/sonar never invalidate the detailed geography. */
const MapBackground = memo(function MapBackground({ viewBox, hosts }: { viewBox: string; hosts: string }) {
  return (
    <svg className="rs-map-base" viewBox={viewBox} preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        {/* Ocean: a fine dot lattice that scales with zoom, giving the sea depth without noise. */}
        <pattern id="rs-ocean" width="14" height="14" patternUnits="userSpaceOnUse">
          <circle cx="7" cy="7" r="0.85" fill="rgba(244,241,234,0.07)" />
        </pattern>
        <linearGradient id="rs-land-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#22222a" />
          <stop offset="1" stopColor="#18181e" />
        </linearGradient>
        <linearGradient id="rs-land-host" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#262534" />
          <stop offset="1" stopColor="#201f29" />
        </linearGradient>
      </defs>
      <BaseMap hosts={hosts} />
    </svg>
  );
});

const LABELS: [string, number, number][] = [
  ["United Kingdom", -1.9, 54.6],
  ["Ireland", -8.1, 53.2],
  ["France", 2.4, 46.6],
  ["Germany", 10.2, 51.1],
  ["Spain", -3.8, 39.9],
  ["Italy", 12.4, 42.9],
  ["Poland", 19.3, 52.1],
  ["Norway", 9.5, 61.4],
  ["Czechia", 15.4, 49.9],
];

export type MapMode = "discovery" | "checking" | "shortlist" | "disruption";
export const xy = (lon: number, lat: number) => projection([lon, lat]) as [number, number];

type VB = [number, number, number, number];
type Pt = [number, number];
/** Zoom range from a local region to the worldwide supplier network. */
const MIN_W = W * 0.025;
const MAX_W = W * 1.5;
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
const reduced = () => typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;

function frame(points: Pt[], pad: number, aspect: number, insetRight = 0): VB {
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  let x0 = Math.min(...xs) - pad;
  let x1 = Math.max(...xs) + pad;
  let y0 = Math.min(...ys) - pad;
  const y1 = Math.max(...ys) + pad;
  let w = x1 - x0;
  let h = y1 - y0;
  // reserve room for right-side panel
  w = w / (1 - insetRight);
  x1 = x0 + w;
  if (w / h > aspect) {
    const nh = w / aspect;
    y0 -= (nh - h) / 2;
    h = nh;
  } else {
    const nw = h * aspect;
    x0 -= (nw - w) / 2 - (insetRight * nw) / 2;
    w = nw;
  }
  return [x0, y0, w, h];
}

/** Zoom a viewBox by `f` (new width = w × f) about an svg-space point, within limits. */
function zoomAt(v: VB, f: number, p: Pt): VB {
  const w = clamp(v[2] * f, MIN_W, MAX_W);
  const k = w / v[2];
  return pan([p[0] - (p[0] - v[0]) * k, p[1] - (p[1] - v[1]) * k, w, v[3] * k], 0, 0);
}
/** Shift a viewBox while keeping its centre within the world map. */
function pan(v: VB, dx: number, dy: number): VB {
  const cx = clamp(v[0] + v[2] / 2 + dx, -W * 0.15, W * 1.15);
  const cy = clamp(v[1] + v[3] / 2 + dy, -H * 0.15, H * 1.15);
  return [cx - v[2] / 2, cy - v[3] / 2, v[2], v[3]];
}

/**
 * Eased viewBox. `ms === 0` follows the target immediately (drag / pinch),
 * otherwise it glides from wherever the view currently is.
 */
function useTween(target: VB, ms: number): VB {
  const [vb, setVb] = useState<VB>(target);
  const cur = useRef<VB>(target);
  const key = target.join(",");
  useEffect(() => {
    if (ms === 0 || reduced()) {
      cur.current = target;
      setVb(target);
      return;
    }
    const from = cur.current;
    const start = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      const e = 1 - Math.pow(1 - t, 4);
      const next = from.map((v, i) => v + (target[i] - v) * e) as VB;
      cur.current = next;
      setVb(next);
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [key, ms]); // eslint-disable-line react-hooks/exhaustive-deps
  return ms === 0 ? target : vb;
}

function Pin({ a, mode, active, checking, selected, onSelect, disrupted, labelAll }: {
  a: Assessed; mode: MapMode; active: boolean; checking: boolean; selected: boolean; onSelect: () => void; disrupted: boolean; labelAll: boolean;
}) {
  const [x, y] = xy(a.site.lon, a.site.lat);
  const showRank = (mode === "shortlist" || mode === "disruption") && a.rank != null;
  const hidden = (mode === "shortlist" || mode === "disruption") && a.rank == null && !disrupted;
  const state = !active ? "pending" : a.state;
  const cls = `rs-pin is-${state}${hidden ? " is-dim" : ""}${selected ? " is-selected" : ""}`;
  const label = `${a.candidate.supplier_name.replace(" (sample)", "")}, ${a.site.city}: ${!active ? "not yet checked" : a.state}${a.rank ? `, rank ${a.rank}` : ""}`;
  const labelled = showRank || selected || (mode === "disruption" && disrupted) || (labelAll && !hidden);
  return (
    <g
      className={cls}
      transform={`translate(${x} ${y})`}
      role="button"
      tabIndex={hidden ? -1 : 0}
      aria-label={label}
      aria-pressed={selected}
      data-pin={a.candidate.candidate_id}
      onClick={onSelect}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onSelect())}
    >
      <circle r="22" fill="transparent" />
      {/* Light pool on the ground under qualified sites. */}
      {showRank || state === "eligible" ? <ellipse rx="26" ry="9" className={`rs-pin-pool${showRank ? " is-ranked" : ""}`} /> : null}
      {state === "awaiting" && !showRank ? <ellipse rx="18" ry="6" className="rs-pin-pool is-wait" /> : null}
      {selected ? <circle r="17" className="rs-pin-halo" cy={showRank ? -22 : state === "pending" || state === "excluded" ? 0 : -14} /> : null}
      {checking ? (
        <circle r="15" fill="none" stroke="url(#rs-thermal)" strokeWidth="2.2" className="rs-pin-ping">
          <animate attributeName="r" values="8;20;8" dur="1.4s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="1;0.2;1" dur="1.4s" repeatCount="indefinite" />
        </circle>
      ) : null}
      <g className="rs-pin-glyph">
        {showRank ? (
          <g>
            <path d="M0 0 C -9 -12 -14 -17 -14 -25 A 14 14 0 1 1 14 -25 C 14 -17 9 -12 0 0 Z" fill={selected ? "url(#rs-thermal)" : "#f4f1ea"} stroke="rgba(9,9,12,.6)" strokeWidth="1" />
            <text y="-20" textAnchor="middle" fontSize="13" fontWeight="650" fill="#0b0b0e" fontFamily="var(--rs-mono)">{a.rank}</text>
          </g>
        ) : state === "excluded" ? (
          <g>
            <circle r="9" fill="rgba(9,9,12,.7)" stroke={disrupted ? "#f87171" : "#8a857d"} strokeWidth="1.6" />
            <line x1="-6" y1="6" x2="6" y2="-6" stroke={disrupted ? "#f87171" : "#8a857d"} strokeWidth="1.6" />
          </g>
        ) : state === "awaiting" ? (
          <g>
            <path d="M0 0 C -6 -8 -9 -11 -9 -16 A 9 9 0 1 1 9 -16 C 9 -11 6 -8 0 0 Z" fill="rgba(9,9,12,.6)" stroke="#fbbf24" strokeWidth="2" />
            <circle cy="-16" r="3" fill="#fbbf24" />
          </g>
        ) : state === "eligible" ? (
          <path d="M0 0 C -6 -8 -9 -11 -9 -16 A 9 9 0 1 1 9 -16 C 9 -11 6 -8 0 0 Z" fill="#4ade9c" stroke="rgba(9,9,12,.5)" strokeWidth="1" />
        ) : (
          <circle r="5" fill="#f4f1ea" opacity="0.75" />
        )}
      </g>
      {labelled ? (
        <>
          <text className="rs-pin-label" x="20" y={showRank ? -20 : -8}>{a.site.city}</text>
          {selected && !showRank ? <text className="rs-pin-sub" x="20" y="10">{a.candidate.supplier_name.replace(" (sample)", "")}</text> : null}
        </>
      ) : (
        <text className="rs-pin-label rs-pin-hover" x="20" y="-8">{a.site.city}</text>
      )}
    </g>
  );
}

function routeD(from: Pt, to: Pt) {
  const mx = (from[0] + to[0]) / 2;
  const my = (from[1] + to[1]) / 2;
  const dx = to[0] - from[0];
  const dy = to[1] - from[1];
  const len = Math.hypot(dx, dy) || 1;
  const bend = Math.min(140, len * 0.22);
  const cx = mx - (dy / len) * bend;
  const cy = my + (dx / len) * bend;
  return `M ${from[0]} ${from[1]} Q ${cx} ${cy} ${to[0]} ${to[1]}`;
}

const STATE_LABEL: Record<Assessed["state"] | "pending", string> = {
  eligible: "Eligible",
  awaiting: "Awaiting evidence",
  excluded: "Excluded",
  pending: "Not yet checked",
};

export function SupplierMap({
  list,
  mode,
  checked,
  checkingId,
  selectedId,
  onSelect,
  disruptedId,
  insetRight = 0,
}: {
  list: Assessed[];
  mode: MapMode;
  checked: Set<string>;
  checkingId: string | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
  disruptedId: string | null;
  insetRight?: number;
}) {
  const box = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [size, setSize] = useState({ w: 1200, h: 750 });
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: Math.max(1, el.clientWidth), h: Math.max(1, el.clientHeight) }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const aspect = size.w / size.h;
  const narrow = typeof window !== "undefined" && window.innerWidth <= 900;
  // Split mode narrows this map independently of the browser viewport. Reserve
  // the actual 400px checks panel, not just a fraction of the original screen.
  const inset = narrow || !insetRight ? 0 : Math.min(0.72, Math.max(insetRight, 424 / size.w));
  const dest = useMemo(() => xy(DESTINATION.lon, DESTINATION.lat), []);
  const signature = list.map(a => a.candidate.candidate_id).join("|");
  const [revealed, setRevealed] = useState({ signature: "", count: 0 });
  useEffect(() => {
    if (reduced()) { setRevealed({ signature, count: list.length }); return; }
    setRevealed({ signature, count: 0 });
    if (!list.length) return;
    let count = 0;
    const timer = window.setInterval(() => {
      count += 1;
      setRevealed({ signature, count });
      if (count >= list.length) window.clearInterval(timer);
    }, 160);
    return () => window.clearInterval(timer);
  }, [signature]); // eslint-disable-line react-hooks/exhaustive-deps
  const visible = useMemo(() => list.slice(0, revealed.signature === signature ? revealed.count : 0), [list, signature, revealed]);
  const auto = useMemo<VB>(() => {
    if (mode === "shortlist" || mode === "disruption") {
      const pts = list.filter((a) => a.rank != null || a.candidate.candidate_id === disruptedId).map((a) => xy(a.site.lon, a.site.lat));
      return frame([...pts, dest], 28, aspect, inset);
    }
    // Start one smooth zoom as the result batch arrives. Staggered pin reveals
    // must not restart the 1.1-second camera tween every 160 ms.
    const pts = list.map((a) => xy(a.site.lon, a.site.lat));
    return frame([...pts, dest], 44, aspect, inset);
  }, [list, mode, aspect, inset, disruptedId, dest]);

  // ---- User camera: null = automatic framing for the current stage ----
  const [user, setUser] = useState<VB | null>(null);
  const [instant, setInstant] = useState(false);
  const [open, setOpen] = useState<string | null>(null); // candidate id, "dest", or null
  useEffect(() => { setUser(null); setInstant(false); }, [mode]);
  useEffect(() => { if (mode === "discovery") setOpen(null); }, [mode]);
  const vb = useTween(user ?? auto, instant ? 0 : user ? 420 : 1100);
  const live = useRef(vb);
  live.current = vb;
  const go = useCallback((next: VB, now = false) => { setInstant(now); setUser(next); }, []);

  // Screen ↔ svg mapping for preserveAspectRatio="xMidYMid slice".
  const s = Math.max(size.w / vb[2], size.h / vb[3]);
  const ox = (size.w - vb[2] * s) / 2;
  const oy = (size.h - vb[3] * s) / 2;
  const toScreen = (p: Pt): Pt => [(p[0] - vb[0]) * s + ox, (p[1] - vb[1]) * s + oy];
  const toSvg = useCallback((clientX: number, clientY: number): Pt => {
    const r = box.current!.getBoundingClientRect();
    const v = live.current;
    const sc = Math.max(r.width / v[2], r.height / v[3]);
    return [(clientX - r.left - (r.width - v[2] * sc) / 2) / sc + v[0], (clientY - r.top - (r.height - v[3] * sc) / 2) / sc + v[1]];
  }, []);
  /** Centre of the visible map (left of any side panel), in screen px. */
  const viewCentre = (): Pt => [(size.w * (1 - inset)) / 2, size.h / 2];
  const zoomBy = (f: number) => {
    const r = box.current!.getBoundingClientRect();
    const [cx, cy] = viewCentre();
    go(zoomAt(live.current, f, toSvg(r.left + cx, r.top + cy)));
  };
  const reset = () => { setInstant(false); setUser(null); };
  const focusOn = (p: Pt) => {
    // Centre a point in the visible area at a comfortable zoom.
    const v = live.current;
    const w = Math.min(v[2], W * 0.32);
    const h = w * (v[3] / v[2]);
    const shift = (inset * w) / 2; // keep the point left of the side panel
    go(pan([p[0] - w / 2 + shift, p[1] - h / 2, w, h], 0, 0));
  };

  // ---- Wheel zoom (cursor-anchored), drag pan, pinch zoom, click-vs-drag ----
  const pointers = useRef(new Map<number, Pt>());
  const gesture = useRef<{ moved: boolean; start: Pt; pinch?: { d: number; v: VB; mid: Pt } } | null>(null);
  const suppressClick = useRef(false);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const speed = e.ctrlKey ? 0.012 : e.deltaMode === 1 ? 0.05 : 0.0018;
      const f = Math.exp(e.deltaY * speed);
      setInstant(true);
      setUser(zoomAt(live.current, f, toSvg(e.clientX, e.clientY)));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [toSvg]);

  const onPointerDown = (e: React.PointerEvent) => {
    if ((e.target as Element).closest(".rs-map-ui")) return;
    suppressClick.current = false;
    pointers.current.set(e.pointerId, [e.clientX, e.clientY]);
    if (pointers.current.size === 1) gesture.current = { moved: false, start: [e.clientX, e.clientY] };
    if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      const mid: Pt = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
      gesture.current = { moved: true, start: mid, pinch: { d: Math.hypot(a[0] - b[0], a[1] - b[1]), v: live.current, mid: toSvg(...mid) } };
      box.current!.setPointerCapture(e.pointerId);
    }
  };
  const onPointerMove = (e: React.PointerEvent) => {
    const prev = pointers.current.get(e.pointerId);
    const g = gesture.current;
    if (!prev || !g) return;
    pointers.current.set(e.pointerId, [e.clientX, e.clientY]);
    if (g.pinch && pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      go(zoomAt(g.pinch.v, g.pinch.d / Math.max(1, d), g.pinch.mid), true);
      return;
    }
    if (!g.moved && Math.hypot(e.clientX - g.start[0], e.clientY - g.start[1]) < 5) return;
    if (!g.moved) {
      // Only capture once it is really a drag, so plain clicks still reach the pins.
      g.moved = true;
      box.current!.setPointerCapture(e.pointerId);
      box.current!.dataset.dragging = "1";
    }
    const v = live.current;
    const r = box.current!.getBoundingClientRect();
    const sc = Math.max(r.width / v[2], r.height / v[3]);
    go(pan(v, -(e.clientX - prev[0]) / sc, -(e.clientY - prev[1]) / sc), true);
  };
  const endPointer = (e: React.PointerEvent) => {
    pointers.current.delete(e.pointerId);
    if (pointers.current.size === 0) {
      suppressClick.current = !!gesture.current?.moved;
      gesture.current = null;
      if (box.current) delete box.current.dataset.dragging;
    }
  };

  const pick = (id: string) => {
    if (suppressClick.current) return;
    setOpen(id);
    if (id !== "dest") onSelect(id);
  };

  // Keyboard on the focused map: +/- zoom, arrows pan, 0 resets, Esc closes the card.
  const onKeyDown = (e: React.KeyboardEvent) => {
    if ((e.target as Element).closest(".rs-map-card")) return;
    const v = live.current;
    const step = v[2] * 0.12;
    const keys: Record<string, () => void> = {
      "+": () => zoomBy(0.7), "=": () => zoomBy(0.7), "-": () => zoomBy(1 / 0.7), _: () => zoomBy(1 / 0.7), "0": reset,
      ArrowLeft: () => go(pan(v, -step, 0)), ArrowRight: () => go(pan(v, step, 0)),
      ArrowUp: () => go(pan(v, 0, -step)), ArrowDown: () => go(pan(v, 0, step)),
      Escape: () => setOpen(null),
    };
    const fn = keys[e.key];
    if (fn) { e.preventDefault(); fn(); }
  };

  const scale = vb[2] / W;
  const glyph = Math.max(0.1, scale * 1.4);
  const labelAll = vb[2] < W * 0.42 && mode !== "discovery";
  const routes = (mode === "shortlist" || mode === "disruption")
    ? list.filter((a) => a.rank != null || a.candidate.candidate_id === disruptedId)
    : [];
  const zoomPct = Math.round((auto[2] / vb[2]) * 100);
  const hosts = useMemo(() => [...new Set(list.map((a) => ISO_NUM[a.site.countryCode]).filter(Boolean))].sort().join(","), [list]);
  // Scale bar: the largest round distance that fits in ~120 screen px.
  const pxPerKm = unitsPerKm * s;
  const km = [...NICE_KM].reverse().find((k) => k * pxPerKm <= 120) ?? NICE_KM[0];
  const openA = open && open !== "dest" ? list.find((a) => a.candidate.candidate_id === open) ?? null : null;
  const openPt: Pt | null = open === "dest" ? dest : openA ? xy(openA.site.lon, openA.site.lat) : null;
  // The card must stay clear of whichever side panel is actually showing.
  // Wide: panels sit on the right. Narrow: they are bottom sheets, so clip the height instead.
  let visibleW = size.w * (1 - inset);
  let visibleH = size.h;
  if (openPt && box.current) {
    const panel = box.current.closest(".rs-studio")?.querySelector(".rs-check-panel, .rs-drawer");
    const pr = panel?.getBoundingClientRect();
    const br = box.current.getBoundingClientRect();
    if (pr && pr.width) {
      if (narrow) visibleH = Math.min(size.h, pr.top - br.top);
      else visibleW = Math.min(size.w, pr.left - br.left);
    }
  }

  return (
    <div
      className="rs-map"
      ref={box}
      tabIndex={0}
      role="application"
      aria-label="Supplier map. Drag to pan, scroll or pinch to zoom, +/- keys zoom, 0 resets, select a pin for details."
      data-visible-suppliers={visible.length}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endPointer}
      onPointerCancel={endPointer}
      onClickCapture={(e) => {
        // A drag that ends over a pin must not count as a click on it.
        if (suppressClick.current) { e.stopPropagation(); suppressClick.current = false; }
      }}
      onDoubleClick={(e) => {
        if ((e.target as Element).closest(".rs-map-ui, .rs-pin")) return;
        go(zoomAt(live.current, 0.5, toSvg(e.clientX, e.clientY)));
      }}
      onKeyDown={onKeyDown}
    >
      <MapBackground viewBox={vb.join(" ")} hosts={hosts} />
      <svg
        className="rs-map-overlay"
        ref={svgRef}
        viewBox={vb.join(" ")}
        preserveAspectRatio="xMidYMid slice"
        aria-labelledby="rs-map-title"
        onClick={(e) => { if (!(e.target as Element).closest(".rs-pin, .rs-route-hit, .rs-dest")) setOpen(null); }}
      >
        <title id="rs-map-title">Supplier sites and delivery destination</title>
        <defs>
          <linearGradient id="rs-thermal" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#38bdf8" />
            <stop offset="0.4" stopColor="#8b5cf6" />
            <stop offset="0.72" stopColor="#ec4899" />
            <stop offset="1" stopColor="#fb923c" />
          </linearGradient>
          <radialGradient id="rs-vignette" cx="50%" cy="45%" r="75%">
            <stop offset="55%" stopColor="#09090c" stopOpacity="0" />
            <stop offset="100%" stopColor="#09090c" stopOpacity="0.92" />
          </radialGradient>
          <marker id="rs-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0 0 L10 5 L0 10 z" fill="#f4f1ea" />
          </marker>
          <marker id="rs-arrow-bad" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0 0 L10 5 L0 10 z" fill="#f87171" />
          </marker>
          <radialGradient id="rs-pool-ok">
            <stop offset="0" stopColor="#4ade9c" stopOpacity="0.55" />
            <stop offset="1" stopColor="#4ade9c" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="rs-pool-rank">
            <stop offset="0" stopColor="#f4f1ea" stopOpacity="0.5" />
            <stop offset="1" stopColor="#8b5cf6" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="rs-pool-wait">
            <stop offset="0" stopColor="#fbbf24" stopOpacity="0.4" />
            <stop offset="1" stopColor="#fbbf24" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="rs-beacon">
            <stop offset="0" stopColor="#f4f1ea" stopOpacity="0.35" />
            <stop offset="0.4" stopColor="#8b5cf6" stopOpacity="0.12" />
            <stop offset="1" stopColor="#8b5cf6" stopOpacity="0" />
          </radialGradient>
        </defs>
        {/* Discovery: sonar rings sweeping out from the delivery site. */}
        {mode === "discovery" ? (
          <g transform={`translate(${dest[0]} ${dest[1]})`} className="rs-sonar" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <circle key={i} r="0" stroke="url(#rs-thermal)">
                <animate attributeName="r" values={`0;${W * 0.55}`} dur="3.6s" begin={`${i * 1.2}s`} repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.7;0" dur="3.6s" begin={`${i * 1.2}s`} repeatCount="indefinite" />
              </circle>
            ))}
          </g>
        ) : null}
        {(mode === "shortlist" || mode === "disruption" || vb[2] < W * 0.7) &&
          LABELS.map(([n, lon, lat]) => {
            const [x, y] = xy(lon, lat);
            return (
              <text key={n} x={x} y={y} className="rs-country-label" textAnchor="middle" style={{ fontSize: 11 * scale * 1.6 }}>
                {n}
              </text>
            );
          })}
        {routes.map((a) => {
          const id = a.candidate.candidate_id;
          const from = xy(a.site.lon, a.site.lat);
          const d = routeD(from, dest);
          const isBad = id === disruptedId;
          const isSel = id === selectedId;
          return (
            <g key={`r-${id}`}>
              {isSel || isBad ? <path d={d} className="rs-route-glow" stroke={isBad ? "#f87171" : "url(#rs-thermal)"} /> : null}
              <path d={d} className="rs-route is-schematic" stroke={isBad ? "#f87171" : isSel ? "url(#rs-thermal)" : "rgba(244,241,234,.55)"} markerEnd={isBad ? "url(#rs-arrow-bad)" : "url(#rs-arrow)"} />
              {isSel || isBad ? <path d={d} className="rs-route-flow" stroke={isBad ? "#f87171" : "url(#rs-thermal)"} /> : null}
              {isSel && !isBad && !reduced() ? (
                <circle r={4 * glyph} className="rs-comet">
                  <animateMotion dur="2.4s" repeatCount="indefinite" path={d} />
                </circle>
              ) : null}
              <path d={d} className="rs-route-hit" onClick={() => pick(id)} aria-hidden="true">
                <title>{`${a.site.city} → ${DESTINATION.short} · est. ${fmtDay(a.arrival)}`}</title>
              </path>
            </g>
          );
        })}
        <g
          className="rs-dest"
          transform={`translate(${dest[0]} ${dest[1]}) scale(${glyph})`}
          role="button"
          tabIndex={0}
          aria-label={`Destination: ${DESTINATION.name}`}
          onClick={() => pick("dest")}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), pick("dest"))}
        >
          <circle r="16" fill="transparent" />
          <circle r="46" fill="url(#rs-beacon)" pointerEvents="none" />
          <circle r="10" className="rs-dest-ring" />
          <circle r="10" className="rs-dest-ring is-late" />
          <rect x="-6" y="-6" width="12" height="12" fill="#f4f1ea" stroke="#09090c" strokeWidth="1.5" />
          <text className="rs-pin-label" x="14" y="5">{DESTINATION.short}</text>
        </g>
        {visible.map((a) => {
          const [x, y] = xy(a.site.lon, a.site.lat);
          const id = a.candidate.candidate_id;
          return (
            <g key={id} transform={`translate(${x} ${y}) scale(${glyph}) translate(${-x} ${-y})`}>
              <Pin
                a={a}
                mode={mode}
                active={checked.has(id)}
                checking={checkingId === id}
                selected={selectedId === id || open === id}
                onSelect={() => pick(id)}
                disrupted={disruptedId === id}
                labelAll={labelAll}
              />
            </g>
          );
        })}
        <rect x={vb[0]} y={vb[1]} width={vb[2]} height={vb[3]} fill="url(#rs-vignette)" pointerEvents="none" />
      </svg>

      {openPt ? (
        <InfoCard
          key={open!}
          at={toScreen(openPt)}
          bounds={{ w: visibleW, h: visibleH }}
          a={openA}
          active={openA ? checked.has(openA.candidate.candidate_id) : true}
          disrupted={!!openA && openA.candidate.candidate_id === disruptedId}
          onClose={() => setOpen(null)}
          onZoom={() => focusOn(openPt)}
        />
      ) : null}

      <div className="rs-map-ui rs-map-zoom" role="toolbar" aria-label="Map zoom">
        <button type="button" onClick={() => zoomBy(0.6)} aria-label="Zoom in" title="Zoom in (+)"><Plus size={16} /></button>
        <span className="rs-map-pct" aria-live="polite">{zoomPct}%</span>
        <button type="button" onClick={() => zoomBy(1 / 0.6)} aria-label="Zoom out" title="Zoom out (−)"><Minus size={16} /></button>
        <i />
        <button type="button" onClick={reset} aria-label="Fit all sites" title="Fit all sites (0)" aria-pressed={!user}><Scan size={15} /></button>
      </div>
      <div className="rs-map-ui rs-map-scale" aria-label={`Scale: ${km} kilometres`}>
        <i style={{ width: Math.round(km * pxPerKm) }} />
        <span>{km} km</span>
      </div>
    </div>
  );
}

function InfoCard({ at, bounds, a, active, disrupted, onClose, onZoom }: {
  at: Pt;
  bounds: { w: number; h: number };
  a: Assessed | null;
  active: boolean;
  disrupted: boolean;
  onClose: () => void;
  onZoom: () => void;
}) {
  const CW = 290;
  const CH = a ? 236 : 120;
  // Prefer right of the pin; flip left near the panel edge; keep inside the map.
  const right = at[0] + 22 + CW < bounds.w - 12;
  const left = right ? at[0] + 22 : at[0] - 22 - CW;
  const top = clamp(at[1] - CH / 2, 76, Math.max(76, bounds.h - CH - 16));
  const offscreen = at[0] < -40 || at[0] > bounds.w + 40 || at[1] < -40 || at[1] > bounds.h + 40;
  // No room (phone with a bottom sheet open): the sheet already shows this site's details.
  if (offscreen || bounds.h < CH + 92) return null;
  const state = a ? (active ? a.state : "pending") : null;
  return (
    <div
      className="rs-map-ui rs-map-card"
      style={{ left: clamp(left, 12, Math.max(12, bounds.w - CW - 12)), top, width: CW }}
      role="dialog"
      aria-label={a ? `${a.candidate.supplier_name} details` : "Delivery destination"}
      onKeyDown={(e) => e.key === "Escape" && onClose()}
    >
      <div className="rs-map-card-head">
        {a ? (
          <span className={`rs-map-chip is-${state}${disrupted ? " is-bad" : ""}`}>
            {a.rank ? `#${a.rank} · ` : ""}{disrupted ? "Disrupted" : STATE_LABEL[state!]}
          </span>
        ) : <span className="rs-map-chip is-dest">Delivery site</span>}
        <button type="button" className="rs-map-x" onClick={onClose} aria-label="Close"><X size={14} /></button>
      </div>
      {a ? (
        <>
          <b className="rs-map-card-title">{a.candidate.supplier_name.replace(" (sample)", "")}</b>
          <span className="rs-map-card-sub">{a.site.city}, {a.candidate.country} · {a.site.siteType}</span>
          <p className="rs-map-card-note">
            {!active ? "Checks for this site haven't run yet." : a.state === "eligible" ? "All mandatory checks passed on demo evidence." : a.reason}
          </p>
          <dl className="rs-map-card-kv">
            <div><dt>Est. arrival</dt><dd>{active ? fmtDay(a.arrival) : "—"}</dd></div>
            <div><dt>Price</dt><dd>{money(a.candidate.price, a.candidate.currency ?? "GBP")} <small>est.</small></dd></div>
            <div><dt>Source</dt><dd>{a.site.sourceLabel}</dd></div>
          </dl>
        </>
      ) : (
        <>
          <b className="rs-map-card-title">{DESTINATION.name}</b>
          <span className="rs-map-card-sub">Where the replacement part is delivered</span>
        </>
      )}
      <button type="button" className="rs-map-card-zoom" onClick={onZoom}><Crosshair size={13} /> Zoom to {a ? a.site.city : DESTINATION.short}</button>
    </div>
  );
}
