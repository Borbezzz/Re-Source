import { test } from "node:test";
import assert from "node:assert/strict";
import * as THREE from "three";
import { AssemblyInstances, sourceMesh } from "../src/studio/scene/instances.ts";
import { ScanLines } from "../src/studio/scene/scan-lines.ts";

function fixture() {
  const root = new THREE.Group();
  root.position.set(-4, 1, 2);
  const geometry = new THREE.BoxGeometry();
  const material = new THREE.MeshStandardMaterial();
  const sources = Array.from({ length: 40 }, (_, i) => {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(i * 2, 0, 0);
    mesh.userData.stableId = `blade-${i}`;
    root.add(mesh);
    return mesh;
  });
  root.updateMatrixWorld(true);
  const renderer = new AssemblyInstances(sources);
  renderer.sync();
  return { root, sources, renderer };
}

test("repeated parts share one draw while keeping all geometry, transforms and stable identities", () => {
  const { sources, renderer } = fixture();
  assert.equal(renderer.root.children.length, 1);
  const batch = renderer.root.children[0] as THREE.InstancedMesh;
  assert.equal(batch.count, 40);
  assert.equal(batch.geometry, sources[0].geometry);
  for (let i = 0; i < sources.length; i++) {
    const matrix = new THREE.Matrix4();
    batch.getMatrixAt(i, matrix);
    assert.deepEqual(matrix.elements, sources[i].matrixWorld.elements);
    assert.equal(sourceMesh(batch, i), sources[i]);
  }
});

test("selection, hover and isolation preserve materials and restore all parts without stale instances", () => {
  const { sources, renderer } = fixture();
  const base = sources[0].material;
  const highlight = new THREE.MeshStandardMaterial({ color: "orange" });
  const hover = new THREE.MeshStandardMaterial({ transparent: true, opacity: 0.86 });
  sources[7].material = highlight;
  sources[8].material = hover;
  sources[8].renderOrder = 10;
  sources[9].visible = false;
  renderer.sync();
  const visible = renderer.root.children.filter(o => o.visible) as THREE.Mesh[];
  assert.equal(visible.length, 3);
  assert.equal((visible.find(m => m.material === base) as THREE.InstancedMesh).count, 37);
  assert.equal(sourceMesh(visible.find(m => m.material === highlight)!, 0), sources[7]);
  const preview = visible.find(m => m.material === hover)!;
  assert.equal(sourceMesh(preview), sources[8]);
  assert.equal(preview.renderOrder, 10);
  for (const source of sources) { source.material = base; source.visible = true; source.renderOrder = 0; }
  renderer.sync();
  const restored = renderer.root.children.filter(o => o.visible) as THREE.InstancedMesh[];
  assert.equal(restored.length, 1);
  assert.equal(restored[0].count, 40);
});

test("raycasting resolves an individual part after an assembly moves", () => {
  const { root, sources, renderer } = fixture();
  root.position.x += 100;
  sources[7].position.y = 5;
  root.updateMatrixWorld(true);
  renderer.sync();
  renderer.root.updateMatrixWorld(true);
  const position = sources[7].getWorldPosition(new THREE.Vector3());
  const ray = new THREE.Raycaster(position.clone().add(new THREE.Vector3(0, 0, 10)), new THREE.Vector3(0, 0, -1));
  const hit = ray.intersectObject(renderer.root, true)[0];
  assert.ok(hit);
  assert.equal(sourceMesh(hit.object, hit.instanceId), sources[7]);
});

test("a retired transparent preview cannot intercept picking after its part moves", () => {
  const { root, sources, renderer } = fixture();
  const base = sources[7].material;
  sources[7].material = new THREE.MeshStandardMaterial({ transparent: true });
  renderer.sync();
  renderer.root.updateMatrixWorld(true);
  const oldPosition = sources[7].getWorldPosition(new THREE.Vector3());
  sources[7].material = base;
  sources[7].position.y += 5;
  root.updateMatrixWorld(true);
  renderer.sync();
  renderer.root.updateMatrixWorld(true);
  const ray = new THREE.Raycaster(oldPosition.add(new THREE.Vector3(0, 0, 10)), new THREE.Vector3(0, 0, -1));
  assert.equal(ray.intersectObject(renderer.root, true).length, 0);
});

for (const fallback of [false, true]) {
  test(`cut-through picking follows world-space planes and restores the housing (${fallback ? "transparent copy" : "instances"})`, () => {
    const geometry = new THREE.PlaneGeometry(8, 8);
    const shellMaterial = new THREE.MeshStandardMaterial({ transparent: fallback });
    const shell = new THREE.Mesh(geometry, shellMaterial);
    const inside = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial());
    const root = new THREE.Group();
    root.position.set(2, 1, 3);
    shell.position.z = 2;
    root.add(shell, inside);
    root.updateMatrixWorld(true);
    const renderer = new AssemblyInstances([shell, inside]);
    renderer.sync();
    renderer.root.updateMatrixWorld(true);
    const pick = (x: number) => {
      const ray = new THREE.Raycaster(new THREE.Vector3(x, 1, 10), new THREE.Vector3(0, 0, -1));
      const hit = ray.intersectObject(renderer.root, true)[0];
      return hit && sourceMesh(hit.object, hit.instanceId);
    };
    assert.equal(pick(2), shell);
    shellMaterial.clippingPlanes = [
      new THREE.Plane(new THREE.Vector3(0, 0, -1), 4),
      new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0),
    ];
    shellMaterial.clipIntersection = true;
    assert.equal(pick(2), inside, "the removed housing cannot intercept an internal part");
    assert.equal(pick(-1), shell, "the retained intake lip remains selectable");
    shellMaterial.clipIntersection = false;
    assert.equal(pick(-1), inside, "union clipping discards a hit behind either plane");
    shellMaterial.clippingPlanes = null;
    assert.equal(pick(2), shell, "turning cut-through off restores full housing picking");
    renderer.dispose();
    geometry.dispose();
    shellMaterial.dispose();
    inside.material.dispose();
  });
}

