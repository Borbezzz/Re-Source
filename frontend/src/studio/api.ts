import { productApi } from "../product-flow/client.ts";
import type { ProductEnquiry, ProductProject } from "../product-flow/types.ts";
import type { NeedsDraft } from "./supply-risk/types.ts";

/** Thin journey wrapper over the real /api/v1/products contract. */
export const journeyApi = {
  async create(demoId: string): Promise<ProductProject> {
    return productApi.create({ demo_id: demoId });
  },
  async confirmParts(p: ProductProject, draft: NeedsDraft): Promise<ProductProject> {
    if (p.parts.every((part) => {
      const reviewed = draft.parts.find((r) => r.part_id === part.part_id);
      return part.status === "confirmed" && reviewed && (part.part_number ?? "") === reviewed.part_number.trim() && part.quantity === reviewed.quantity && (part.requirements.find((r) => r.key === "revision")?.value ?? "") === reviewed.revision.trim();
    })) return p;
    const parts = p.parts.map((part) => {
      const reviewed = draft.parts.find((r) => r.part_id === part.part_id)!;
      const requirements = part.requirements.filter((r) => !["revision", "part_number"].includes(r.key)).map((r) => ({ ...r, status: "confirmed" as const }));
      for (const [key, label, value] of [["part_number", "Part number", reviewed.part_number], ["revision", "Revision", reviewed.revision]]) {
        if (!value.trim()) continue;
        const previous = part.requirements.find((r) => r.key === key);
        requirements.push({ key, label, value: value.trim(), status: "confirmed", unit: null, source: previous?.value === value.trim() ? previous.source : null });
      }
      return { ...part, part_number: reviewed.part_number.trim() || null, quantity: reviewed.quantity,
        part_number_source: part.part_number === reviewed.part_number.trim() ? part.part_number_source : null,
        quantity_source: part.quantity === reviewed.quantity ? part.quantity_source : null,
        status: "confirmed" as const, requirements };
    });
    return productApi.parts(p.project_id, parts, true, p.version);
  },
  project: (id: string) => productApi.project(id),
  async research(projectId: string, partId: string, signal?: AbortSignal): Promise<ProductProject> {
    let p = await productApi.investigate(projectId, [partId], "demo");
    for (let i = 0; i < 80; i++) {
      const r = p.research.find((x) => x.part_id === partId);
      if (r && (r.status === "complete" || r.status === "failed")) return p;
      await new Promise((res) => setTimeout(res, 400));
      if (signal?.aborted) throw new DOMException("aborted", "AbortError");
      p = await productApi.project(projectId, signal);
    }
    throw new Error("Supplier research is taking longer than expected. Please retry.");
  },
  select: (projectId: string, partId: string, candidateId: string) => productApi.select(projectId, partId, candidateId),
  package: (projectId: string, enquiry: ProductEnquiry) => productApi.package(projectId, enquiry),
  approve: (projectId: string, packageId: string) => productApi.approve(projectId, packageId),
  simulate: (projectId: string, packageId: string) => productApi.simulate(projectId, packageId),
};
