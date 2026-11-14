import {
  Component,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  Canvas,
  useFrame,
  useThree,
  type ThreeEvent,
} from "@react-three/fiber";
import {
  ContactShadows,
  Environment,
  Lightformer,
  OrbitControls,
  useGLTF,
} from "@react-three/drei";
import * as THREE from "three";
import assembly from "./toy-car.json";

class Boundary extends Component<
  { children: ReactNode; onError: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onError();
  }
  render() {
    return this.state.failed ? (
      <div className="scene-fallback">
        The 3D view could not load. You can still select parts from the list.
      </div>
    ) : (
      this.props.children
    );
  }
}
type Props = {
  selected: string[];
  separation: number;
  reduced: boolean;
  onSelect: (id: string) => void;
};
function Model({
  selected,
  separation,
  reduced,
  onSelect,
  onReady,
}: Props & { onReady: () => void }) {
  const { scene } = useGLTF(assembly.asset_url);
  const { invalidate } = useThree();
  const root = useMemo(() => {
    const r = scene.clone(true);
    r.traverse((o) => {
      if (o instanceof THREE.Mesh) {
        o.material = Array.isArray(o.material)
          ? o.material.map((m) => m.clone())
          : o.material.clone();
      }
    });
    return r;
  }, [scene]);
  const parts = useMemo(
    () =>
      assembly.components.map((p) => {
        const node = root.getObjectByName(p.node_name);
        return {
          ...p,
          node,
          start: node?.position.clone() ?? new THREE.Vector3(),
        };
      }),
    [root],
  );
  const originalEmission = useMemo(() => {
    const materials = new Map<
      THREE.MeshStandardMaterial,
      { color: THREE.Color; intensity: number; map: THREE.Texture | null }
    >();
    root.traverse((o) => {
      if (o instanceof THREE.Mesh)
        for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
          if (m instanceof THREE.MeshStandardMaterial)
            materials.set(m, {
              color: m.emissive.clone(),
              intensity: m.emissiveIntensity,
              map: m.emissiveMap,
            });
        }
    });
    return materials;
  }, [root]);
  const progress = useRef(separation);
  useEffect(() => {
    onReady();
    invalidate();
    return () =>
      root.traverse((o) => {
        if (o instanceof THREE.Mesh)
          (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) =>
            m.dispose(),
          );
      });
  }, [root]);
  useEffect(() => {
    for (const p of parts)
      p.node?.traverse((o) => {
        if (o instanceof THREE.Mesh) {
          for (const m of Array.isArray(o.material) ? o.material : [o.material])
            if (m instanceof THREE.MeshStandardMaterial) {
              const original = originalEmission.get(m)!;
              const active = selected.includes(p.component_id);
              m.emissive.copy(
                active ? new THREE.Color("#2251ef") : original.color,
              );
              m.emissiveIntensity = active ? 0.85 : original.intensity;
              // Selection must not be masked by the asset's emissive texture.
              const map = active ? null : original.map;
              if (m.emissiveMap !== map) {
                m.emissiveMap = map;
                m.needsUpdate = true;
              }
            }
        }
      });
    invalidate();
  }, [selected, parts, originalEmission, invalidate]);
  useEffect(() => {
    invalidate();
  }, [separation, invalidate]);
  useFrame((_, dt) => {
    progress.current = reduced
      ? separation
      : THREE.MathUtils.damp(
          progress.current,
          separation,
          10,
          Math.min(dt, 0.1),
        );
    for (const p of parts)
      p.node?.position
        .copy(p.start)
        .addScaledVector(
          new THREE.Vector3(...(p.explode as [number, number, number])),
          progress.current,
        );
    if (Math.abs(progress.current - separation) > 0.0005) invalidate();
  });
  const pick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    let node: THREE.Object3D | null = e.object;
    while (node) {
      const p = parts.find((p) => p.node === node);
      if (p) {
        onSelect(p.component_id);
        break;
      }
      node = node.parent;
    }
  };
  return <primitive object={root} onClick={pick} />;
}
function Camera() {
  const { camera, size, invalidate } = useThree();
  useEffect(() => {
    const factor = Math.max(1, 1.5 / (size.width / size.height));
    camera.position.set(5.6 * factor, 3.7 * factor, 6.5 * factor);
    camera.lookAt(0, 0.6, 0);
    invalidate();
  }, [camera, size, invalidate]);
  return (
    <OrbitControls
      target={[0, 0.6, 0]}
      enablePan={false}
      enableZoom={false}
      minPolarAngle={0.3}
      maxPolarAngle={Math.PI / 2.05}
    />
  );
}
export default function ProductScene(props: Props) {
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  return (
    <div
      className="product-scene"
      data-ready={status === "ready"}
      data-status={status}
      data-separation={props.separation.toFixed(3)}
    >
      <Boundary onError={() => setStatus("error")}>
        <Canvas
          frameloop="demand"
          dpr={[1, 1.5]}
          camera={{ fov: 38, near: 0.1, far: 60 }}
          gl={{ antialias: true, alpha: true }}
        >
          <ambientLight intensity={0.7} />
          <directionalLight position={[3, 7, 4]} intensity={3} />
          <Suspense fallback={null}>
            <Model {...props} onReady={() => setStatus("ready")} />
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
            <ContactShadows
              position={[0, -0.12, 0]}
              opacity={0.24}
              blur={2.6}
              scale={15}
              far={4}
            />
          </Suspense>
          <Camera />
        </Canvas>
      </Boundary>
      {status === "loading" && (
        <span className="model-loading">Loading the prepared assembly…</span>
      )}
    </div>
  );
}
