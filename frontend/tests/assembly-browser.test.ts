import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { buildAssemblyTree, indexAssembly } from "../src/studio/data/assembly.ts";

const root = new URL("../../", import.meta.url);
const read = (path: string) => readFileSync(new URL(path, root));
const manifest = JSON.parse(read("blueprint%20input/input-package/manifest.json").toString());
const bytes = read("blueprint%20input/input-package/assembly.glb");
const nodes = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString()).nodes;
const tree = buildAssemblyTree(nodes, manifest.components);
const index = indexAssembly(tree);

test("uploaded geometry exposes seven sections and 1,835 independent pieces without decorative duplicates", () => {
  assert.equal(tree.length, 7);
  const leaves = [...index.values()].filter(item => !item.children.length);
  assert.equal(leaves.length, 1835);
  assert.equal(new Set(leaves.map(item => item.id)).size, 1835);
  assert.equal(tree.reduce((sum, item) => sum + item.pieceCount, 0), 1835);
});

test("fan group and individual blades target exact, distinct model occurrences", () => {
  const fan = [...index.values()].find(item => item.name === "Fan blades")!;
  assert.equal(fan.children.length, 24);
  assert.equal(fan.nodeIds.length, 24);
  assert.equal(fan.componentId, "RS-TF-FAN-BLADE");
  for (const [i, blade] of fan.children.entries()) {
    assert.equal(blade.name, `Fan blade ${String(i + 1).padStart(2, "0")}`);
    assert.equal(blade.nodeIds.length, 1);
    assert.equal(blade.componentId, "RS-TF-FAN-BLADE");
    assert.equal(blade.nodeIds[0], `rs-mech-tf-v1.fan.m000.i${String(i).padStart(3, "0")}`);
  }
});

test("stage sourcing identities come from the manifest and all 35 cases reach the backend with map sites", () => {
  const cp = tree.find(item => item.assemblyId === "compressor")!;
  const stages = cp.children.find(item => item.name === "Rotor blades")!.children;
  assert.equal(stages.length, 9);
  assert.equal(new Set(stages.map(item => item.componentId)).size, 9);
  assert.ok(stages.every(item => item.componentId && item.children.every(leaf => leaf.componentId === item.componentId)));
  const turbine = tree.find(item => item.assemblyId === "turbine")!;
  assert.equal(turbine.children.find(item => item.name === "Rotor blades")!.children.length, 5);
  const profile = JSON.parse(read("data/demo-products/turbofan.json").toString());
  const sites = JSON.parse(read("frontend/src/studio/data/extra-sites.json").toString());
  assert.equal(profile.parts.length, 35);
  for (const component of manifest.components) {
    const part = profile.parts.find((part: { part_id: string }) => part.part_id === component.componentId.toLowerCase());
    assert.equal(part.part_number, component.partNumber);
    assert.deepEqual(part.node_names, component.nodeIds);
    assert.ok([...index.values()].some(item => item.componentId === component.componentId));
    const extra = profile.sample_offers.filter((offer: { part_id: string; candidate_id: string }) => offer.part_id === part.part_id && /-site-1[345]$/.test(offer.candidate_id));
    assert.equal(extra.length, 3);
    assert.ok(extra.every((offer: { candidate_id: string }) => sites[offer.candidate_id]));
  }
});

test("unmapped fasteners remain inspectable without inheriting an invented sourcing identity", () => {
  const fasteners = tree.find(item => item.assemblyId === "casing")!.children.find(item => item.name === "Fasteners")!;
  assert.equal(fasteners.componentId, null);
  assert.ok(fasteners.children.every(item => item.componentId === null));
});
