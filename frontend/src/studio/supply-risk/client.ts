import type { RiskEvidence, RiskNeed, RiskScan } from "./types.ts";

async function request(projectId: string, path = "", body?: unknown, signal?: AbortSignal): Promise<RiskScan> {
  const response = await fetch(`/api/v1/products/${encodeURIComponent(projectId)}/supply-risk${path}`, {
    credentials: "same-origin", signal,
    ...(body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify(body) }),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.message ?? data?.detail?.message ?? (typeof data?.detail === "string" ? data.detail : "Supply-risk update failed. Try again."));
  return data;
}
export const riskApi = {
  get: (id: string, signal?: AbortSignal) => request(id, "", undefined, signal),
  confirm: (id: string, expected_project_version: number, needs: RiskNeed[]) => request(id, "/confirm", { expected_project_version, needs }),
  refresh: (id: string) => request(id, "/refresh", {}),
  evidence: (id: string, expected_scan_version: number, evidence: RiskEvidence) => request(id, "/evidence", { expected_scan_version, evidence }),
};
