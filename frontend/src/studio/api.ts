import { productApi } from "../product-flow/client.ts";
import type { ProductProject } from "../product-flow/types.ts";

/** Thin journey wrapper over the real /api/v1/products contract. */
export const journeyApi = {
  async create(demoId: string): Promise<ProductProject> {
    return productApi.create({ demo_id: demoId });
  },
  async confirmParts(p: ProductProject): Promise<ProductProject> {
    const parts = p.parts.map((part) => ({
      ...part,
      status: "confirmed" as const,
      requirements: part.requirements.map((r) => ({ ...r, status: "confirmed" as const })),
    }));
    return productApi.parts(p.project_id, parts, true, p.version);
  },
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
  package: (projectId: string) => productApi.package(projectId),
  approve: (projectId: string, packageId: string) => productApi.approve(projectId, packageId),
  simulate: (projectId: string, packageId: string) => productApi.simulate(projectId, packageId),
};
