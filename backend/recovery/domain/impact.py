"""Evidence graph traversal (PRD FR-10/FR-11). Resolves a change to affected offers and cases through
explicit relationship rows and returns human-readable impact paths."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

# (node type, relation, direction) -> next node type. "in" = follow edges pointing INTO the node.
TRAVERSAL = {
    "geo": [("passes_through", "in"), ("located_in", "in")],
    "route": [("ships_via", "in")],
    "site": [("supplied_from", "in")],
    "supplier": [("sold_by", "in")],
    "part": [("offers_part", "in")],
    "evidence": [("supports", "out"), ("applies_to", "out")],
    "offer": [("candidate_for", "out")],
}


class Graph:
    def __init__(self, relationships: Iterable[dict]):
        self.out: dict[str, list[dict]] = defaultdict(list)
        self.inc: dict[str, list[dict]] = defaultdict(list)
        self.types: dict[str, str] = {}
        for r in relationships:
            self.out[r["from_id"]].append(r)
            self.inc[r["to_id"]].append(r)
            self.types[r["from_id"]] = r["from_type"]
            self.types[r["to_id"]] = r["to_type"]

    def type_of(self, node: str, default: str = "unknown") -> str:
        return self.types.get(node, default)

    def impact(self, start_ids: Iterable[str], start_type_hint: dict[str, str] | None = None) -> dict:
        """BFS from changed entities to cases. Returns affected offers/cases and one path per (start, case)."""
        hint = start_type_hint or {}
        paths: list[list[dict]] = []
        affected_offers: set[str] = set()
        affected_cases: set[str] = set()
        touched: set[str] = set()
        for start in start_ids:
            stype = hint.get(start) or self.type_of(start)
            queue = deque([(start, stype, [{"id": start, "type": stype}])])
            seen = {start}
            while queue:
                node, ntype, path = queue.popleft()
                touched.add(node)
                if ntype == "case":
                    affected_cases.add(node)
                    paths.append(path)
                    continue
                if ntype == "offer":
                    affected_offers.add(node)
                for rel, direction in TRAVERSAL.get(ntype, []):
                    edges = self.inc[node] if direction == "in" else self.out[node]
                    for e in edges:
                        if e["relation_type"] != rel:
                            continue
                        nxt, nxt_type = (e["from_id"], e["from_type"]) if direction == "in" else (e["to_id"], e["to_type"])
                        if nxt in seen:
                            continue
                        seen.add(nxt)
                        queue.append((nxt, nxt_type, path + [{"id": nxt, "type": nxt_type, "via": rel}]))
        return {"offers": sorted(affected_offers), "cases": sorted(affected_cases), "paths": paths, "touched": sorted(touched)}


def scope_entities(signal: dict, sites: dict[str, dict]) -> tuple[list[str], dict[str, str]]:
    scope = signal.get("scope", {})
    ids: list[str] = []
    hint: dict[str, str] = {}
    for g in scope.get("geo_ids", []):
        ids.append(g)
        hint[g] = "geo"
    for r in scope.get("route_ids", []):
        ids.append(r)
        hint[r] = "route"
    for s in scope.get("site_ids", []):
        ids.append(s)
        hint[s] = "site"
    for e in scope.get("entity_ids", []):
        ids.append(e)
        hint[e] = "supplier"
    for c in scope.get("origin_countries", []):
        gid = f"GEO-COUNTRY-{c}"
        ids.append(gid)
        hint[gid] = "geo"
    return ids, hint
