import { useEffect, useMemo, useRef, useState } from "react";
import { geoConicConformal, geoGraticule10, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import countries from "world-atlas/countries-50m.json";
import type { Topology, GeometryCollection } from "topojson-specification";
import type { Assessed } from "../data/checks.ts";
import { DESTINATION } from "../data/sites.ts";

const W = 1600;
const H = 1000;
const world = feature(countries as unknown as Topology, countries.objects.countries as GeometryCollection);
const projection = geoConicConformal()
  .rotate([-8, 0])
  .parallels([38, 62])
  .fitExtent(
    [
      [0, 0],
      [W, H],
    ],
    {
      type: "Feature",
      properties: {},
      geometry: { type: "MultiPoint", coordinates: [[-12, 35], [26, 35], [-12, 63], [26, 63]] },
    } as never,
  );
const path = geoPath(projection);
const landPaths = (world.features as { id?: string; geometry: unknown }[]).map((f, i) => ({ id: `${f.id ?? "x"}-${i}`, d: path(f as never) ?? "" }));
const grat = path(geoGraticule10()) ?? "";

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
function frame(points: [number, number][], pad: number, aspect: number, insetRight = 0): VB {
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  let x0 = Math.min(...xs) - pad;
  let x1 = Math.max(...xs) + pad;
  let y0 = Math.min(...ys) - pad;
  let y1 = Math.max(...ys) + pad;
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

function useTween(target: VB, ms = 1100): VB {
  const [vb, setVb] = useState<VB>(target);
  const from = useRef<VB>(target);
  const cur = useRef<VB>(target);
  useEffect(() => {
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    from.current = cur.current;
    const start = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const t = reduce ? 1 : Math.min(1, (now - start) / ms);
      const e = 1 - Math.pow(1 - t, 4);
      const next = from.current.map((v, i) => v + (target[i] - v) * e) as VB;
      cur.current = next;
      setVb(next);
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target.join(","), ms]); // eslint-disable-line react-hooks/exhaustive-deps
  return vb;
}

function Pin({ a, mode, active, checking, selected, onSelect, disrupted }: {
  a: Assessed; mode: MapMode; active: boolean; checking: boolean; selected: boolean; onSelect: () => void; disrupted: boolean;
}) {
  const [x, y] = xy(a.site.lon, a.site.lat);
  const showRank = (mode === "shortlist" || mode === "disruption") && a.rank != null;
  const hidden = (mode === "shortlist" || mode === "disruption") && a.rank == null && !disrupted;
  const state = !active ? "pending" : a.state;
  const cls = `rs-pin is-${state}${hidden ? " is-dim" : ""}`;
  const label = `${a.candidate.supplier_name.replace(" (sample)", "")}, ${a.site.city}: ${!active ? "not yet checked" : a.state}${a.rank ? `, rank ${a.rank}` : ""}`;
  return (
    <g
      className={cls}
      transform={`translate(${x} ${y})`}
      role="button"
      tabIndex={hidden ? -1 : 0}
      aria-label={label}
      aria-pressed={selected}
      onClick={onSelect}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onSelect())}
    >
      <circle r="22" fill="transparent" />
      {checking ? (
        <circle r="15" fill="none" stroke="url(#rs-thermal)" strokeWidth="2.2" className="rs-pin-ping">
          <animate attributeName="r" values="8;20;8" dur="1.4s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="1;0.2;1" dur="1.4s" repeatCount="indefinite" />
        </circle>
      ) : null}
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
      {(showRank || selected || (mode === "disruption" && disrupted)) && (
        <>
          <text className="rs-pin-label" x="20" y={showRank ? -20 : -8}>{a.site.city}</text>
          {selected && !showRank ? <text className="rs-pin-sub" x="20" y="10">{a.candidate.supplier_name.replace(" (sample)", "")}</text> : null}
        </>
      )}
    </g>
  );
}

