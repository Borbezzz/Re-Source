// Geographic marks come from supplier findings. Motion never creates research activity.
import {
  Component,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Billboard, Html, Line, OrbitControls } from "@react-three/drei";
import { geoContains } from "d3-geo";
import { feature } from "topojson-client";
import land from "world-atlas/land-110m.json";
import type { Topology, GeometryCollection } from "topojson-specification";
import * as THREE from "three";
import { ArrowLeft, ArrowRight, Pause, Play } from "lucide-react";
import { knownLocation, type Finding } from "./findings.ts";
import "./research-globe.css";

const earth = feature(land as unknown as Topology, {
  ...(land.objects.land as GeometryCollection),
});
const position = (lat: number, lng: number, r = 1) =>
  new THREE.Vector3(
    Math.cos((lat * Math.PI) / 180) * Math.sin((lng * Math.PI) / 180) * r,
    Math.sin((lat * Math.PI) / 180) * r,
    Math.cos((lat * Math.PI) / 180) * Math.cos((lng * Math.PI) / 180) * r,
  );
const hub = new THREE.Vector3(-1.25, 0.75, 0.5);
const rotationSpeed = Math.PI / 90; // Two degrees per second, independent of frame rate.
const glowVertex = `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const glowFragment = `varying vec2 vUv; uniform vec3 color; uniform float strength; void main() { float radius = length(vUv - 0.5) * 2.0; float glow = exp(-4.5 * radius * radius) * (1.0 - smoothstep(0.65, 1.0, radius)); gl_FragColor = vec4(color, glow * strength); }`;

class GlobeBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="globe-fallback">
        The globe could not load. All supplier findings remain in the list.
      </div>
    ) : (
      this.props.children
    );
  }
}

function LandDots({ immersive }: { immersive: boolean }) {
  const positions = useMemo(() => {
    const points: number[] = [];
    const count = 16000;
    for (let i = 0; i < count; i++) {
      const y = 1 - (2 * (i + 0.5)) / count;
      const lat = (Math.asin(y) * 180) / Math.PI;
      const lng = ((i * 137.507764) % 360) - 180;
      if (geoContains(earth, [lng, lat]))
        points.push(...position(lat, lng, 1.006).toArray());
    }
    return new Float32Array(points);
  }, []);
  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color={immersive ? "#b3c3da" : "#bac8e1"}
        size={immersive ? 0.009 : 0.012}
        sizeAttenuation
        transparent={immersive}
        opacity={immersive ? 0.64 : 1}
        depthWrite={!immersive}
      />
    </points>
  );
}

function GlobeCamera({
  immersive,
  onInteract,
}: {
  immersive: boolean;
  onInteract: () => void;
}) {
  const { camera, size, invalidate } = useThree();
  useEffect(() => {
    const aspect = size.width / Math.max(size.height, 1);
    if (immersive) {
      const factor = Math.max(1, 1 / aspect);
      camera.position.set(0.15 * factor, 1.0 * factor, 3.45 * factor);
    } else {
      const factor = Math.max(1, 1.3 / aspect);
      camera.position.set(0.3 * factor, 1.8 * factor, 3.5 * factor);
    }
    camera.lookAt(0, 0, 0);
    invalidate();
  }, [camera, size, immersive, invalidate]);
  return (
    <OrbitControls
      enableZoom={false}
      enablePan={false}
      enableDamping={false}
      onStart={onInteract}
    />
  );
}

function FindingArc({
  finding,
  selected,
  onSelect,
}: {
  finding: Finding;
  selected: boolean;
  onSelect: () => void;
}) {
  const point = useMemo(
    () =>
      position(finding.location.latitude!, finding.location.longitude!, 1.025),
    [finding.location.latitude, finding.location.longitude],
  );
  const arc = useMemo(
    () =>
      new THREE.QuadraticBezierCurve3(
        hub,
        hub.clone().add(point).normalize().multiplyScalar(1.8),
        point,
      ).getPoints(36),
    [point],
  );
  return (
    <group>
      <Line
        points={arc}
        color={selected ? "#ffffff" : "#628dff"}
        lineWidth={selected ? 1.7 : 0.6}
        transparent
        opacity={selected ? 1 : 0.22}
      />
      <mesh
        position={point}
        onClick={(event) => {
          event.stopPropagation();
          onSelect();
        }}
      >
        <sphereGeometry args={[selected ? 0.028 : 0.017, 16, 12]} />
        <meshBasicMaterial color={selected ? "#ffffff" : "#6e98ff"} />
      </mesh>
    </group>
  );
}

function SourceMarker({
  finding,
  selected,
  onSelect,
}: {
  finding: Finding;
  selected: boolean;
  onSelect: () => void;
}) {
  const marker = useRef<THREE.Group>(null);
  const core = useRef<THREE.MeshBasicMaterial>(null);
  const worldPoint = useMemo(() => new THREE.Vector3(), []);
  const cameraDirection = useMemo(() => new THREE.Vector3(), []);
  const point = useMemo(
    () =>
      position(finding.location.latitude!, finding.location.longitude!, 1.018),
    [finding.location.latitude, finding.location.longitude],
  );
  const uniforms = useMemo(
    () => ({
      color: { value: new THREE.Color(selected ? "#f2f6ff" : "#9cbaff") },
      strength: { value: selected ? 0.95 : 0.7 },
    }),
    [selected],
  );
  useFrame(({ camera }) => {
    if (!marker.current) return;
    marker.current.getWorldPosition(worldPoint);
    camera.getWorldPosition(cameraDirection);
    // Far-side points remain faintly visible through the translucent surface.
    const facing = worldPoint.normalize().dot(cameraDirection.normalize());
    const visibility = THREE.MathUtils.smoothstep(facing, -0.2, 0.2);
    uniforms.strength.value =
      (selected ? 0.95 : 0.7) * (0.16 + 0.84 * visibility);
    if (core.current) core.current.opacity = 0.22 + 0.78 * visibility;
  });
  return (
    <group ref={marker} position={point}>
      <Billboard>
        <mesh renderOrder={2}>
          <planeGeometry
            args={[selected ? 0.19 : 0.14, selected ? 0.19 : 0.14]}
          />
          <shaderMaterial
            vertexShader={glowVertex}
            fragmentShader={glowFragment}
            uniforms={uniforms}
            transparent
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      </Billboard>
      <mesh renderOrder={3}>
        <sphereGeometry args={[selected ? 0.025 : 0.017, 16, 12]} />
        <meshBasicMaterial
          ref={core}
          color={selected ? "#ffffff" : "#c2d4ff"}
          transparent
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>
      <mesh
        onClick={(event) => {
          event.stopPropagation();
          onSelect();
        }}
      >
        <sphereGeometry args={[0.048, 12, 8]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>
    </group>
  );
}

function GlobeContents({
  sites,
  selected,
  onSelect,
  immersive,
  spinning,
  rotation,
  reset,
}: {
  sites: Finding[];
  selected: string | null;
  onSelect: (id: string) => void;
  immersive: boolean;
  spinning: boolean;
  rotation: number;
  reset: number;
}) {
  const globe = useRef<THREE.Group>(null);
  const previousRotation = useRef(rotation);
  const { invalidate } = useThree();
  useEffect(() => {
    if (globe.current)
      globe.current.rotation.y += rotation - previousRotation.current;
    previousRotation.current = rotation;
    invalidate();
  }, [rotation, invalidate]);
  useEffect(() => {
    if (globe.current) globe.current.rotation.y = 0;
    invalidate();
  }, [reset, invalidate]);
  useEffect(() => {
    invalidate();
  }, [spinning, invalidate]);
  useFrame((_, delta) => {
    if (!spinning || !globe.current) return;
    globe.current.rotation.y += Math.min(delta, 0.05) * rotationSpeed;
    invalidate();
  });
  return (
    <group ref={globe}>
      <mesh>
        <sphereGeometry args={[1, 64, 40]} />
        <meshBasicMaterial
          color={immersive ? "#132034" : "#192331"}
          transparent={immersive}
          opacity={immersive ? 0.58 : 1}
          depthWrite={!immersive}
        />
      </mesh>
      <LandDots immersive={immersive} />
      {sites.map((finding) =>
        immersive ? (
          <SourceMarker
            key={finding.location.site_id}
            finding={finding}
            selected={selected === finding.event_id}
            onSelect={() => onSelect(finding.event_id)}
          />
        ) : (
          <FindingArc
            key={finding.location.site_id}
            finding={finding}
            selected={selected === finding.event_id}
            onSelect={() => onSelect(finding.event_id)}
          />
        ),
      )}
      {!immersive ? (
        <>
          <mesh position={hub}>
            <octahedronGeometry args={[0.035]} />
            <meshBasicMaterial color="#91b1ff" />
          </mesh>
          <Html
            position={hub}
            center
            style={{
              color: "#dce5f8",
              fontSize: 11,
              whiteSpace: "nowrap",
              pointerEvents: "none",
              transform: "translateY(-20px)",
            }}
          >
            Investigation
          </Html>
        </>
      ) : null}
    </group>
  );
}

export default function ResearchGlobe({
  findings,
  selected,
  onSelect,
  locationLabel = "sourced locations",
  locationNote,
  variant = "panel",
  autoRotate = false,
}: {
  locationLabel?: string;
  locationNote?: string;
  findings: Finding[];
  selected: string | null;
  onSelect: (id: string) => void;
  variant?: "panel" | "immersive";
  autoRotate?: boolean;
}) {
  const immersive = variant === "immersive";
  const container = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const [rotation, setRotation] = useState(0);
  const [reset, setReset] = useState(0);
  const [paused, setPaused] = useState(!autoRotate);
  const [inView, setInView] = useState(false);
  const [documentVisible, setDocumentVisible] = useState(
    () => !document.hidden,
  );
  const [reduced, setReduced] = useState(
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    setPaused(!autoRotate);
  }, [autoRotate]);
  useEffect(() => {
    const query = matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(query.matches);
    query.addEventListener("change", update);
    const visibility = () => setDocumentVisible(!document.hidden);
    document.addEventListener("visibilitychange", visibility);
    return () => {
      query.removeEventListener("change", update);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);
  useEffect(() => {
    if (!container.current) return;
    if (!window.IntersectionObserver) {
      setInView(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => setInView(entries.some((entry) => entry.isIntersecting)),
      { threshold: 0 },
    );
    observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  const spinning = !paused && !reduced && inView && documentVisible;
  const sites = useMemo(() => {
    const unique = new Map<string, Finding>();
    for (const finding of findings.filter(knownLocation)) {
      const key = finding.location.site_id;
      if (!unique.has(key) || finding.event_id === selected)
        unique.set(key, finding);
    }
    return [...unique.values()];
  }, [findings, selected]);
  const pause = () => setPaused(true);
  const nudge = (delta: number) => {
    pause();
    setRotation((value) => value + delta);
  };
  return (
    <div
      ref={container}
      className={`research-globe${immersive ? " research-globe-immersive" : ""}`}
      data-ready={ready}
      data-auto-rotating={spinning}
    >
      <div className="globe-heading">
        <h2>{immersive ? "Supplier locations" : "Research connections"}</h2>
        <span>
          {sites.length} {locationLabel}
        </span>
      </div>
      <div
        className="globe-canvas"
        aria-label="Interactive globe of reported supplier locations"
      >
        <GlobeBoundary>
          <Canvas
            frameloop="demand"
            dpr={[1, 1.5]}
            camera={{ position: [0.3, 1.8, 3.5], fov: immersive ? 36 : 40 }}
            gl={{ alpha: true, antialias: true }}
            onCreated={() => setReady(true)}
          >
            <GlobeContents
              sites={sites}
              selected={selected}
              onSelect={onSelect}
              immersive={immersive}
              spinning={spinning}
              rotation={rotation}
              reset={reset}
            />
            <GlobeCamera key={reset} immersive={immersive} onInteract={pause} />
          </Canvas>
        </GlobeBoundary>
      </div>
      <div className="globe-controls">
        <span>
          {reduced && immersive
            ? "Reduced motion · drag to rotate"
            : spinning
              ? "Rotating slowly"
              : "Drag to rotate"}
        </span>
        {immersive || autoRotate ? (
          <button
            className="globe-motion-toggle"
            aria-label={
              paused ? "Resume globe rotation" : "Pause globe rotation"
            }
            onClick={() => setPaused((value) => !value)}
            disabled={reduced}
            title={
              reduced
                ? "Automatic rotation is disabled by your reduced-motion preference."
                : undefined
            }
          >
            {paused || reduced ? <Play size={14} /> : <Pause size={14} />}
            <span>{paused || reduced ? "Resume" : "Pause"}</span>
          </button>
        ) : null}
        <button aria-label="Rotate globe left" onClick={() => nudge(-0.4)}>
          <ArrowLeft size={16} />
        </button>
        <button
          aria-label="Reset globe rotation"
          onClick={() => {
            pause();
            setRotation(0);
            setReset((value) => value + 1);
          }}
        >
          Reset
        </button>
        <button aria-label="Rotate globe right" onClick={() => nudge(0.4)}>
          <ArrowRight size={16} />
        </button>
      </div>
      <p>
        {locationNote ??
          (immersive
            ? "Markers show sourced or explicitly labelled sample locations. Unknown locations remain in the supplier list."
            : "Lines link discovered locations to this investigation, not transport routes. Fixture locations are representative; unknown locations stay in the list.")}
      </p>
    </div>
  );
}
