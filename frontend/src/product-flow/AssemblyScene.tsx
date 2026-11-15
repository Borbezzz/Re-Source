import {
  Component,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import {
  Canvas,
  useFrame,
  useThree,
  type ThreeEvent,
} from "@react-three/fiber";
import {
  Environment,
  Lightformer,
  OrbitControls,
  useGLTF,
} from "@react-three/drei";
import * as THREE from "three";
import type { ProductModel, ProductPart } from "./types.ts";

class SceneBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="pf-scene-notice">
        The 3D view could not load. Select parts using the list alongside it.
      </div>
    ) : (
      this.props.children
    );
  }
}
type Props = {
  model: ProductModel;
  parts: ProductPart[];
  selected: string[];
  separation: number;
  reduced: boolean;
  onSelect: (id: string) => void;
};
function Model({
  model,
  parts,
  selected,
  separation,
  reduced,
  onSelect,
}: Props) {
  const { scene } = useGLTF(model.asset_url!);
  const { invalidate } = useThree();
  const root = useMemo(() => {
    const clone = scene.clone(true);
    clone.traverse((o) => {
      if (o instanceof THREE.Mesh) {
        o.material = Array.isArray(o.material)
          ? o.material.map((m) => m.clone())
          : o.material.clone();
      }
    });
    return clone;
  }, [scene]);
  const fitting = useMemo(() => {
    root.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(root),
      size = box.getSize(new THREE.Vector3()),
      center = box.getCenter(new THREE.Vector3());
    const scale = 4 / Math.max(size.x, size.y, size.z, 0.01);
    return { scale, position: center.multiplyScalar(-scale) };
  }, [root]);
  const basePositions = useMemo(() => {
    const positions = new Map<THREE.Object3D, THREE.Vector3>();
    root.traverse((node) => positions.set(node, node.position.clone()));
    return positions;
  }, [root]);
  const nodes = useMemo(
    () =>
      parts.flatMap((part, index) =>
        part.node_names.flatMap((name) => {
          const node = root.getObjectByName(name);
          if (!node) return [];
          const direction = (part as ProductPart & { explode?: number[] })
            .explode ?? [
            ((index % 3) - 1) * 0.8,
            (index % 2 ? 1 : -1) * 0.6,
            ((index % 4) - 1.5) * 0.5,
          ];
          return [
            {
              partId: part.part_id,
              node,
              start: basePositions.get(node)!.clone(),
              direction: new THREE.Vector3(
                ...(direction as [number, number, number]),
              ),
            },
          ];
        }),
      ),
    [parts, root, basePositions],
  );
  const emissions = useMemo(() => {
    const map = new Map<
      THREE.MeshStandardMaterial,
      { color: THREE.Color; intensity: number; map: THREE.Texture | null }
    >();
    root.traverse((o) => {
      if (o instanceof THREE.Mesh)
        for (const m of Array.isArray(o.material) ? o.material : [o.material])
          if (m instanceof THREE.MeshStandardMaterial)
            map.set(m, {
              color: m.emissive.clone(),
              intensity: m.emissiveIntensity,
              map: m.emissiveMap,
            });
    });
    return map;
  }, [root]);
  useEffect(() => {
    for (const [material, original] of emissions) {
      material.emissive.copy(original.color);
      material.emissiveIntensity = original.intensity;
      material.emissiveMap = original.map;
      material.needsUpdate = true;
    }
    for (const { partId, node } of nodes)
      node.traverse((o) => {
        if (o instanceof THREE.Mesh)
          for (const m of Array.isArray(o.material) ? o.material : [o.material])
            if (m instanceof THREE.MeshStandardMaterial) {
              const original = emissions.get(m)!;
              const active = selected.includes(partId);
              m.emissive.copy(
                active ? new THREE.Color("#719dff") : original.color,
              );
              m.emissiveIntensity = active ? 0.6 : original.intensity;
              m.emissiveMap = active ? null : original.map;
              m.needsUpdate = true;
            }
      });
    invalidate();
  }, [selected, nodes, emissions, invalidate]);
  useEffect(
    () => () => {
      root.traverse((object) => {
        if (object instanceof THREE.Mesh)
          for (const material of Array.isArray(object.material)
            ? object.material
            : [object.material])
            material.dispose();
      });
    },
    [root],
  );
  useEffect(() => {
    invalidate();
  }, [separation, invalidate]);
  useEffect(() => {
    for (const [node, position] of basePositions) node.position.copy(position);
    invalidate();
  }, [nodes, basePositions, invalidate]);
  const amount = useRef(separation);
  useFrame((_, dt) => {
    amount.current = reduced
      ? separation
      : THREE.MathUtils.damp(amount.current, separation, 9, Math.min(dt, 0.1));
    for (const p of nodes)
      p.node.position
        .copy(p.start)
        .addScaledVector(p.direction, amount.current);
    if (Math.abs(amount.current - separation) > 0.0005) invalidate();
  });
  const pick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    let node: THREE.Object3D | null = event.object;
    while (node) {
      const match = nodes.find((p) => p.node === node);
      if (match) {
        onSelect(match.partId);
        return;
      }
      node = node.parent;
    }
  };
  return (
    <group scale={fitting.scale} position={fitting.position}>
      <primitive object={root} onClick={pick} />
    </group>
  );
}
function LoadingModel() {
  return (
    <div className="pf-scene-notice" role="status">
      Loading assembly…
    </div>
  );
}
export default function AssemblyScene(props: Props) {
  return (
    <div className="pf-model-canvas">
      <SceneBoundary key={props.model.asset_url}>
        <Suspense fallback={<LoadingModel />}>
          <Canvas
            frameloop="demand"
            dpr={[1, 1.5]}
            camera={{ position: [5, 3.5, 6], fov: 38, near: 0.01, far: 150 }}
          >
            <ambientLight intensity={1.4} />
            <directionalLight position={[4, 6, 5]} intensity={3} />
            <directionalLight position={[-4, 2, -3]} intensity={2} />
            <Model {...props} />
            <Environment resolution={128}>
              <Lightformer
                position={[0, 5, -3]}
                rotation={[Math.PI / 2, 0, 0]}
                scale={[8, 5, 1]}
                intensity={4}
              />
              <Lightformer
                position={[-5, 2, 2]}
                rotation={[0, Math.PI / 2, 0]}
                scale={[4, 6, 1]}
                intensity={3}
              />
              <Lightformer
                position={[5, 1, 0]}
                rotation={[0, -Math.PI / 2, 0]}
                scale={[3, 5, 1]}
                intensity={2}
              />
            </Environment>
            <OrbitControls enablePan={false} minDistance={4} maxDistance={15} />
          </Canvas>
        </Suspense>
      </SceneBoundary>
    </div>
  );
}
