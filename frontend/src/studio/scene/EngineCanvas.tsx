import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { CameraControls, Environment, Html, Lightformer, useGLTF } from "@react-three/drei";
import { Suspense, useEffect, useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import type { PackageComponent } from "../data/package.ts";
import type { AssemblyItem } from "../data/assembly.ts";

/*
 * Art direction follows Astra's (gpt-6-astra) review in
 * frontend/design/astra-review/astra-3d-review.md: AgX tone mapping, four
 * neutral reflection cards, satin (not chrome) metals, intake-preserving
 * cutaway, bounds-fitted framing, opaque context isolation, a narrow thermal
 * Fresnel rim on the selection, and a thin scan band rather than additive fog.
 */

export type SceneMode = "scan" | "explore" | "hidden";
export type ReassemblyPhase = "idle" | "remove" | "insert" | "done";

export interface EngineCanvasProps {
  url: string;
  mode: SceneMode;
  /** 0..1 wireframe scan progress (processing stage) */
  scan: number;
  /** 0..1 solid metal sweep (reveal after confirmation) */
  solid: number;
  components: PackageComponent[];
  selected: string | null;
  inspection?: AssemblyItem | null;
  hovered?: AssemblyItem | null;
  onInspect?: (id: string) => void;
  exploded: boolean;
  isolate: boolean;
  spin: boolean;
  phase: ReassemblyPhase;
  showHotspots: boolean;
  resetKey: number;
  onSelect?: (componentId: string | null) => void;
  /** pixels reserved on the right / left for overlay panels (camera framing) */
  rightInset?: number;
  leftInset?: number;
  onReady?: () => void;
  /** Keep the whole assembly in frame while a selected part animates. */
  wide?: boolean;
}

// Engine axis is X: fan/intake at -X, exhaust at +X. World X is centred.
const BOUNDS = { min: -4.03, max: 5.1 };
const CENTER_X = (BOUNDS.min + BOUNDS.max) / 2;
const WMIN = BOUNDS.min - CENTER_X;
const WLEN = BOUNDS.max - BOUNDS.min;
const LIP_X = -2.85; // world X: casing ahead of this stays whole (intake lip + fan silhouette)
const VIEW_DIR = new THREE.Vector3(-0.55, 0.22, 1).normalize();
const EXPLODE: Record<string, [number, number, number]> = {
  fan: [-1.9, 0, 0],
  compressor: [-0.85, 0, 0],
  combustor: [0.15, 0, 0],
  turbine: [1.05, 0, 0],
  nozzle: [2.2, 0, 0],
  shaft: [0, 0, 0],
  casing: [0, 3.4, 0],
};
/** Per-part inspection framing: view direction, fit factor and minimum radius. */
const FOCUS: Record<string, { dir: THREE.Vector3; k: number; minR: number; axis?: number }> = {
  "RS-TF-FAN-BLADE": { dir: new THREE.Vector3(-1, 0.3, 0.62).normalize(), k: 2.15, minR: 1.15, axis: 0.45 },
  "RS-TF-FUEL-INJECTOR": { dir: new THREE.Vector3(-0.35, 0.4, 1).normalize(), k: 2.6, minR: 0.5 },
  "RS-TF-CORE-NOZZLE": { dir: new THREE.Vector3(0.75, 0.3, 1).normalize(), k: 1.55, minR: 1.2 },
};
/** Assemblies kept (opaque, subdued) around a selected part; the rest hides. */
const CONTEXT: Record<string, string[]> = {
  "RS-TF-FAN-BLADE": ["fan"],
  "RS-TF-FUEL-INJECTOR": ["combustor"],
  "RS-TF-CORE-NOZZLE": ["nozzle", "turbine"],
};

const THERMAL_STOPS = ["#38BDF8", "#8B5CF6", "#EC4899", "#FB923C"].map((c) => new THREE.Color(c)); // linear RGB
const THERMAL_GLSL = /* glsl */ `
uniform vec3 uT0; uniform vec3 uT1; uniform vec3 uT2; uniform vec3 uT3;
vec3 thermalLinear(float t){
  t = clamp(t, 0.0, 1.0);
  if (t < 0.4) return mix(uT0, uT1, t / 0.4);
  if (t < 0.72) return mix(uT1, uT2, (t - 0.4) / 0.32);
  return mix(uT2, uT3, (t - 0.72) / 0.28);
}`;
const thermalUniforms = () => ({
  uT0: { value: THERMAL_STOPS[0] },
  uT1: { value: THERMAL_STOPS[1] },
  uT2: { value: THERMAL_STOPS[2] },
  uT3: { value: THERMAL_STOPS[3] },
});

function makeScanMaterial() {
  return new THREE.ShaderMaterial({
    wireframe: true,
    transparent: true,
    depthWrite: false,
    depthTest: true,
    blending: THREE.NormalBlending,
    uniforms: { uReveal: { value: WMIN }, uSolid: { value: WMIN - 1 }, ...thermalUniforms() },
    vertexShader: /* glsl */ `
      varying float vX;
      void main(){
        vec4 wp = modelMatrix * vec4(position, 1.0);
        vX = wp.x;
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader: /* glsl */ `
      uniform float uReveal; uniform float uSolid;
      varying float vX;
      ${THERMAL_GLSL}
      void main(){
        float behind = uReveal - vX;
        if (behind < 0.0 || vX < uSolid) discard;
        float t = (vX - (${WMIN.toFixed(3)})) / ${WLEN.toFixed(3)};
        float front = 1.0 - smoothstep(0.0, 0.22, behind);
        float trail = 1.0 - smoothstep(0.22, 1.1, behind);
        float alpha = 0.05 + 0.5 * front + 0.07 * trail;
        vec3 c = mix(thermalLinear(t), vec3(1.0), front * 0.35);
        gl_FragColor = vec4(c, alpha);
        #include <colorspace_fragment>
      }`,
  });
}

function metal(color: string, roughness: number, metalness = 1, extra: Partial<THREE.MeshPhysicalMaterialParameters> = {}) {
  return new THREE.MeshPhysicalMaterial({ color, roughness, metalness, envMapIntensity: 1, clearcoat: 0, ...extra });
}

/** Satin metal with a narrow thermal Fresnel rim (gradient by view-space normal angle). */
function makeHighlight(clip: THREE.Plane) {
  const m = metal("#e2e5e8", 0.24, 1, { clippingPlanes: [clip], envMapIntensity: 1.25 });
  const uniforms = { uRim: { value: 0.9 }, ...thermalUniforms() };
  m.userData.uniforms = uniforms;
  m.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\nuniform float uRim;\n${THERMAL_GLSL}`)
      .replace(
        "#include <opaque_fragment>",
        `{
          vec3 nn = normalize(normal);
          float rim = pow(1.0 - clamp(dot(nn, normalize(vViewPosition)), 0.0, 1.0), 3.2);
          float t = atan(nn.y, nn.x) / 6.2831853 + 0.5;
          outgoingLight += thermalLinear(t) * rim * uRim;
        }
        #include <opaque_fragment>`,
      );
  };
  m.customProgramCacheKey = () => "rs-thermal-rim-v1";
  return m;
}

interface Prepared {
  root: THREE.Group;
  scanRoot: THREE.Group;
  meshes: THREE.Mesh[];
  groups: Map<string, { node: THREE.Object3D; home: THREE.Vector3 }>;
  compNodes: Map<string, THREE.Object3D[]>;
  compHome: Map<string, THREE.Vector3[]>;
  byStable: Map<string, THREE.Object3D>;
  nodeHome: Map<string, THREE.Vector3>;
  mats: Record<string, THREE.MeshPhysicalMaterial>;
  casingPlanes: { scan: THREE.Plane[]; cut: THREE.Plane[] };
  highlight: THREE.MeshPhysicalMaterial;
  hover: THREE.MeshPhysicalMaterial;
  context: THREE.MeshStandardMaterial;
  scanMat: THREE.ShaderMaterial;
  clip: THREE.Plane;
}

function groupOf(obj: THREE.Object3D): string {
  let cur: THREE.Object3D | null = obj;
  while (cur) {
    if (cur.userData?.assemblyId) return cur.userData.assemblyId as string;
    cur = cur.parent;
  }
  return "casing";
}
function componentOf(obj: THREE.Object3D): string | null {
  let cur: THREE.Object3D | null = obj;
  while (cur) {
    if (cur.userData?.componentId) return cur.userData.componentId as string;
    cur = cur.parent;
  }
  return null;
}

function boundsOf(nodes: THREE.Object3D[]) {
  const box = new THREE.Box3();
  nodes.forEach((n) => box.expandByObject(n));
  return box;
}

function usePrepared(url: string, components: PackageComponent[]): Prepared {
  const gltf = useGLTF(url);
  return useMemo(() => {
    const root = gltf.scene.clone(true) as THREE.Group;
    root.position.x = -CENTER_X;
    const clip = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 99);
    // Cutaway (explore): clip only where z > 0 AND x > LIP_X (clipIntersection).
    const cutZ = new THREE.Plane(new THREE.Vector3(0, 0, -1), -0.02);
    const cutX = new THREE.Plane(new THREE.Vector3(-1, 0, 0), LIP_X);
    const casingPlanes = { scan: [clip], cut: [cutZ, cutX] };
    const common = { clippingPlanes: [clip] };
    const shell = { clippingPlanes: casingPlanes.cut, clipIntersection: true, side: THREE.DoubleSide };
    const mats = {
      fan: metal("#b9bec3", 0.34, 1, common),
      compressor: metal("#a7adb2", 0.39, 1, common),
      combustor: metal("#938a7e", 0.46, 1, common),
      turbine: metal("#a49787", 0.42, 1, common),
      nozzle: metal("#858a90", 0.47, 1, common),
      shaft: metal("#747a80", 0.38, 1, common),
      casing: metal("#aab0b5", 0.4, 0.95, shell),
      casingDetail: metal("#c2c5c8", 0.3, 1, { clippingPlanes: casingPlanes.cut, clipIntersection: true }),
      detail: metal("#c2c5c8", 0.3, 1, common),
    } as Record<string, THREE.MeshPhysicalMaterial>;
    const highlight = makeHighlight(clip);
    // An x-ray preview makes rear blades visible through the inlet without moving the camera.
    const hover = metal("#63d4ee", 0.32, 0.55, { emissive: "#14728a", emissiveIntensity: 0.45,
      transparent: true, opacity: 0.86, depthTest: false, depthWrite: false });
    const context = new THREE.MeshStandardMaterial({ color: "#33363a", metalness: 0.35, roughness: 0.78, envMapIntensity: 0.25 });
    const scanMat = makeScanMaterial();
    const meshes: THREE.Mesh[] = [];
    const groups = new Map<string, { node: THREE.Object3D; home: THREE.Vector3 }>();
    const compNodes = new Map<string, THREE.Object3D[]>();
    const byStable = new Map<string, THREE.Object3D>();
    const nodeHome = new Map<string, THREE.Vector3>();
    root.traverse((o) => {
      if (o.userData?.stableId) { byStable.set(o.userData.stableId, o); nodeHome.set(o.userData.stableId, o.position.clone()); }
      if (o.userData?.assemblyId && String(o.userData?.stableId ?? "").includes(".group.")) groups.set(o.userData.assemblyId, { node: o, home: o.position.clone() });
      const mesh = o as THREE.Mesh;
      if (mesh.isMesh) {
        const g = groupOf(mesh);
        const isDetail = /fastener|bolt|ring/i.test(String(mesh.userData?.displayName ?? ""));
        const base = g === "casing" ? (isDetail ? mats.casingDetail : mats.casing) : isDetail ? mats.detail : (mats[g] ?? mats.casing);
        mesh.userData.baseMat = base;
        mesh.material = base;
        mesh.userData.group = g;
        mesh.userData.comp = componentOf(mesh);
        meshes.push(mesh);
      }
    });
    const compHome = new Map<string, THREE.Vector3[]>();
    for (const c of components) {
      const nodes = c.nodeIds.map((id) => byStable.get(id)).filter(Boolean) as THREE.Object3D[];
      compNodes.set(c.componentId, nodes);
      compHome.set(c.componentId, nodes.map((n) => n.position.clone()));
      nodes.forEach((n) => n.traverse((m) => ((m as THREE.Mesh).isMesh ? (m.userData.comp = c.componentId) : null)));
    }
    const scanRoot = root.clone(true) as THREE.Group;
    scanRoot.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) {
        (o as THREE.Mesh).material = scanMat;
        o.raycast = () => {};
      }
    });
    return { root, scanRoot, meshes, groups, compNodes, compHome, byStable, nodeHome, mats, casingPlanes, highlight, hover, context, scanMat, clip };
  }, [gltf, components]);
}

