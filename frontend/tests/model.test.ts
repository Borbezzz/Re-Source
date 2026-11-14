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

test("prepared asset keeps each published part mapped to nonempty mesh geometry and animation", () => {
  const mapping = JSON.parse(
    readFileSync(
      new URL("../src/product/toy-car.json", import.meta.url),
      "utf8",
    ),
  );
  const bytes = readFileSync(
    new URL("../public/models/toy-car.glb", import.meta.url),
  );
  assert.equal(bytes.toString("utf8", 0, 4), "glTF");
  const gltf = JSON.parse(
    bytes.toString("utf8", 20, 20 + bytes.readUInt32LE(12)),
  );
  assert.equal(
    new Set(mapping.components.map((p: any) => p.component_id)).size,
    8,
  );
  for (const part of mapping.components) {
    const nodes = gltf.nodes.filter((n: any) => n.name === part.node_name);
    assert.equal(nodes.length, 1, part.node_name);
    assert.equal(nodes[0].extras.component_id, part.component_id);
    const mesh = gltf.meshes[nodes[0].mesh];
    assert.ok(
      mesh.primitives.every(
        (p: any) => gltf.accessors[p.attributes.POSITION].count >= 3,
      ),
    );
    assert.equal(part.requirements_status, "source_required");
  }
  assert.ok(gltf.animations.length > 0);
});
