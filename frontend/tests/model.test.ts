import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  createDemoEngine,
  validateMeshMappings,
  disposeModel,
} from "../src/scene/model.ts";
const manifest = JSON.parse(
  readFileSync(
    new URL("../../data/manifests/engine-demo-001.json", import.meta.url),
    "utf8",
  ),
);
test("every manifest component has one nonempty mesh and all seven module names survive", () => {
  const model = createDemoEngine(
    manifest.components,
    manifest.engine.asset.modules,
  );
  assert.deepEqual(validateMeshMappings(model, manifest.components), []);
  for (const module of manifest.engine.asset.modules)
    assert.ok(model.getObjectByName(module.node_name));
  const node = model.getObjectByName(
    manifest.components[0].mesh_mapping.node_name,
  )!;
  model.add(node.clone());
  assert.match(validateMeshMappings(model, manifest.components)[0], /found 2/);
  disposeModel(model);
});