test("clipped front faces pass clicks through while the visible rear housing remains selectable", () => {
  const material = new THREE.MeshStandardMaterial({ side: THREE.DoubleSide,
    clippingPlanes: [new THREE.Plane(new THREE.Vector3(0, 0, -1), 0)] });
  const source = new THREE.Mesh(new THREE.BoxGeometry(4, 4, 4), material);
  source.updateMatrixWorld(true);
  const renderer = new AssemblyInstances([source]);
  renderer.sync();
  renderer.root.updateMatrixWorld(true);
  const ray = new THREE.Raycaster(new THREE.Vector3(0, 0, 10), new THREE.Vector3(0, 0, -1));
  const hit = ray.intersectObject(renderer.root, true)[0];
  assert.equal(hit.point.z, -2);
  assert.equal(sourceMesh(hit.object, hit.instanceId), source);
  renderer.dispose();
  source.geometry.dispose();
  material.dispose();
});

test("multi-material copies use the intersected face's clipping and visibility", () => {
  const visible = new THREE.MeshStandardMaterial();
  const front = visible.clone();
  front.clippingPlanes = [new THREE.Plane(new THREE.Vector3(0, 0, -1), 0)];
  const source = new THREE.Mesh(new THREE.BoxGeometry(4, 4, 4), [visible, visible, visible, visible, front, visible]);
  source.updateMatrixWorld(true);
  const renderer = new AssemblyInstances([source]);
  renderer.sync();
  renderer.root.updateMatrixWorld(true);
  const ray = new THREE.Raycaster(new THREE.Vector3(0, 0, 10), new THREE.Vector3(0, 0, -1));
  assert.equal(ray.intersectObject(renderer.root, true).length, 0);
  front.clippingPlanes = null;
  assert.equal(sourceMesh(ray.intersectObject(renderer.root, true)[0].object), source);
  front.visible = false;
  assert.equal(ray.intersectObject(renderer.root, true).length, 0);
  renderer.dispose();
  source.geometry.dispose();
  front.dispose();
  visible.dispose();
});

test("disposing draw batches leaves shared model assets intact", () => {
  const { sources } = fixture();
  const material = new THREE.MeshStandardMaterial();
  for (const source of sources) source.material = material;
  const renderer = new AssemblyInstances(sources);
  renderer.sync();
  assert.equal(renderer.root.children.length, 1);
  assert.equal((renderer.root.children[0] as THREE.InstancedMesh).count, 40);
  let sharedDisposed = false;
  sources[0].geometry.addEventListener("dispose", () => { sharedDisposed = true; });
  material.addEventListener("dispose", () => { sharedDisposed = true; });
  renderer.dispose();
  assert.equal(sharedDisposed, false);
});

test("scan outlines retain every part transform and leave the full-detail geometry unchanged", () => {
  const { sources } = fixture();
  const original = sources[0].geometry;
  const indices = [...original.index!.array];
  const scan = new ScanLines(sources, new THREE.ShaderMaterial());
  assert.equal(scan.root.children.length, 1);
  const geometry = (scan.root.children[0] as THREE.LineSegments).geometry as THREE.InstancedBufferGeometry;
  assert.equal(geometry.instanceCount, sources.length);
  // A box has twelve physical edges; its six triangulation diagonals are unnecessary scan work.
  assert.equal(geometry.getAttribute("position").count, 24);
  const matrices = geometry.getAttribute("scanMatrix").array;
  sources.forEach((source, index) => {
    assert.deepEqual([...matrices.slice(index * 16, index * 16 + 16)], source.matrixWorld.elements);
    assert.equal(source.geometry, original);
  });
  scan.dispose();
  assert.deepEqual([...original.index!.array], indices);
});

test("deferred scan preparation yields before building and produces the same outlines", async () => {
  const { sources } = fixture();
  const material = new THREE.ShaderMaterial();
  const immediate = new ScanLines(sources, material);
  const deferred = new ScanLines(sources, material, true);
  assert.equal(deferred.root.children.length, 0);
  await deferred.ready;
  const expected = (immediate.root.children[0] as THREE.LineSegments).geometry;
  const actual = (deferred.root.children[0] as THREE.LineSegments).geometry;
  assert.deepEqual(actual.getAttribute("position").array, expected.getAttribute("position").array);
  assert.deepEqual(actual.getAttribute("scanMatrix").array, expected.getAttribute("scanMatrix").array);
  immediate.dispose();
  deferred.dispose();
});

test("abandoned deferred scans cannot build or allocate resources after disposal", async () => {
  const { sources } = fixture();
  const scan = new ScanLines(sources, new THREE.ShaderMaterial(), true);
  scan.dispose();
  await scan.ready;
  assert.equal(scan.root.children.length, 0);
});
