import { geoCentroid } from "d3-geo";
import { feature } from "topojson-client";
import countries from "world-atlas/countries-110m.json" with { type: "json" };
import type { Topology, GeometryCollection } from "topojson-specification";
import { sourceUrl } from "../api/guards.ts";
import type { Finding } from "../investigation/findings.ts";
import type { ProductProject } from "./types.ts";
const geography = feature(
  countries as unknown as Topology,
  countries.objects.countries as GeometryCollection,
);
const aliases: Record<string, string> = {
  uk: "united kingdom",
  "great britain": "united kingdom",
  usa: "united states of america",
  us: "united states of america",
  "united states": "united states of america",
  "czech republic": "czechia",
};
const normalized = (name: string) =>
  aliases[name.toLowerCase().trim()] ?? name.toLowerCase().trim();
const centroids = new Map(
  geography.features.map((country) => [
    normalized(
      String((country.properties as { name?: string } | null)?.name ?? ""),
    ),
    geoCentroid(country),
  ]),
);
/** Country-centroid presentation only: never infer an unknown supplier's location. */
export function candidateFindings(project: ProductProject): Finding[] {
  return project.research.flatMap((job) =>
    job.candidates.flatMap((c) => {
      if (
        !c.country ||
        (c.data_origin === "public_web" && !sourceUrl(c.source_url))
      )
        return [];
      const point = centroids.get(normalized(c.country));
      if (!point || !point.every(Number.isFinite)) return [];
      return [
        {
          event_id: c.candidate_id,
          component_id: job.part_id,
          candidate_id: c.candidate_id,
          supplier_id: c.candidate_id,
          supplier_name: c.supplier_name,
          route: c.route.toUpperCase(),
          evidence_refs: c.source_url ? [c.source_url] : [],
          occurred_at: job.completed_at ?? job.started_at ?? project.updated_at,
          case_id: project.project_id,
          location: {
            site_id: `country:${normalized(c.country)}`,
            label: c.country,
            country: c.country,
            latitude: point[1],
            longitude: point[0],
            source: c.source_url ?? `demo:${project.demo_id}`,
            precision: "representative",
            data_origin: c.data_origin,
          },
        } as unknown as Finding,
      ];
    }),
  );
}
