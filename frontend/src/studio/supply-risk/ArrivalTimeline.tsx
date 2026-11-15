import { useId } from "react";
import { dateLabel, type RiskObservation } from "./types.ts";

const day = (value: string | null) => Date.parse(value!.slice(0, 10) + "T12:00:00Z") / 86400000;
export function ArrivalTimeline({ observations, deadline }: { observations: RiskObservation[]; deadline: string }) {
  const titleId = useId();
  const points = observations.filter((o) => o.evidence.issued_on && o.evidence.arrival_on && ["quote", "shipment", "delivery"].includes(o.evidence.kind)).sort((a, b) => a.evidence.issued_on!.localeCompare(b.evidence.issued_on!));
  if (points.length < 2) return <div className="rs-risk-chart-empty"><strong>Arrival timeline is waiting for evidence</strong><p>{points.length ? "One dated arrival is recorded." : "No dated arrivals are recorded."} Add another dated quote or shipment update to see what shifted against the deadline.</p></div>;
  const due = day(deadline);
  const xmin = Math.min(...points.map((o) => day(o.evidence.issued_on)));
  const xmax = Math.max(xmin + 1, ...points.map((o) => day(o.evidence.issued_on)));
  const ymin = Math.min(due, ...points.map((o) => day(o.evidence.arrival_on!))) - 2;
  const ymax = Math.max(due, ...points.map((o) => day(o.evidence.arrival_on!))) + 2;
  const x = (d: number) => 76 + (d - xmin) / (xmax - xmin) * 420;
  const y = (d: number) => 210 - (d - ymin) / (ymax - ymin) * 160;
  const suppliers = [...new Set(points.map((o) => o.evidence.supplier ?? "Supplier unknown"))];
  const colors = ["#7dd3fc", "#fbbf24", "#c4b5fd", "#4ade9c"];
  return <figure className="rs-risk-chart">
    <figcaption id={titleId}>Quoted arrival vs. project deadline</figcaption>
    <svg viewBox="0 0 560 270" role="img" aria-labelledby={titleId}>
      <desc>{points.map((o) => `${o.evidence.supplier ?? "Unknown supplier"}, source ${o.evidence.issued_on}, arrival ${o.evidence.arrival_on}: ${o.evidence.event ?? o.evidence.title}. ${o.applies_because}`).join(" ")}</desc>
      <rect x="76" y="36" width="420" height={Math.max(0, y(due) - 36)} fill="var(--rs-bad)" opacity=".055" />
      {[ymin, (ymin + ymax) / 2, ymax].map((d) => <g key={d}><line x1="76" x2="496" y1={y(d)} y2={y(d)} stroke="var(--rs-line-2)" /><text x="65" y={y(d) + 4} textAnchor="end">{dateLabel(new Date(d * 86400000).toISOString())}</text></g>)}
      <line x1="76" x2="496" y1={y(due)} y2={y(due)} stroke="var(--rs-bad)" strokeDasharray="5 4" />
      <text x="496" y={y(due) - 9} textAnchor="end" fill="var(--rs-bad)">Need by {dateLabel(deadline)}</text>
      {suppliers.map((supplier, index) => {
        const group = points.filter((o) => (o.evidence.supplier ?? "Supplier unknown") === supplier);
        return <g key={supplier}>
          <polyline points={group.map((o) => `${x(day(o.evidence.issued_on))},${y(day(o.evidence.arrival_on!))}`).join(" ")} fill="none" stroke={colors[index % colors.length]} strokeWidth="2" />
          {group.map((o) => <g key={o.evidence.evidence_id}><circle cx={x(day(o.evidence.issued_on))} cy={y(day(o.evidence.arrival_on!))} r="5" stroke={colors[index % colors.length]} strokeWidth="2" fill={o.level === "watchlist" ? "var(--rs-panel-solid)" : colors[index % colors.length]}><title>{o.evidence.title}: {o.evidence.event ?? o.applies_because}</title></circle>{o.evidence.event ? <text x={x(day(o.evidence.issued_on))} y={y(day(o.evidence.arrival_on!)) - 12} textAnchor={x(day(o.evidence.issued_on)) > 350 ? "end" : "start"} fill={colors[index % colors.length]}>Update</text> : null}</g>)}
        </g>;
      })}
      <text x="76" y="235">{dateLabel(new Date(xmin * 86400000).toISOString())}</text><text x="496" y="235" textAnchor="end">{dateLabel(new Date(xmax * 86400000).toISOString())}</text>
      <text x="286" y="259" textAnchor="middle">Date of source document</text>
      <text x="76" y="20">Estimated arrival</text>
    </svg>
    <div className="rs-risk-legend">{suppliers.map((s, i) => <span key={s}><i style={{ background: colors[i % colors.length] }} />{s}</span>)}<span>Hollow point: scope unverified</span></div>
    <details><summary>Timeline data and events</summary><div className="rs-risk-table-scroll"><table><thead><tr><th>Source date</th><th>Supplier</th><th>Arrival</th><th>What changed</th></tr></thead><tbody>{points.map((o) => <tr key={o.evidence.evidence_id}><td>{dateLabel(o.evidence.issued_on)}</td><td>{o.evidence.supplier ?? "Unknown"}</td><td>{dateLabel(o.evidence.arrival_on!)}</td><td>{o.evidence.event ?? o.evidence.title}</td></tr>)}</tbody></table></div></details>
  </figure>;
}
