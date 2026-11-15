import * as THREE from "three";

type Batch = { mesh: THREE.InstancedMesh; sources: THREE.Mesh[] };

/** Render repeated geometry together, retaining the source hierarchy for part identity and animation. */
export class AssemblyInstances {
  readonly root = new THREE.Group();
  private batches = new Map<string, Batch>();
  private capacities = new Map<THREE.BufferGeometry, number>();
  private singles = new Map<THREE.Mesh, THREE.Mesh>();
  private sources: THREE.Mesh[];

  constructor(sources: THREE.Mesh[]) {
    this.sources = sources;
    for (const source of sources) {
      this.capacities.set(source.geometry, (this.capacities.get(source.geometry) ?? 0) + 1);
    }
  }

  /** Call after source transforms, visibility or materials change, never just for camera motion. */
  sync() {
    for (const batch of this.batches.values()) { batch.mesh.count = 0; batch.sources.length = 0; }
    for (const mesh of this.singles.values()) mesh.visible = false;
    for (const source of this.sources) {
      if (!source.visible) continue;
      const material = source.material;
      // Preserve per-object transparency sorting, multi-material and deformed meshes.
      if (Array.isArray(material) || material.transparent ||
          source.geometry.morphAttributes.position || (source as THREE.SkinnedMesh).isSkinnedMesh ||
          source.matrixWorld.determinant() < 0) {
        let copy = this.singles.get(source);
        if (!copy) {
          copy = source.clone(false);
          copy.matrixAutoUpdate = false;
          copy.userData = { source };
          const raycast = copy.raycast;
          copy.raycast = function (raycaster, hits) {
            if (this.visible) raycast.call(this, raycaster, hits);
          };
          this.singles.set(source, copy);
          this.root.add(copy);
        }
        copy.visible = true;
        copy.material = material;
        copy.renderOrder = source.renderOrder;
        copy.matrix.copy(source.matrixWorld);
        copy.matrixWorldNeedsUpdate = true;
        continue;
      }
      const key = `${source.geometry.uuid}:${material.uuid}:${source.renderOrder}`;
      let batch = this.batches.get(key);
      if (!batch) {
        const mesh = new THREE.InstancedMesh(source.geometry, material, this.capacities.get(source.geometry)!);
        mesh.count = 0;
        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        mesh.matrixAutoUpdate = false;
        mesh.renderOrder = source.renderOrder;
        batch = { mesh, sources: [] };
        mesh.userData.sources = batch.sources;
        this.batches.set(key, batch);
        this.root.add(mesh);
      }
      batch.mesh.setMatrixAt(batch.mesh.count++, source.matrixWorld);
      batch.sources.push(source);
    }
    for (const { mesh } of this.batches.values()) {
      mesh.visible = mesh.count > 0;
      if (!mesh.visible) continue;
      mesh.instanceMatrix.needsUpdate = true;
      // Bounds must follow exploded and reassembled parts (including raycasting).
      mesh.computeBoundingSphere();
      mesh.computeBoundingBox();
    }
  }

  dispose() {
    for (const { mesh } of this.batches.values()) mesh.dispose();
    // Geometry and materials belong to the cached GLTF / scene, not these draw batches.
  }
}

export function sourceMesh(object: THREE.Object3D, instanceId?: number): THREE.Mesh | undefined {
  return instanceId == null ? object.userData.source : object.userData.sources?.[instanceId];
}
