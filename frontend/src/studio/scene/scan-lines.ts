import * as THREE from "three";

/** Technical scan outlines omit dense tessellation seams; the solid model is untouched. */
export class ScanLines {
  readonly root = new THREE.Group();
  readonly ready: Promise<void>;
  private geometries: THREE.InstancedBufferGeometry[] = [];
  private disposed = false;

  constructor(sources: THREE.Mesh[], material: THREE.ShaderMaterial, deferred = false) {
    const groups = new Map<THREE.BufferGeometry, THREE.Mesh[]>();
    for (const source of sources) {
      const group = groups.get(source.geometry) ?? [];
      group.push(source);
      groups.set(source.geometry, group);
    }
    const build = ([sourceGeometry, meshes]: [THREE.BufferGeometry, THREE.Mesh[]]) => {
      // A five-degree crease retains fine part outlines without drawing every triangulation diagonal.
      const edges = new THREE.EdgesGeometry(sourceGeometry, 5);
      const geometry = new THREE.InstancedBufferGeometry();
      geometry.setAttribute("position", edges.getAttribute("position"));
      const matrices = new Float32Array(meshes.length * 16);
      meshes.forEach((mesh, index) => mesh.matrixWorld.toArray(matrices, index * 16));
      geometry.setAttribute("scanMatrix", new THREE.InstancedBufferAttribute(matrices, 16));
      geometry.instanceCount = meshes.length;
      const lines = new THREE.LineSegments(geometry, material);
      // The GPU applies the per-part world transforms. Use the whole assembly's bounds.
      const box = new THREE.Box3();
      for (const mesh of meshes) box.expandByObject(mesh);
      geometry.boundingBox = box;
      geometry.boundingSphere = box.getBoundingSphere(new THREE.Sphere());
      lines.raycast = () => {};
      this.root.add(lines);
      this.geometries.push(geometry);
    };
    if (deferred) {
      // Let input/paint run between small preparation batches instead of blocking one frame.
      this.ready = (async () => {
        await new Promise(resolve => setTimeout(resolve, 0));
        let deadline = performance.now() + 8;
        for (const entry of groups) {
          if (this.disposed) return;
          build(entry);
          if (performance.now() >= deadline) {
            await new Promise(resolve => setTimeout(resolve, 0));
            deadline = performance.now() + 8;
          }
        }
      })();
    } else {
      groups.forEach((meshes, geometry) => build([geometry, meshes]));
      this.ready = Promise.resolve();
    }
  }

  dispose() {
    this.disposed = true;
    this.geometries.forEach(geometry => geometry.dispose());
  }
}
