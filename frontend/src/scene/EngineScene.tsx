import {
  Component,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import {
  Canvas,
  useFrame,
  useThree,
  type ThreeEvent,
} from "@react-three/fiber";
import {
  OrbitControls,
  ContactShadows,
  Environment,
  Lightformer,
  useGLTF,
} from "@react-three/drei";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import type { ComponentInstance, EngineView, Schema } from "../api/types.ts";
import {
  disposeModel,
  validateMeshMappings,
  type ModuleSpec,
} from "./model.ts";
import preparedEngine from "./prepared-engine.json";

interface Props {
  engine: EngineView;
  selected: string | null;
  explosion: number;
  visualState?: Schema<"VisualState">;
  reducedMotion: boolean;
  focusToken: number;
  onSelect: (id: string) => void;
  hero?: boolean;
  selectedModule?: string | null;
  onSelectModule?: (id: string) => void;
}
class SceneBoundary extends Component<
  { children: ReactNode },
  { error: boolean }
> {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  render() {
    return this.state.error ? (
      <div className="scene-fallback" role="status">
        <strong>The 3D view is unavailable.</strong>
        <p>
          Continue with the component list below. Reload to retry the renderer.
        </p>
      </div>
    ) : (
      this.props.children
    );
  }
}
interface OverlayRefs {
  pins: RefObject<(HTMLButtonElement | null)[]>;
  lines: RefObject<(SVGLineElement | null)[]>;
  host: RefObject<HTMLDivElement | null>;
  onReady: () => void;
}
function SceneModel({
  root,
  clips = [],
  ...props
}: Props & OverlayRefs & { root: THREE.Group; clips?: THREE.AnimationClip[] }) {
  const {
    engine,
    selected,
    explosion,
    visualState,
    onSelect,
    reducedMotion,
    focusToken,
  } = props;
  const controls = useRef<OrbitControlsImpl>(null);
  const { camera, invalidate, size } = useThree();
  const authored = useMemo(() => {
    if (!clips.length) return null;
    const mixer = new THREE.AnimationMixer(root);
    for (const clip of clips) {
      const action = mixer.clipAction(clip);
      action.setLoop(THREE.LoopOnce, 1);
      action.clampWhenFinished = true;
      action.play();
    }
    return { mixer, duration: Math.max(...clips.map((c) => c.duration)) };
  }, [root, clips]);
  useEffect(
    () => () => {
      authored?.mixer.stopAllAction();
      authored?.mixer.uncacheRoot(root);
    },
    [authored, root],
  );
  useEffect(() => {
    props.onReady();
    invalidate();
  }, [root, invalidate]);
  const progress = useRef(explosion);
  const cameraTarget = useRef<THREE.Vector3 | null>(null);
  const eyeTarget = useRef<THREE.Vector3 | null>(null);
  const focusPending = useRef(false);
  useEffect(() => {
    focusPending.current = focusToken > 0;
    cameraTarget.current = new THREE.Vector3(0, 0, 0);
    eyeTarget.current = (
      props.hero
        ? new THREE.Vector3(
            -3.4 - explosion * 1.1,
            1.45 + explosion * 0.65,
            4.5 + explosion * 3,
          )
        : new THREE.Vector3(-5, 2.6, 6.2)
    ).multiplyScalar(
      Math.max(1, (props.hero ? 1.55 : 1.4) / (size.width / size.height)),
    );
    invalidate();
  }, [
    focusToken,
    selected,
    engine.components,
    camera,
    invalidate,
    size.width,
    size.height,
    props.hero ? explosion : 0,
  ]);
  useEffect(() => {
    invalidate();
  }, [explosion, selected, visualState, props.selectedModule, invalidate]);
  useFrame((_, delta) => {
    progress.current = reducedMotion
      ? explosion
      : THREE.MathUtils.damp(
          progress.current,
          explosion,
          10,
          Math.min(delta, 0.1),
        );
    const p = progress.current;
    if (authored) {
      for (const clip of clips) {
        const action = authored.mixer.clipAction(clip);
        action.enabled = true;
        action.paused = false;
      }
      authored.mixer.setTime(p * authored.duration);
    }
    root.traverse((node) => {
      if (typeof node.userData.moduleIndex === "number") {
        if (!authored)
          node.position.x =
            (node.userData.moduleBaseX ?? 0) +
            (node.userData.moduleIndex - 3) * p * (props.hero ? 0.65 : 0.48);
        node.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            for (const material of Array.isArray(child.material)
              ? child.material
              : [child.material]) {
              if (material instanceof THREE.MeshStandardMaterial) {
                material.emissive.set(
                  node.name === props.selectedModule ? "#237f6b" : "#000000",
                );
                material.emissiveIntensity =
                  node.name === props.selectedModule ? 0.22 : 0;
              }
            }
          }
        });
      }
    });
    for (const [index, component] of engine.components.entries()) {
      const mesh = root.getObjectByName(component.mesh_mapping.node_name);
      if (!mesh) continue;
      mesh.position.fromArray(
        mesh.userData.basePosition ?? component.mesh_mapping.hotspot_anchor,
      );
      mesh.position.addScaledVector(
        new THREE.Vector3().fromArray(component.mesh_mapping.exploded_offset),
        p,
      );
      // Separate the three illustrative parts for inspection; this is a demo
      // presentation offset, never a change to sourced geometry or identity.
      if (root.userData.provenance === "procedural_demo") {
        mesh.position.x += (index - 1) * 1.05 * p;
        mesh.position.y += (index === 1 ? 0.32 : 0) * p;
      }
      const active = selected === component.component_id;
      if (
        active &&
        ["removed", "replacement_ready"].includes(visualState ?? "")
      )
        mesh.position.addScaledVector(
          new THREE.Vector3().fromArray(component.mesh_mapping.removal_vector),
          0.75,
        );
      mesh.traverse((child) => {
        if (!(child instanceof THREE.Mesh)) return;
        for (const material of Array.isArray(child.material)
          ? child.material
          : [child.material]) {
          if (material instanceof THREE.MeshStandardMaterial) {
            material.emissive.set(active ? "#207d69" : "#000000");
            material.emissiveIntensity = active ? 0.3 : 0;
          }
        }
      });
    }
    // Focus the rendered part, including its authored module transform and
    // server-gated visual offset; manifest anchors remain source/run metadata.
    if (focusPending.current) {
      const chosen = engine.components.find((c) => c.component_id === selected);
      const mesh =
        chosen && root.getObjectByName(chosen.mesh_mapping.node_name);
      if (mesh) {
        root.updateMatrixWorld(true);
        const anchor = mesh.getWorldPosition(new THREE.Vector3());
        cameraTarget.current = anchor;
        eyeTarget.current = anchor
          .clone()
          .add(
            new THREE.Vector3(-1.8, 1.25, 2.2).multiplyScalar(
              Math.max(1, 1.4 / (size.width / size.height)),
            ),
          );
      }
      focusPending.current = false;
    }
    const labelPositions: THREE.Vector2[] = [];
    for (const [index, component] of engine.components.entries()) {
      const mesh = root.getObjectByName(component.mesh_mapping.node_name);
      const pin = props.pins.current[index],
        line = props.lines.current[index];
      if (!mesh || !pin) continue;
      const point = mesh.getWorldPosition(new THREE.Vector3()).project(camera);
      const x = (point.x * 0.5 + 0.5) * size.width,
        y = (-point.y * 0.5 + 0.5) * size.height;
      let labelX = THREE.MathUtils.clamp(
        x + (index - 1) * 52,
        22,
        size.width - 22,
      );
      let labelY = THREE.MathUtils.clamp(
        y - 44 - index * 22,
        22,
        size.height - 22,
      );
      // Keep the three actionable labels distinct on narrow canvases. Their
      // leaders still terminate at the exact projected mesh positions.
      const offsets = [
        [0, 0],
        [-48, 0],
        [48, 0],
        [0, -48],
        [0, 48],
        [-48, -48],
        [48, -48],
        [-48, 48],
        [48, 48],
      ];
      for (const [dx, dy] of offsets) {
        const candidate = new THREE.Vector2(
          THREE.MathUtils.clamp(labelX + dx, 22, size.width - 22),
          THREE.MathUtils.clamp(labelY + dy, 22, size.height - 22),
        );
        if (
          labelPositions.every(
            (position) => position.distanceTo(candidate) >= 44,
          )
        ) {
          labelX = candidate.x;
          labelY = candidate.y;
          break;
        }
      }
      labelPositions.push(new THREE.Vector2(labelX, labelY));
      pin.style.transform =
        "translate(" + labelX + "px," + labelY + "px) translate(-50%,-50%)";
      pin.style.visibility = point.z < 1 ? "visible" : "hidden";
      if (line) {
        line.setAttribute("x1", String(x));
        line.setAttribute("y1", String(y));
        line.setAttribute("x2", String(labelX));
        line.setAttribute("y2", String(labelY));
      }
    }
    if (eyeTarget.current && cameraTarget.current && controls.current) {
      if (reducedMotion) {
        camera.position.copy(eyeTarget.current);
        controls.current.target.copy(cameraTarget.current);
      } else {
        camera.position.lerp(eyeTarget.current, 1 - Math.exp(-delta * 6));
        controls.current.target.lerp(
          cameraTarget.current,
          1 - Math.exp(-delta * 6),
        );
      }
      controls.current.update();
      if (camera.position.distanceTo(eyeTarget.current) < 0.01) {
        eyeTarget.current = null;
        cameraTarget.current = null;
      } else invalidate();
    }
    if (props.host.current) {
      props.host.current.dataset.settled = String(
        Math.abs(p - explosion) < 0.01 && !eyeTarget.current,
      );
      props.host.current.dataset.separation = p.toFixed(3);
    }
    if (Math.abs(p - explosion) > 0.001) invalidate();
  });
  const select = (e: ThreeEvent<PointerEvent>) => {
    let n: THREE.Object3D | null = e.object;
    while (n && !n.userData.componentId && !n.userData.moduleName) n = n.parent;
    if (n) {
      e.stopPropagation();
      if (n.userData.componentId) onSelect(n.userData.componentId);
      else props.onSelectModule?.(n.userData.moduleName);
    }
  };
  return (
    <>
      <primitive object={root} onPointerDown={select} />
      <OrbitControls
        ref={controls}
        makeDefault
        enablePan={false}
        enableZoom={false}
        minPolarAngle={0.2}
        maxPolarAngle={Math.PI * 0.8}
        onStart={() => {
          eyeTarget.current = null;
          cameraTarget.current = null;
        }}
      />
    </>
  );
}
function Loaded(props: Props & OverlayRefs & { path: string }) {
  const gltf = useGLTF(props.path);
  const model = useMemo(() => {
    const root = gltf.scene.clone(true);
    const modules = props.engine.engine.asset.modules as
      ModuleSpec[] | undefined;
    root.traverse((node) => {
      const index = modules?.findIndex((m) => m.node_name === node.name) ?? -1;
      if (index >= 0) {
        node.userData.moduleIndex = index;
        node.userData.moduleName = node.name;
        node.userData.moduleBaseX = node.position.x;
      }
    });
    root.traverse((n) => {
      if (n instanceof THREE.Mesh) {
        n.geometry = n.geometry.clone();
        n.material = Array.isArray(n.material)
          ? n.material.map((m) => m.clone())
          : n.material.clone();
      }
    });
    const errors = validateMeshMappings(root, props.engine.components);
    if (errors.length) throw new Error(errors.join(" "));
    return root;
  }, [gltf.scene, props.engine.components]);
  useEffect(() => () => disposeModel(model), [model]);
  return (
    <SceneModel
      {...props}
      root={model}
      clips={
        props.path === preparedEngine.asset_url ? gltf.animations : undefined
      }
    />
  );
}
export default function EngineScene(props: Props) {
  const [lost, setLost] = useState(false);
  const [readyPath, setReadyPath] = useState<string | null>(null);
  const pins = useRef<(HTMLButtonElement | null)[]>([]),
    lines = useRef<(SVGLineElement | null)[]>([]),
    host = useRef<HTMLDivElement>(null);
  // Compatible presentation upgrade applies to persisted runs too. Never replace
  // an activated user mesh, change a run, or rewrite its evidence/part identities.
  const uploadedPath = props.engine.engine.asset.glb_path;
  const path =
    typeof uploadedPath === "string" && uploadedPath
      ? uploadedPath
      : props.engine.engine.engine_id === "engine-demo-001"
        ? preparedEngine.asset_url
        : null;
  const ready = !!path && readyPath === path;
  const overlay = { pins, lines, host, onReady: () => setReadyPath(path) };
  return (
    <div
      className="scene-root"
      ref={host}
      data-ready={ready}
      data-asset={path ?? "unavailable"}
    >
      <SceneBoundary
        key={path ?? props.engine.engine.scenario_manifest_version}
      >
        {!path ? (
          <div className="scene-fallback" role="status">
            No model is connected. Use the component list to continue.
          </div>
        ) : lost ? (
          <div className="scene-fallback">
            3D graphics were interrupted. The component list remains available.
          </div>
        ) : (
          <Canvas
            frameloop="demand"
            dpr={[1, 1.5]}
            camera={{
              position: props.hero ? [-3.4, 1.45, 4.5] : [-5, 2.6, 6.2],
              fov: props.hero ? 30 : 34,
            }}
            gl={{ antialias: true, alpha: true }}
            onCreated={({ gl }) =>
              gl.domElement.addEventListener(
                "webglcontextlost",
                () => setLost(true),
                { once: true },
              )
            }
            fallback={
              <div className="scene-fallback">
                Use the component list to continue without 3D.
              </div>
            }
          >
            <ambientLight intensity={0.45} />
            <directionalLight position={[-3, 5, 4]} intensity={2.2} />
            <directionalLight position={[4, 2, -3]} intensity={1.4} />
            <Suspense fallback={null}>
              <Environment resolution={128}>
                <Lightformer
                  form="rect"
                  intensity={3}
                  position={[0, 5, 0]}
                  rotation={[Math.PI / 2, 0, 0]}
                  scale={[10, 4, 1]}
                />
                <Lightformer
                  form="rect"
                  intensity={2}
                  position={[-5, 0, 3]}
                  scale={[3, 6, 1]}
                />
              </Environment>
              {typeof path === "string" && path ? (
                <Loaded {...props} {...overlay} path={path} />
              ) : null}
              <ContactShadows
                position={[0, -1.25, 0]}
                opacity={0.25}
                scale={14}
                blur={2.8}
                far={3}
                frames={1}
              />
            </Suspense>
          </Canvas>
        )}
      </SceneBoundary>
      {ready && !lost && (
        <div className="mesh-overlay">
          <svg aria-hidden="true">
            {props.engine.components.map((c, i) => (
              <line
                key={c.component_id}
                ref={(node) => {
                  lines.current[i] = node;
                }}
                stroke="#8aa894"
                strokeWidth="1"
              />
            ))}
          </svg>
          {props.engine.components.map((c, i) => (
            <button
              key={c.component_id}
              ref={(node) => {
                pins.current[i] = node;
              }}
              className={
                "mesh-pin " +
                (props.selected === c.component_id ? "active" : "")
              }
              onClick={() => props.onSelect(c.component_id)}
              aria-label={"Select " + c.display_name}
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
