import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import type { ComponentInstance } from "../api/types.ts";

export interface ModuleSpec {
  node_name: string;
  label: string;
  x_range: [number, number];
}
export const demoModules: ModuleSpec[] = [
  { node_name: "Module_Fan", label: "Fan", x_range: [-2, -1.3] },
  { node_name: "Module_LPC", label: "Booster", x_range: [-1.3, -0.9] },
  { node_name: "Module_HPC", label: "Compressor", x_range: [-0.9, -0.15] },
  { node_name: "Module_Combustor", label: "Combustor", x_range: [-0.15, 0.35] },
  { node_name: "Module_HPT", label: "HP turbine", x_range: [0.35, 0.6] },
  { node_name: "Module_LPT", label: "LP turbine", x_range: [0.6, 1.2] },
  { node_name: "Module_Exhaust", label: "Exhaust", x_range: [1.2, 1.8] },
];
function alloy(color: string, roughness = 0.36) {
  return new THREE.MeshStandardMaterial({
    color,
    metalness: 0.72,
    roughness,
    side: THREE.DoubleSide,
  });
}
function lathe(points: [number, number][], segments = 64) {
  return new THREE.LatheGeometry(
    points.map(([radius, x]) => new THREE.Vector2(radius, x)),
    segments,
  ).rotateZ(-Math.PI / 2);
}
function ring(x: number, r: number, thickness: number) {
  return new THREE.TorusGeometry(r, thickness, 8, 64)
    .rotateY(Math.PI / 2)
    .translate(x, 0, 0);
}
// Curved, twisted blade surfaces, repeated around the engine axis. These are
// intentionally illustrative meshes, never manufactured geometry or dimensions.
function rotor(
  x: number,
  root: number,
  tip: number,
  count: number,
  chord: number,
) {
  const positions: number[] = [],
    indices: number[] = [];
  const radialSteps = 24,
    chordSteps = 8;
  const point = (t: number, u: number, angle: number) => {
    const r = root + (tip - root) * t;
    const a = angle + ((u - 0.5) * chord * (1 - 0.2 * t)) / r + t * t * 0.24;
    return [
      x + (u - 0.5) * 0.22 + t * 0.07 + Math.sin(u * Math.PI) * 0.035,
      Math.cos(a) * r,
      Math.sin(a) * r,
    ];
  };
  for (let k = 0; k < count; k++) {
    const offset = positions.length / 3;
    for (let t = 0; t <= radialSteps; t++)
      for (let u = 0; u <= chordSteps; u++)
        positions.push(
          ...point(t / radialSteps, u / chordSteps, (k / count) * Math.PI * 2),
        );
    for (let t = 0; t < radialSteps; t++)
      for (let u = 0; u < chordSteps; u++) {
        const a = offset + t * (chordSteps + 1) + u,
          b = a + chordSteps + 1;
        indices.push(a, b, b + 1, a, b + 1, a + 1);
      }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  g.setIndex(indices);
  g.computeVertexNormals();
  return g;
}
function solid(
  geometry: THREE.BufferGeometry,
  material: THREE.Material,
  name: string,
) {
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = name;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}
export function createDemoEngine(
  components: ComponentInstance[],
  modules = demoModules,
) {
  const root = new THREE.Group();
  root.name = "Representative_RS_TF2";
  root.userData.provenance = "procedural_demo";
  const silver = alloy("#7c8c91", 0.28),
    dark = alloy("#26383f", 0.32),
    copper = alloy("#8f6344", 0.3),
    polished = alloy("#b3bfc3", 0.2);
  const radii = [1.04, 0.66, 0.54, 0.55, 0.48, 0.51, 0.48];
  modules.forEach((spec, index) => {
    const group = new THREE.Group();
    group.name = spec.node_name;
    group.userData.moduleIndex = index;
    group.userData.moduleName = spec.node_name;
    const [start, end] = spec.x_range,
      r = radii[index] ?? 0.5,
      mid = (start + end) / 2;
    group.add(solid(ring(start + 0.04, r, 0.025), polished, "Forward ring"));
    group.add(solid(ring(end - 0.04, r, 0.025), polished, "Rear ring"));
    if (index === 0) {
      group.add(
        solid(
          lathe([
            [1.02, start],
            [1.12, start + 0.06],
            [1.13, start + 0.18],
            [1.08, end],
            [1.02, end],
            [1.02, start],
          ]),
          silver,
          "Intake shroud",
        ),
      );
      group.add(
        solid(rotor(start + 0.25, 0.2, 0.99, 24, 0.18), polished, "Fan blades"),
      );
      group.add(
        solid(
          lathe([
            [0, start - 0.16],
            [0.12, start - 0.1],
            [0.22, start + 0.25],
            [0.19, end],
            [0, end],
          ]),
          dark,
          "Spinner",
        ),
      );
    } else if (index === 3) {
      group.add(
        solid(
          lathe([
            [r - 0.03, start],
            [r, start + 0.04],
            [r, end - 0.04],
            [r - 0.03, end],
            [r - 0.07, end],
            [r - 0.07, start],
          ]),
          copper,
          "Combustor liner",
        ),
      );
      for (let j = 0; j < 20; j++) {
        const a = (j / 20) * Math.PI * 2;
        const g = new THREE.CylinderGeometry(0.026, 0.026, end - start - 0.1, 8)
          .rotateZ(Math.PI / 2)
          .translate(mid, Math.cos(a) * (r + 0.02), Math.sin(a) * (r + 0.02));
        group.add(solid(g, dark, "Fuel manifold tube"));
      }
    } else if (index === 6) {
      group.add(
        solid(
          lathe([
            [r, start],
            [r + 0.015, start + 0.04],
            [0.32, end],
            [0.3, end],
            [r - 0.03, start],
          ]),
          dark,
          "Nozzle casing",
        ),
      );
      group.add(
        solid(
          lathe([
            [0.2, start],
            [0.24, start + 0.1],
            [0.05, end + 0.16],
            [0, end + 0.2],
          ]),
          silver,
          "Exhaust cone",
        ),
      );
    } else {
      const stages = index === 2 ? 5 : index === 5 ? 3 : 2;
      for (let j = 0; j < stages; j++) {
        const x =
          start + 0.08 + ((end - start - 0.16) * j) / Math.max(1, stages - 1);
        group.add(
          solid(
            rotor(x, 0.17, r - 0.035, 32 + j * 2, 0.085),
            j % 2 ? dark : silver,
            "Blade row " + j,
          ),
        );
        group.add(solid(ring(x, r, 0.012), polished, "Stage tip ring"));
      }
      group.add(
        solid(
          lathe([
            [0.14, start],
            [0.19, mid],
            [0.16, end],
          ]),
          dark,
          "Core shaft",
        ),
      );
    }
    group.traverse((n) => {
      if (n instanceof THREE.Mesh)
        n.material = Array.isArray(n.material)
          ? n.material.map((m) => m.clone())
          : n.material.clone();
    });
    root.add(group);
  });
  components.forEach((component, index) => {
    let geometry: THREE.BufferGeometry;
    if (index === 0) {
      geometry = mergeGeometries([
        new THREE.CylinderGeometry(0.045, 0.055, 0.28, 24),
        new THREE.CylinderGeometry(0.085, 0.085, 0.035, 24).translate(
          0,
          0.09,
          0,
        ),
        new THREE.CylinderGeometry(0.035, 0.06, 0.08, 24).translate(
          0,
          -0.16,
          0,
        ),
      ])!;
    } else if (index === 1) {
      geometry = mergeGeometries([
        new THREE.BoxGeometry(0.18, 0.035, 0.18).translate(0, 0.13, 0),
        new THREE.BoxGeometry(0.18, 0.035, 0.18).translate(0, -0.13, 0),
        new THREE.BoxGeometry(0.035, 0.25, 0.13).rotateY(0.3),
      ])!;
    } else {
      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(-0.16, -0.05, 0),
        new THREE.Vector3(0, -0.05, 0),
        new THREE.Vector3(0.1, 0.06, 0),
        new THREE.Vector3(0.1, 0.2, 0),
      ]);
      geometry = mergeGeometries([
        new THREE.TubeGeometry(curve, 20, 0.045, 16, false),
        new THREE.CylinderGeometry(0.08, 0.08, 0.025, 24).translate(
          0.1,
          0.2,
          0,
        ),
      ])!;
    }
    const mesh = solid(
      geometry,
      alloy("#d09550", 0.3),
      component.mesh_mapping.node_name,
    );
    mesh.position.fromArray(component.mesh_mapping.hotspot_anchor);
    mesh.userData.componentId = component.component_id;
    mesh.userData.basePosition = mesh.position.toArray();
    root.add(mesh);
  });
  return root;
}

