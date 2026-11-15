import { useMemo } from "react";
import { geoContains, geoMercator } from "d3-geo";
import { feature } from "topojson-client";
import land from "world-atlas/land-50m.json";
import type { Topology, GeometryCollection } from "topojson-specification";
import { MapPin } from "lucide-react";
import type { RankedCandidate } from "../api/types.ts";
const earth = feature(land as unknown as Topology, {
  ...(land.objects.land as GeometryCollection),
});
const supplierName = (r: RankedCandidate) =>
  r.supplier?.legal_entity_name ?? r.candidate.supplier_id;
export default function SupplyMap({
  candidates,
  selected,
  onSelect,
}: {
  candidates: RankedCandidate[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const projection = useMemo(
    () => geoMercator().center([0, 53.3]).scale(1250).translate([390, 175]),
    [],
  );
  const dots = useMemo(() => {
    const points: { x: number; y: number }[] = [];
    for (let y = 4; y < 340; y += 7)
      for (let x = 4; x < 800; x += 7) {
        const p = projection.invert?.([x, y]);
        if (p && geoContains(earth, p)) points.push({ x, y });
      }
    return points;
  }, [projection]);
  const sites = candidates.flatMap((c) => {
    const g = c.site?.geography;
    const lat = g?.lat,
      lon = g?.lon;
    if (
      typeof lat !== "number" ||
      typeof lon !== "number" ||
      !Number.isFinite(lat) ||
      !Number.isFinite(lon)
    )
      return [];
    const p = projection([lon, lat]);
    return p ? [{ c, x: p[0], y: p[1] }] : [];
  });
  return (
    <div className="supply-map">
      <div className="map-heading">
        <h3>Supply network</h3>
        <span>{sites.length} located sites</span>
      </div>
      <svg
        viewBox="0 0 800 340"
        role="img"
        aria-label="Supplier locations in northern Europe. Choose a site from the list below."
      >
        <g fill="#b9cabe">
          {dots.map(({ x, y }) => (
            <rect key={`${x}-${y}`} x={x} y={y} width={3} height={3} rx={0.5} />
          ))}
        </g>
        {sites.map(({ c, x, y }) => (
          <g
            key={c.candidate.candidate_id}
            transform={`translate(${x},${y})`}
            onClick={() => onSelect(c.candidate.candidate_id)}
            className="map-marker"
          >
            <circle
              r={selected === c.candidate.candidate_id ? 17 : 12}
              fill={c.eligibility === "eligible" ? "#194f45" : "#8a4d17"}
              stroke="#fff"
              strokeWidth={3}
            />
            <text textAnchor="middle" dy=".35em" fill="white" fontSize={11}>
              {c.rank ?? "?"}
            </text>
            <title>
              {supplierName(c)} · {c.site?.name}
            </title>
          </g>
        ))}
      </svg>
      <div className="map-sites">
        {sites.map(({ c }) => (
          <button
            key={c.candidate.candidate_id}
            className={selected === c.candidate.candidate_id ? "chosen" : ""}
            onClick={() => onSelect(c.candidate.candidate_id)}
          >
            <MapPin size={13} />
            {c.site?.name}
          </button>
        ))}
      </div>
      <p className="map-caption">
        Natural Earth basemap · Locations from supplier records.{" "}
        {candidates.length - sites.length > 0
          ? `${candidates.length - sites.length} option(s) have no mapped location.`
          : ""}
      </p>
    </div>
  );
}
