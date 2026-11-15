export type AppRoute =
  | { page: "home" }
  | { page: "investigations" }
  | { page: "new"; upload?: boolean }
  | { page: "project"; id: string }
  | { page: "legacy" };

export function readRoute(hash: string): AppRoute {
  if (hash.startsWith("#project/")) {
    const id = hash.slice(9);
    if (id) return { page: "project", id };
  }
  if (hash === "#investigations") return { page: "investigations" };
  if (hash === "#new" || hash === "#products") return { page: "new" };
  if (hash === "#new/upload" || hash === "#upload")
    return { page: "new", upload: true };
  if (
    hash === "#sources" ||
    hash === "#engine" ||
    hash.startsWith("#demo/") ||
    hash.startsWith("#batch/")
  )
    return { page: "legacy" };
  return { page: "home" };
}

export function routeHash(route: AppRoute): string {
  if (route.page === "project") return `#project/${route.id}`;
  if (route.page === "new") return route.upload ? "#new/upload" : "#new";
  if (route.page === "legacy") return "#engine";
  return `#${route.page}`;
}