export function validateMeshMappings(
  root: THREE.Object3D,
  components: ComponentInstance[],
) {
  const errors: string[] = [];
  for (const component of components) {
    const matches: THREE.Object3D[] = [];
    root.traverse((n) => {
      if (n.name === component.mesh_mapping.node_name) matches.push(n);
    });
    if (matches.length !== 1) {
      errors.push(
        `${component.part_identity}: expected one named mesh, found ${matches.length}.`,
      );
      continue;
    }
    const node = matches[0];
    const meshes: THREE.Mesh[] = [];
    node.traverse((child) => {
      if (child instanceof THREE.Mesh) meshes.push(child);
    });
    const usable = meshes.some((mesh) => {
      const position = mesh.geometry.getAttribute("position");
      if (!position || position.count < 3) return false;
      mesh.geometry.computeBoundingBox();
      const size = new THREE.Vector3();
      mesh.geometry.boundingBox?.getSize(size);
      return (
        [size.x, size.y, size.z].filter((v) => Number.isFinite(v) && v > 1e-6)
          .length >= 2
      );
    });
    if (!usable) {
      errors.push(
        `${component.part_identity}: node has no usable mesh geometry.`,
      );
      continue;
    }
    node.userData.componentId = component.component_id;
    node.userData.basePosition = node.position.toArray();
  }
  return errors;
}

export function disposeModel(root: THREE.Object3D) {
  const materials = new Set<THREE.Material>();
  root.traverse((n) => {
    if (n instanceof THREE.Mesh) {
      n.geometry.dispose();
      (Array.isArray(n.material) ? n.material : [n.material]).forEach((m) =>
        materials.add(m),
      );
    }
  });
  materials.forEach((m) => m.dispose());
}
