export type AppRoute =
  | { page: "home" }
  | { page: "investigations" }
  | { page: "new"; upload?: boolean }
  | { page: "project"; id: string }
  | { page: "quotes"; id: string }
  | { page: "risk"; id: string }
  | { page: "legacy" };

export function readRoute(hash: string): AppRoute {
  if (hash.startsWith("#risk/") && hash.length > 6) return { page: "risk", id: hash.slice(6) };
  if (hash.startsWith("#quotes/") && hash.length > 8) return { page: "quotes", id: hash.slice(8) };
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
  if (route.page === "quotes") return `#quotes/${route.id}`;
  if (route.page === "risk") return `#risk/${route.id}`;
  if (route.page === "new") return route.upload ? "#new/upload" : "#new";
  if (route.page === "legacy") return "#engine";
  return `#${route.page}`;
}
