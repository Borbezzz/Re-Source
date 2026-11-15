import type { PackageComponent } from "./package.ts";

/** Visual inventory from the uploaded GLB. Sourcing identities come only from its manifest. */
export interface AssemblyItem {
  id: string;
  name: string;
  nodeIds: string[];
  assemblyId: string;
  pieceCount: number;
  componentId: string | null;
  children: AssemblyItem[];
}

export interface AssemblyNode {
  mesh?: number;
  children?: number[];
  extras?: {
    stableId?: string;
    assemblyId?: string;
    parentAssemblyId?: string;
    displayName?: string;
    sourceMeshIndex?: number;
    attachedToStableId?: string;
  };
}

const PLURALS: Record<string, string> = {
  "Rotor blade": "Rotor blades", "Stator vane": "Stator vanes", "Fuel injector": "Fuel injectors",
  "Housing": "Housings", "Retaining ring": "Retaining rings", "Fastener": "Fasteners",
  "Tube": "Tubes", "Shaft / sleeve": "Shafts and sleeves", "Spinner / cone": "Spinner / cone",
};

export function buildAssemblyTree(nodes: AssemblyNode[], components: PackageComponent[]): AssemblyItem[] {
  const mapped = new Map(components.flatMap(c => c.nodeIds.map(id => [id, c] as const)));
  const attachments = new Map<string, string[]>();
  for (const n of nodes) {
    const e = n.extras;
    if (e?.attachedToStableId && e.stableId) {
      const list = attachments.get(e.attachedToStableId) ?? [];
      list.push(e.stableId);
      attachments.set(e.attachedToStableId, list);
    }
  }
  const roots: AssemblyItem[] = [];
  for (const group of nodes.filter(n => n.extras?.assemblyId && n.extras.stableId)) {
    const e = group.extras!;
    const assemblyId = e.assemblyId!;
    const families = new Map<string, AssemblyNode[]>();
    for (const n of nodes) {
      const p = n.extras;
      if (n.mesh == null || p?.parentAssemblyId !== assemblyId || !p.stableId || p.attachedToStableId) continue;
      const label = p.displayName ?? "Piece";
      const list = families.get(label) ?? [];
      list.push(n);
      families.set(label, list);
    }
    const children: AssemblyItem[] = [];
    for (const [label, pieces] of families) {
      const singular = assemblyId === "fan" && label === "Rotor blade" ? "Fan blade" : label;
      const leaves = pieces.map((n, i): AssemblyItem => {
        const id = n.extras!.stableId!;
        const component = mapped.get(id);
        return { id, name: component?.nodeIds.length === 1 ? component.name : `${singular} ${String(i + 1).padStart(2, "0")}`,
          nodeIds: [id, ...(attachments.get(id) ?? [])], assemblyId, pieceCount: 1,
          componentId: component?.componentId ?? null, children: [] };
      });
      if (leaves.length === 1) { children.push(leaves[0]); continue; }
      const familyName = assemblyId === "fan" && label === "Rotor blade" ? "Fan blades" : (PLURALS[label] ?? label);
      // Blade/vane rows retain their exported stage boundaries instead of becoming a 400-row menu.
      const stages = new Map<number, AssemblyItem[]>();
      if ((assemblyId === "compressor" || assemblyId === "turbine") && /blade|vane/i.test(label)) {
        pieces.forEach((n, i) => {
          const key = n.extras!.sourceMeshIndex ?? 0;
          stages.set(key, [...(stages.get(key) ?? []), leaves[i]]);
        });
      }
      const familyId = `${e.stableId}:${label}`;
      const familyChildren = stages.size > 1 ? [...stages.values()].map((items, i): AssemblyItem => ({
        id: `${familyId}:stage-${i + 1}`, name: `Stage ${i + 1}`, assemblyId, pieceCount: items.length,
        nodeIds: items.flatMap(p => p.nodeIds), children: items, componentId: commonComponent(items),
      })) : leaves;
      children.push({ id: familyId, name: familyName, assemblyId, pieceCount: leaves.length,
        nodeIds: leaves.flatMap(p => p.nodeIds), children: familyChildren, componentId: commonComponent(leaves) });
    }
    if (!children.length) continue;
    const component = mapped.get(e.stableId!);
    roots.push({ id: e.stableId!, name: e.displayName ?? assemblyId, assemblyId,
      nodeIds: [e.stableId!], pieceCount: children.reduce((n, c) => n + c.pieceCount, 0),
      componentId: component?.componentId ?? null, children });
  }
  // Packages without the Mechanica assembly metadata still expose their explicit manifest mappings.
  if (!roots.length) return components.map(c => ({ id: c.componentId, name: c.name, nodeIds: c.nodeIds,
    assemblyId: c.parentAssemblyId, pieceCount: 1, componentId: c.componentId, children: [] }));
  return roots;
}

function commonComponent(items: AssemblyItem[]): string | null {
  const id = items[0]?.componentId;
  return id && items.every(item => item.componentId === id) ? id : null;
}

export function indexAssembly(items: AssemblyItem[]): Map<string, AssemblyItem> {
  const result = new Map<string, AssemblyItem>();
  const visit = (item: AssemblyItem) => { result.set(item.id, item); item.children.forEach(visit); };
  items.forEach(visit);
  return result;
}