function routeD(from: [number, number], to: [number, number]) {
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
  const [aspect, setAspect] = useState(1.6);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setAspect(el.clientWidth / Math.max(1, el.clientHeight)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const dest = xy(DESTINATION.lon, DESTINATION.lat);
  const target = useMemo<VB>(() => {
    const narrow = (box.current?.clientWidth ?? 1200) < 800;
    const inset = narrow ? 0 : insetRight;
    if (mode === "shortlist" || mode === "disruption") {
      const pts = list.filter((a) => a.rank != null || a.candidate.candidate_id === disruptedId).map((a) => xy(a.site.lon, a.site.lat));
      return frame([...pts, dest], 150, aspect, inset);
    }
    const pts = list.map((a) => xy(a.site.lon, a.site.lat));
    return frame([...pts, dest], 120, aspect, inset);
  }, [list, mode, aspect, insetRight, disruptedId, dest]);
  const vb = useTween(target);
  const scale = vb[2] / W;
  const routes = (mode === "shortlist" || mode === "disruption")
    ? list.filter((a) => a.rank != null || a.candidate.candidate_id === disruptedId)
    : [];

  return (
    <div className="rs-map" ref={box}>
      <svg viewBox={vb.join(" ")} preserveAspectRatio="xMidYMid slice" aria-labelledby="rs-map-title">
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
        </defs>
        <rect x={-W} y={-H} width={W * 3} height={H * 3} fill="#0b0b0f" />
        <path d={grat} className="rs-graticule" />
        <g>
          {landPaths.map((l, i) => (
            <path key={`${l.id}-${i}`} d={l.d} className="rs-land" />
          ))}
        </g>
        {(mode === "shortlist" || mode === "disruption") &&
          LABELS.map(([n, lon, lat]) => {
            const [x, y] = xy(lon, lat);
            return (
              <text key={n} x={x} y={y} className="rs-country-label" textAnchor="middle" style={{ fontSize: 11 * scale * 1.6 }}>
                {n}
              </text>
            );
          })}
        {routes.map((a) => {
          const from = xy(a.site.lon, a.site.lat);
          const d = routeD(from, dest);
          const isBad = a.candidate.candidate_id === disruptedId;
          const isSel = a.candidate.candidate_id === selectedId;
          return (
            <g key={`r-${a.candidate.candidate_id}`}>
              <path d={d} className="rs-route is-schematic" stroke={isBad ? "#f87171" : isSel ? "url(#rs-thermal)" : "rgba(244,241,234,.55)"} markerEnd={isBad ? "url(#rs-arrow-bad)" : "url(#rs-arrow)"} />
              {isSel || isBad ? <path d={d} className="rs-route-flow" stroke={isBad ? "#f87171" : "url(#rs-thermal)"} /> : null}
            </g>
          );
        })}
        <g transform={`translate(${dest[0]} ${dest[1]}) scale(${Math.max(0.6, scale * 1.4)})`} aria-label={`Destination: ${DESTINATION.name}`}>
          <rect x="-6" y="-6" width="12" height="12" fill="#f4f1ea" stroke="#09090c" strokeWidth="1.5" />
          <text className="rs-pin-label" x="14" y="5">{DESTINATION.short}</text>
        </g>
        {list.map((a) => (
          <g key={a.candidate.candidate_id} transform={`translate(0 0)`}>
            <g style={{ transform: `scale(1)` }}>
              <ScaledPin scale={Math.max(0.55, scale * 1.4)}>
                <Pin
                  a={a}
                  mode={mode}
                  active={checked.has(a.candidate.candidate_id)}
                  checking={checkingId === a.candidate.candidate_id}
                  selected={selectedId === a.candidate.candidate_id}
                  onSelect={() => onSelect(a.candidate.candidate_id)}
                  disrupted={disruptedId === a.candidate.candidate_id}
                />
              </ScaledPin>
            </g>
          </g>
        ))}
        <rect x={vb[0]} y={vb[1]} width={vb[2]} height={vb[3]} fill="url(#rs-vignette)" pointerEvents="none" />
      </svg>
    </div>
  );
}

/** Keeps pin glyphs a constant on-screen size while the map zooms. */
function ScaledPin({ scale, children }: { scale: number; children: React.ReactElement<{ a: Assessed }> }) {
  const a = children.props.a;
  const [x, y] = xy(a.site.lon, a.site.lat);
  return (
    <g transform={`translate(${x} ${y}) scale(${scale}) translate(${-x} ${-y})`}>{children}</g>
  );
}
