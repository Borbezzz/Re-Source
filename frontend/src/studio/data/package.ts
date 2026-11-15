import { unzipSync, strFromU8 } from "fflate";
import { buildAssemblyTree, type AssemblyItem, type AssemblyNode } from "./assembly.ts";

/** Parsed Mechanica-style design package (see blueprint input/PACKAGE-CONTRACT.md). */
export interface PackageComponent {
  componentId: string;
  role: "primary" | "secondary";
  name: string;
  partNumber: string;
  revision: string;
  parentAssemblyId: string;
  nodeIds: string[];
  assemblyQuantity: number;
  condition: string;
  requirementSet: string;
}
export interface RequirementCheck {
  id: string;
  kind: string;
  requiredEvidence?: string;
  fields?: string[];
  against?: string;
}
export interface RequirementSet {
  id: string;
  componentId: string;
  partNumber: string;
  revision: string;
  condition: string;
  mandatoryChecks: RequirementCheck[];
  notes?: string;
}
export interface DesignPackage {
  packageId: string;
  displayName: string;
  packageVersion: string;
  dataMode: string;
  source?: { repository: string; commit: string; license: string };
  geometry: { file: string; meshOccurrences: number; independentPieces: number; kind: string };
  components: PackageComponent[];
  requirements: RequirementSet[];
  glb: Uint8Array;
  glbUrl: string;
  /** GLB node stable IDs, read from the binary's JSON chunk. */
  nodeIds: Set<string>;
  assemblyTree: AssemblyItem[];
  files: { path: string; bytes: number; verified: boolean }[];
}

export type StepId = "read" | "verify" | "identify" | "map" | "link" | "scene";
export type StepEvent = { step: StepId; status: "running" | "done" | "error"; detail?: string };

async function sha256(bytes: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes as BufferSource);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function glbNodes(glb: Uint8Array): AssemblyNode[] {
  const view = new DataView(glb.buffer, glb.byteOffset, glb.byteLength);
  if (view.getUint32(0, true) !== 0x46546c67) throw new Error("assembly.glb is not a binary glTF file.");
  const jsonLength = view.getUint32(12, true);
  const json = JSON.parse(new TextDecoder().decode(glb.subarray(20, 20 + jsonLength)));
  return json.nodes ?? [];
}

function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  for (const line of text.trim().split(/\r?\n/)) {
    const cells: string[] = [];
    let cur = "";
    let quoted = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"') {
        if (quoted && line[i + 1] === '"') {
          cur += '"';
          i++;
        } else quoted = !quoted;
      } else if (c === "," && !quoted) {
        cells.push(cur);
        cur = "";
      } else cur += c;
    }
    cells.push(cur);
    rows.push(cells);
  }
  const [head, ...body] = rows;
  return body.map((r) => Object.fromEntries(head.map((h, i) => [h, r[i] ?? ""])));
}

const pause = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Read a design package from a ZIP or a set of loose files. Every step is real:
 * unzip, SHA-256 verification against the manifest, GLB node lookup for each
 * component, and requirement-set linkage. `onStep` reports actual progress.
 */