function inspectionNodes(p: Prepared, inspection: AssemblyItem | null | undefined, selected: string | null): THREE.Object3D[] {
  return inspection ? inspection.nodeIds.flatMap(id => { const node = p.byStable.get(id); return node ? [node] : []; }) : (p.compNodes.get(selected ?? "") ?? []);
}

function meshSet(nodes: THREE.Object3D[]): Set<THREE.Object3D> {
  const result = new Set<THREE.Object3D>();
  nodes.forEach(n => n.traverse(child => { if ((child as THREE.Mesh).isMesh) result.add(child); }));
  return result;
}

function Engine(props: EngineCanvasProps & { prepared: Prepared }) {
  const { prepared: p, mode, scan, solid, selected, inspection, hovered, exploded, isolate, phase, onSelect, onInspect } = props;
  const { gl } = useThree();
  useLayoutEffect(() => {
    gl.localClippingEnabled = true;
  }, [gl]);
  const explodeT = useRef(0);
  const phaseT = useRef(0);
  const scanVal = useRef(WMIN);
  const solidVal = useRef(WMIN - 1);

  // Casing: whole while scanning/solidifying; intake-preserving cutaway when exploring.
  useEffect(() => {
    const scanning = mode === "scan";
    for (const m of [p.mats.casing, p.mats.casingDetail]) {
      m.clippingPlanes = scanning ? p.casingPlanes.scan : p.casingPlanes.cut;
      m.clipIntersection = !scanning;
      m.needsUpdate = true;
    }
  }, [p, mode]);

  // Selection: metal + thermal rim; isolate keeps nearby context opaque and hides the rest.
  useEffect(() => {
    const keep = inspection ? [inspection.assemblyId] : selected ? (CONTEXT[selected] ?? []) : [];
    const chosen = meshSet(inspectionNodes(p, inspection, selected));
    const preview = hovered ? meshSet(inspectionNodes(p, hovered, null)) : new Set();
    for (const m of p.meshes) {
      const isSel = chosen.has(m);
      m.visible = true;
      m.renderOrder = preview.has(m) ? 10 : 0;
      if (preview.has(m)) m.material = p.hover;
      else if (isSel) m.material = p.highlight;
      else if (isolate && (inspection || selected)) {
        // Context keeps nearby internals but drops enclosing shells that would hide the part.
        if (keep.includes(m.userData.group) && !/housing/i.test(String(m.userData.displayName ?? ""))) m.material = p.context;
        else m.visible = false;
      } else m.material = m.userData.baseMat;
    }
  }, [p, selected, inspection, hovered, isolate]);

  useFrame((state, dt) => {
    // Scan + solid sweep along world X.
    const targetScan = WMIN + (WLEN + 0.6) * scan;
    scanVal.current = THREE.MathUtils.damp(scanVal.current, targetScan, 3.2, dt);
    const targetSolid = solid <= 0 ? WMIN - 1 : WMIN + (WLEN + 0.8) * solid;
    solidVal.current = THREE.MathUtils.damp(solidVal.current, targetSolid, 3.6, dt);
    p.scanMat.uniforms.uReveal.value = scanVal.current;
    p.scanMat.uniforms.uSolid.value = solidVal.current;
    p.clip.constant = mode === "scan" ? solidVal.current : 99;
    p.scanRoot.visible = mode === "scan" && solid < 0.999;

    explodeT.current = THREE.MathUtils.damp(explodeT.current, exploded ? 1 : 0, 4, dt);
    const e = explodeT.current;
    for (const [gid, { node, home }] of p.groups) {
      const off = EXPLODE[gid] ?? [0, 0, 0];
      node.position.set(home.x + off[0] * e, home.y + off[1] * e, home.z + off[2] * e);
    }

    // Removal / insertion choreography for the selected part.
    if (selected) {
      const nodes = inspectionNodes(p, inspection, selected);
      const target = phase === "remove" ? 1 : 0;
      phaseT.current = THREE.MathUtils.damp(phaseT.current, target, phase === "insert" ? 2.2 : 2.6, dt);
      const box = boundsOf(nodes);
      const c = box.getCenter(new THREE.Vector3());
      const radial = new THREE.Vector3(0, c.y, c.z);
      if (radial.lengthSq() < 0.01) radial.set(0, 1, 0);
      radial.normalize().multiplyScalar(2.6);
      radial.x += selected.includes("NOZZLE") ? 2.4 : -0.4;
      nodes.forEach((n) => {
        const h = p.nodeHome.get(n.userData.stableId);
        if (h) n.position.set(h.x + radial.x * phaseT.current, h.y + radial.y * phaseT.current, h.z + radial.z * phaseT.current);
      });
      // Rim brightens briefly while the replacement seats, then settles (no breathing glow).
      const u = p.highlight.userData.uniforms as { uRim: { value: number } };
      u.uRim.value = THREE.MathUtils.damp(u.uRim.value, phase === "insert" ? 1.5 : 0.9, 3, dt);
    }
    void state;
  });

  return (
    <>
      <primitive object={p.scanRoot} />
      <primitive
        object={p.root}
        onPointerDown={(ev: { stopPropagation: () => void; object: THREE.Object3D }) => {
          if (mode !== "explore" || !ev.object.visible) return;
          ev.stopPropagation();
          const stable = ev.object.userData.attachedToStableId ?? ev.object.userData.stableId;
          if (stable && onInspect) { onInspect(stable); return; }
          const comp = componentOf(ev.object) ?? (ev.object.userData?.comp as string | null);
          if (comp) onSelect?.(comp);
        }}
        onPointerOver={(ev: { object: THREE.Object3D }) => {
          if (mode === "explore" && ev.object.visible && ev.object.userData?.stableId) document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => (document.body.style.cursor = "")}
      />
    </>
  );
}

/** drei's default ignores camera.view offsets; project through the real projection matrix. */
const _v = new THREE.Vector3();
function projectWithViewOffset(el: THREE.Object3D, camera: THREE.Camera, size: { width: number; height: number }): number[] {
  el.getWorldPosition(_v).project(camera);
  return [(_v.x * 0.5 + 0.5) * size.width, (-_v.y * 0.5 + 0.5) * size.height];
}

function SelectedCallout({ prepared, nodes, name, id, rightInset = 0, leftInset = 0 }: { prepared: Prepared; nodes: THREE.Object3D[]; name: string; id: string; rightInset?: number; leftInset?: number }) {
  const anchor = useRef<THREE.Group>(null);
  const callout = useRef<HTMLDivElement>(null);
  const frame = useRef(0);
  const bounds = useMemo(() => new THREE.Box3(), []);
  const layout = useRef("");
  const updateAnchor = () => {
    if (!anchor.current) return;
    prepared.root.updateMatrixWorld(true);
    bounds.makeEmpty();
    nodes.forEach(node => bounds.expandByObject(node));
    if (!bounds.isEmpty()) bounds.getCenter(anchor.current.position);
  };
  useLayoutEffect(updateAnchor, [prepared, nodes]);
  useFrame(() => {
    if (frame.current++ % 6 === 0) updateAnchor(); // follow assembly motion without traversing every mesh each frame
  });
  const position = (el: THREE.Object3D, camera: THREE.Camera, size: { width: number; height: number }) => {
    const point = projectWithViewOffset(el, camera, size);
    const narrow = size.width < 700;
    const left = point[0] - (narrow ? 0 : leftInset) - 16;
    const right = size.width - (narrow ? 0 : rightInset) - point[0] - 16;
    const side = left > right ? "left" : "right";
    const width = Math.round(Math.max(80, Math.min(230, Math.max(left, right) - 64)));
    const key = `${side}:${width}`;
    if (callout.current && key !== layout.current) {
      callout.current.dataset.side = side;
      callout.current.style.setProperty("--rs-callout-width", `${width}px`);
      layout.current = key;
    }
    return point;
  };
  return (
    <group ref={anchor}>
      <Html zIndexRange={[20, 10]} style={{ pointerEvents: "none" }} calculatePosition={position}>
        <div ref={callout} className="rs-part-callout" role="note" aria-label={`Selected part: ${name}`} data-part-id={id}>
          <span className="rs-part-callout-dot" aria-hidden="true" />
          <svg className="rs-part-callout-leader" width="64" height="40" viewBox="0 0 64 40" aria-hidden="true">
            <path d="M0 40 L28 4 H64" />
          </svg>
          <span className="rs-part-callout-label">{name}</span>
        </div>
      </Html>
    </group>
  );
}

function Rig({ prepared, selected, inspection, mode, resetKey, rightInset = 0, leftInset = 0, turntable, wide }: { prepared: Prepared; selected: string | null; inspection?: AssemblyItem | null; mode: SceneMode; resetKey: number; rightInset?: number; leftInset?: number; turntable: boolean; wide: boolean }) {
  const ref = useRef<CameraControls>(null);
  const { size, camera } = useThree();
  const cam = camera as THREE.PerspectiveCamera;
  useEffect(() => {
    if (import.meta.env.DEV) (window as unknown as { __rsScene: unknown }).__rsScene = { camera, controls: ref.current, prepared };
  }, [camera, prepared]);
  // Offset the projection so the subject centres in the space left of side panels.
  const narrow = size.width < 700;
  const inset = narrow ? 0 : rightInset + leftInset;
  const offsetX = narrow ? 0 : (rightInset - leftInset) / 2;
  useEffect(() => {
    if (offsetX !== 0) cam.setViewOffset(size.width, size.height, offsetX, 0, size.width, size.height);
    else cam.clearViewOffset();
    cam.updateProjectionMatrix();
  }, [cam, offsetX, size.width, size.height]);

  useEffect(() => {
    const cc = ref.current;
    if (!cc) return;
    const v = THREE.MathUtils.degToRad(cam.fov / 2);
    const usableAspect = (size.width - inset) / size.height;
    const h = Math.atan(Math.tan(v) * usableAspect);
    const fit = (center: THREE.Vector3, radius: number, k: number, dir = VIEW_DIR) => {
      const dist = (radius / Math.sin(Math.min(v, h))) * k;
      const eye = center.clone().addScaledVector(dir, dist);
      void cc.setLookAt(eye.x, eye.y, eye.z, center.x, center.y, center.z, true);
    };
    if ((selected || inspection) && mode === "explore" && !wide) {
      prepared.root.updateMatrixWorld(true);
      const sphere = boundsOf(inspectionNodes(prepared, inspection, selected)).getBoundingSphere(new THREE.Sphere());
      // Each part is framed from a view that shows its form, with nearby context.
      const f = FOCUS[selected ?? ""] ?? { dir: VIEW_DIR, k: 1.6, minR: 0.6 };
      const c = sphere.center.clone();
      if (f.axis != null) c.set(c.x, c.y * f.axis, c.z * f.axis); // pull toward the engine axis for disc context
      fit(c, Math.max(sphere.radius, f.minR), f.k, f.dir);
    } else {
      // Whole assembly fills ~85% of the unobstructed width (long axis dominates).
      const halfLen = WLEN / 2;
      const dist = (halfLen / Math.tan(h)) * 1.18 + 2.2;
      const center = new THREE.Vector3(wide && selected ? -0.6 : 0.15, -0.05, 0);
      const eye = center.clone().addScaledVector(VIEW_DIR, narrow ? dist * 1.15 : dist);
      void cc.setLookAt(eye.x, eye.y, eye.z, center.x, center.y, center.z, true);
    }
  }, [selected, inspection, mode, resetKey, prepared, size.width, size.height, inset, wide, cam, narrow]); // eslint-disable-line react-hooks/exhaustive-deps
  useFrame((_, dt) => {
    if (turntable && mode === "explore" && ref.current) ref.current.azimuthAngle += dt * 0.18;
  });
  return <CameraControls ref={ref} makeDefault minDistance={1.5} maxDistance={30} smoothTime={0.35} draggingSmoothTime={0.12} enabled={mode === "explore"} />;
}

function SceneContents(props: EngineCanvasProps) {
  const prepared = usePrepared(props.url, props.components);
  const nodes = useMemo(() => inspectionNodes(prepared, props.inspection, props.selected), [prepared, props.inspection, props.selected]);
  const component = props.components.find(c => c.componentId === props.selected);
  const label = props.inspection?.children.length ? (component?.name ?? props.inspection.name) : (props.inspection?.name ?? component?.name);
  const { onReady } = props;
  useEffect(() => {
    const id = setTimeout(() => onReady?.(), 0);
    return () => clearTimeout(id);
  }, [prepared, onReady]);
  return (
    <>
      <Engine {...props} prepared={prepared} />
      {props.showHotspots && props.mode === "explore" && props.phase === "idle" && label && nodes.length > 0 ? (
        <SelectedCallout key={props.inspection?.id ?? props.selected} prepared={prepared} nodes={nodes} name={label} id={props.inspection?.id ?? props.selected!} rightInset={props.rightInset} leftInset={props.leftInset} />
      ) : null}
      <Rig prepared={prepared} selected={props.selected} inspection={props.inspection} mode={props.mode} resetKey={props.resetKey} rightInset={props.rightInset} leftInset={props.leftInset} turntable={props.spin && props.phase === "idle"} wide={!!props.wide} />
    </>
  );
}

const lookAtOrigin = (o: THREE.Object3D) => o.lookAt(0, 0, 0);

export function EngineCanvas(props: EngineCanvasProps) {
  return (
    <Canvas
      className="rs-engine-canvas"
      dpr={[1, 1.75]}
      frameloop={props.mode === "hidden" ? "never" : "always"}
      camera={{ position: [-8, 3.2, 14.5], fov: 30, near: 0.05, far: 100 }}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      onCreated={({ gl }) => {
        gl.toneMapping = THREE.AgXToneMapping;
        gl.toneMappingExposure = 1.12;
        gl.outputColorSpace = THREE.SRGBColorSpace;
        gl.localClippingEnabled = true;
      }}
      onPointerMissed={() => props.mode === "explore" && props.phase === "idle" && props.onSelect?.(null)}
    >
      <Suspense fallback={null}>
        <Environment resolution={512} frames={1}>
          <Lightformer position={[0, 6, 2]} scale={[11, 4, 1]} color="#fff5e9" intensity={3} onUpdate={lookAtOrigin} />
          <Lightformer position={[-2, 2, 6]} scale={[8, 1.2, 1]} color="#ffffff" intensity={1.8} onUpdate={lookAtOrigin} />
          <Lightformer position={[2, 3, -5]} scale={[9, 0.7, 1]} color="#eef2f5" intensity={2.2} onUpdate={lookAtOrigin} />
          <Lightformer position={[-6, 0, 1]} scale={[3, 3, 1]} color="#ffffff" intensity={0.65} onUpdate={lookAtOrigin} />
        </Environment>
        <SceneContents {...props} />
      </Suspense>
    </Canvas>
  );
}
