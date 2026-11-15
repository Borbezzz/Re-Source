import { useEffect, useId, useRef, useState } from "react";
import { dateLabel, type RiskObservation } from "./types.ts";

const day = (value: string | null) => Date.parse(value!.slice(0, 10) + "T12:00:00Z") / 86400000;
const COLORS = ["#7dd3fc", "#fbbf24", "#c4b5fd", "#4ade9c"];

export function ArrivalTimeline({ observations, deadline }: { observations: RiskObservation[]; deadline: string }) {
  const titleId = useId();
  const uid = titleId.replace(/[^a-zA-Z0-9]/g, "");
  const chart = useRef<SVGSVGElement>(null);
  const [width, setWidth] = useState(560);
  const points = observations.filter((o) => o.evidence.issued_on && o.evidence.arrival_on && ["quote", "shipment", "delivery"].includes(o.evidence.kind)).sort((a, b) => a.evidence.issued_on!.localeCompare(b.evidence.issued_on!));
  useEffect(() => {
    if (!chart.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, Math.round(entry.contentRect.width))));
    observer.observe(chart.current);
    return () => observer.disconnect();
  }, [points.length]);
  if (points.length < 2) return <div className="rs-risk-chart-empty">
    <svg className="rs-risk-chart-ghost" viewBox="0 0 240 64" aria-hidden="true"><path d="M8 50 C 60 46, 90 30, 130 34 S 200 14, 232 12" /><line x1="8" x2="232" y1="26" y2="26" /><circle cx="130" cy="34" r="4" /></svg>
    <strong>Arrival timeline is waiting for evidence</strong><p>{points.length ? "One dated arrival is recorded." : "No dated arrivals are recorded."} Add another dated quote or shipment update to see what shifted against the deadline.</p>
  </div>;
  const due = day(deadline);
  const xmin = Math.min(...points.map((o) => day(o.evidence.issued_on)));
  const xmax = Math.max(xmin + 1, ...points.map((o) => day(o.evidence.issued_on)));
  const ymin = Math.min(due, ...points.map((o) => day(o.evidence.arrival_on!))) - 2;
  const ymax = Math.max(due, ...points.map((o) => day(o.evidence.arrival_on!))) + 2;
  const right = width - 24;
  const x = (d: number) => 66 + (d - xmin) / (xmax - xmin) * (right - 66);
  const y = (d: number) => 210 - (d - ymin) / (ymax - ymin) * 160;
  const suppliers = [...new Set(points.map((o) => o.evidence.supplier ?? "Supplier unknown"))];
  const late = Math.max(0, y(due) - 36);
  return <figure className="rs-risk-chart">
    <figcaption id={titleId}>Quoted arrival vs. project deadline</figcaption>
    <svg ref={chart} viewBox={`0 0 ${width} 270`} role="img" aria-labelledby={titleId}>
      <desc>{points.map((o) => `${o.evidence.supplier ?? "Unknown supplier"}, source ${o.evidence.issued_on}, arrival ${o.evidence.arrival_on}: ${o.evidence.event ?? o.evidence.title}. ${o.applies_because}`).join(" ")}</desc>
      <defs>
        <linearGradient id={`late-${uid}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#f87171" stopOpacity=".16" /><stop offset="1" stopColor="#f87171" stopOpacity=".02" /></linearGradient>
        <linearGradient id={`safe-${uid}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#4ade9c" stopOpacity=".05" /><stop offset="1" stopColor="#4ade9c" stopOpacity="0" /></linearGradient>
        {suppliers.map((_, i) => <linearGradient key={i} id={`area-${uid}-${i}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={COLORS[i % COLORS.length]} stopOpacity=".22" /><stop offset="1" stopColor={COLORS[i % COLORS.length]} stopOpacity="0" /></linearGradient>)}
        <filter id={`glow-${uid}`} x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="3.2" /></filter>
      </defs>
      <rect x="66" y="36" width={right - 66} height={late} fill={`url(#late-${uid})`} rx="4" />
      <rect x="66" y={y(due)} width={right - 66} height={Math.max(0, 210 - y(due))} fill={`url(#safe-${uid})`} />
      {late > 18 ? <text className="rs-chart-zone" x="74" y="50">Late zone</text> : null}
      {[ymin, (ymin + ymax) / 2, ymax].map((d) => <g key={d}><line x1="66" x2={right} y1={y(d)} y2={y(d)} stroke="var(--rs-line)" strokeDasharray="2 4" /><text x="56" y={y(d) + 4} textAnchor="end">{dateLabel(new Date(d * 86400000).toISOString())}</text></g>)}
      <line x1="66" x2={right} y1={y(due)} y2={y(due)} stroke="#f87171" strokeOpacity=".35" strokeWidth="6" filter={`url(#glow-${uid})`} />
      <line className="rs-chart-due" x1="66" x2={right} y1={y(due)} y2={y(due)} stroke="var(--rs-bad)" strokeDasharray="5 4" />
      <text x={right} y={y(due) - 9} textAnchor="end" fill="var(--rs-bad)">Need by {dateLabel(deadline)}</text>
      {suppliers.map((supplier, index) => {
        const color = COLORS[index % COLORS.length];
        const group = points.filter((o) => (o.evidence.supplier ?? "Supplier unknown") === supplier);
        const coords = group.map((o) => [x(day(o.evidence.issued_on)), y(day(o.evidence.arrival_on!))] as const);
        const line = coords.map(([a, b]) => `${a},${b}`).join(" ");
        return <g key={supplier} className="rs-chart-series" style={{ animationDelay: `${index * 120}ms` }}>
          {coords.length > 1 ? <polygon points={`${coords[0][0]},210 ${line} ${coords[coords.length - 1][0]},210`} fill={`url(#area-${uid}-${index})`} className="rs-chart-area" /> : null}
          {coords.length > 1 ? <polyline points={line} fill="none" stroke={color} strokeWidth="5" strokeOpacity=".45" filter={`url(#glow-${uid})`} /> : null}
          <polyline points={line} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" pathLength={1} className="rs-chart-line" />
          {group.map((o) => {
            const cx = x(day(o.evidence.issued_on)), cy = y(day(o.evidence.arrival_on!));
            return <g key={o.evidence.evidence_id} className={`rs-chart-point is-${o.level}`}>
              {o.level === "alert" ? <circle className="rs-chart-ping" cx={cx} cy={cy} r="5" stroke={color} fill="none" /> : null}
              <circle cx={cx} cy={cy} r="9" fill={color} opacity=".14" />
              <circle cx={cx} cy={cy} r="5" stroke={color} strokeWidth="2" fill={o.level === "watchlist" ? "var(--rs-panel-solid)" : color}><title>{o.evidence.title}: {o.evidence.event ?? o.applies_because}</title></circle>
              {o.evidence.event ? <text x={cx} y={cy + (o.level === "watchlist" ? 22 : -14)} textAnchor={cx > width / 2 ? "end" : "start"} fill={color} className="rs-chart-tag">{/backorder/i.test(o.evidence.event) ? "Backorder" : o.level === "watchlist" ? "Scope unverified" : "Revised estimate"}</text> : null}
            </g>;
          })}
        </g>;
      })}
      <text x="66" y="235">{dateLabel(new Date(xmin * 86400000).toISOString())}</text><text x={right} y="235" textAnchor="end">{dateLabel(new Date(xmax * 86400000).toISOString())}</text>
      <text x={width / 2 + 20} y="259" textAnchor="middle" className="rs-chart-axis">Date of source document</text>
      <text x="66" y="20" className="rs-chart-axis">Estimated arrival</text>
    </svg>
    <div className="rs-risk-legend">{suppliers.map((s, i) => <span key={s}><i style={{ background: COLORS[i % COLORS.length], boxShadow: `0 0 8px ${COLORS[i % COLORS.length]}` }} />{s}</span>)}<span><i className="is-hollow" />Hollow point: scope unverified</span></div>
    <details><summary>Timeline data and events</summary><div className="rs-risk-table-scroll"><table><thead><tr><th>Source date</th><th>Supplier</th><th>Arrival</th><th>What changed</th></tr></thead><tbody>{points.map((o) => <tr key={o.evidence.evidence_id}><td>{dateLabel(o.evidence.issued_on)}</td><td>{o.evidence.supplier ?? "Unknown"}</td><td>{dateLabel(o.evidence.arrival_on!)}</td><td>{o.evidence.event ?? o.evidence.title}</td></tr>)}</tbody></table></div></details>
  </figure>;
}