export async function readDesignPackage(
  input: File[] | Uint8Array,
  onStep: (e: StepEvent) => void,
  onIdentified?: (info: { packageId: string; displayName: string; glbUrl: string }) => void,
  minStepMs = 520,
): Promise<DesignPackage> {
  const step = async <T,>(id: StepId, fn: () => Promise<T> | T, detail?: (v: T) => string): Promise<T> => {
    onStep({ step: id, status: "running" });
    const started = performance.now();
    try {
      const value = await fn();
      const left = minStepMs - (performance.now() - started);
      if (left > 0) await pause(left); // keep each real step legible on screen
      onStep({ step: id, status: "done", detail: detail?.(value) });
      return value;
    } catch (err) {
      onStep({ step: id, status: "error", detail: err instanceof Error ? err.message : String(err) });
      throw err;
    }
  };

  const files = await step(
    "read",
    async () => {
      const out: Record<string, Uint8Array> = {};
      const add = (name: string, data: Uint8Array) => {
        const base = name.split("/").pop()!;
        if (!base || base.startsWith(".") || name.startsWith("__MACOSX")) return;
        out[base] = data;
      };
      if (input instanceof Uint8Array) {
        for (const [name, data] of Object.entries(unzipSync(input))) add(name, data);
      } else {
        for (const file of input) {
          const data = new Uint8Array(await file.arrayBuffer());
          if (file.name.toLowerCase().endsWith(".zip")) {
            for (const [name, inner] of Object.entries(unzipSync(data))) add(name, inner);
          } else add(file.name, data);
        }
      }
      if (!out["manifest.json"]) throw new Error("No manifest.json found. Add the package manifest so parts can be mapped.");
      return out;
    },
    (f) => `${Object.keys(f).length} files read`,
  );

  const manifest = JSON.parse(strFromU8(files["manifest.json"]));
  const verified = await step(
    "verify",
    async () => {
      const results: DesignPackage["files"] = [];
      for (const entry of manifest.files ?? []) {
        const data = files[entry.path];
        if (!data) throw new Error(`${entry.path} is listed in the manifest but missing from the package.`);
        const hash = await sha256(data);
        if (hash !== entry.sha256) throw new Error(`${entry.path} does not match its manifest checksum.`);
        results.push({ path: entry.path, bytes: data.byteLength, verified: true });
      }
      return results;
    },
    (r) => `${r.length} checksums match the manifest`,
  );

  const glbName = manifest.geometry?.file ?? "assembly.glb";
  const identity = await step(
    "identify",
    () => {
      if (!files[glbName]) throw new Error(`The assembly model ${glbName} is missing.`);
      const nodes = glbNodes(files[glbName]);
      return {
        packageId: String(manifest.packageId),
        displayName: String(manifest.displayName ?? manifest.packageId),
        nodes,
        nodeIds: new Set(nodes.flatMap(n => n.extras?.stableId ? [n.extras.stableId] : [])),
      };
    },
    (v) => `${v.displayName} · ${manifest.geometry?.independentPieces ?? v.nodeIds.size} pieces`,
  );

  const glbUrl = URL.createObjectURL(new Blob([files[glbName] as BlobPart], { type: "model/gltf-binary" }));
  onIdentified?.({ packageId: identity.packageId, displayName: identity.displayName, glbUrl });

  const components = await step(
    "map",
    () => {
      const csv = files["components.csv"] ? parseCsv(strFromU8(files["components.csv"])) : [];
      const list: PackageComponent[] = (manifest.components ?? []).map((c: PackageComponent) => ({ ...c }));
      for (const row of csv) {
        const match = list.find((c) => c.componentId === row.component_id);
        if (match && (match.partNumber !== row.part_number || match.revision !== row.revision))
          throw new Error(`${row.component_id}: parts list and manifest disagree on part number or revision.`);
      }
      for (const c of list) {
        const missing = c.nodeIds.filter((id) => !identity.nodeIds.has(id));
        if (missing.length) throw new Error(`${c.name} maps to geometry that is not in the model (${missing[0]}).`);
      }
      if (!list.length) throw new Error("The manifest lists no components.");
      return list;
    },
    (l) => `${l.length} components mapped to model geometry`,
  );

  const requirements = await step(
    "link",
    () => {
      if (!files["requirements.json"]) throw new Error("requirements.json is missing.");
      const sets: RequirementSet[] = JSON.parse(strFromU8(files["requirements.json"])).sets ?? [];
      for (const c of components) {
        const set = sets.find((s) => s.id === c.requirementSet);
        if (!set) throw new Error(`${c.name} has no requirement set ${c.requirementSet}.`);
        if (set.partNumber !== c.partNumber || set.revision !== c.revision)
          throw new Error(`${c.name}: requirement set identity differs from the parts list.`);
      }
      return sets;
    },
    (s) => `${s.reduce((n, x) => n + x.mandatoryChecks.length, 0)} mandatory checks linked`,
  );

  const glb = files[glbName];
  return {
    packageId: identity.packageId,
    displayName: identity.displayName,
    packageVersion: String(manifest.packageVersion ?? ""),
    dataMode: String(manifest.dataMode ?? "unknown"),
    source: manifest.source,
    geometry: manifest.geometry,
    components,
    requirements,
    glb,
    glbUrl,
    nodeIds: identity.nodeIds,
    assemblyTree: buildAssemblyTree(identity.nodes, components),
    files: verified,
  };
}

export const SAMPLE_PACKAGE_URL = "/packages/mechanica-input-package.zip";
/** Prepared backend profile for a verified package identity (not the filename). */
export const PROFILE_FOR_PACKAGE: Record<string, string> = { "rs-mechanica-turbofan-v1": "turbofan" };
