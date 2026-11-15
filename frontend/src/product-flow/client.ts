import type {
  DemoProduct,
  ProductPart,
  ProductProject,
  ProductProjectSummary,
} from "./types.ts";
export function createProductApi(
  base = "/api/v1/products",
  transport: typeof fetch = fetch,
) {
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await transport(`${base}${path}`, {
      credentials: "same-origin",
      ...init,
    });
    const data = await response.json().catch(() => null);
    if (!response.ok)
      throw new Error(
        data?.message ??
          data?.detail?.message ??
          (typeof data?.detail === "string"
            ? data.detail
            : `The request failed (${response.status}). Please try again.`),
      );
    return data as T;
  }
  const json = <T>(path: string, body: unknown = {}, method = "POST") =>
    request<T>(path, {
      method,
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify(body),
    });
  const path = (id: string) => `/${encodeURIComponent(id)}`;
  return {
    projects: (signal?: AbortSignal) =>
      request<{ projects: ProductProjectSummary[] }>("", { signal }),
    demos: (signal?: AbortSignal) =>
      request<DemoProduct[]>("/demos", { signal }),
    create: (body: { demo_id?: string; name?: string }) =>
      json<ProductProject>("", body),
    project: (id: string, signal?: AbortSignal) =>
      request<ProductProject>(path(id), { signal }),
    upload: (id: string, file: File, kind: string) => {
      const form = new FormData();
      form.set("file", file);
      form.set("kind", kind);
      return request<ProductProject>(`${path(id)}/documents`, {
        method: "POST",
        body: form,
        headers: { "Idempotency-Key": crypto.randomUUID() },
      });
    },
    extract: (id: string) => json<ProductProject>(`${path(id)}/extract`),
    parts: (
      id: string,
      parts: ProductPart[],
      confirm: boolean,
      version: number,
    ) =>
      json<ProductProject>(
        `${path(id)}/parts`,
        { parts, confirm, expected_version: version },
        "PATCH",
      ),
    model: (id: string, origin: string, document_id?: string) =>
      json<ProductProject>(`${path(id)}/model`, { origin, document_id }),
    investigate: (id: string, part_ids: string[], mode?: "demo" | "live") =>
      json<ProductProject>(`${path(id)}/investigations`, { part_ids, mode }),
    select: (id: string, part_id: string, candidate_id: string) =>
      json<ProductProject>(
        `${path(id)}/selections`,
        { part_id, candidate_id },
        "PATCH",
      ),
    package: (id: string) => json<ProductProject>(`${path(id)}/package`),
    approve: (id: string, package_id: string) =>
      json<ProductProject>(`${path(id)}/package/approve`, {
        acknowledge_unverified: true,
        expected_package_id: package_id,
      }),
    simulate: (id: string, package_id: string) =>
      json<ProductProject>(`${path(id)}/package/simulate`, {
        expected_package_id: package_id,
      }),
  };
}
export const productApi = createProductApi();
