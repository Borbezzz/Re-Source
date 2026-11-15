// Visual direction and geographic convention adapted from Yixin's supplied globe reference.
// The scene uses local land data and actual supplier discovery events, never timed fake findings.
import { Component, useEffect, useMemo, useState, type ReactNode } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Html, Line, OrbitControls } from "@react-three/drei";
import { geoContains } from "d3-geo";
import { feature } from "topojson-client";
import land from "world-atlas/land-110m.json";
import type { Topology, GeometryCollection } from "topojson-specification";
import * as THREE from "three";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { knownLocation, type Finding } from "./findings.ts";
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
function LandDots() {
  const positions = useMemo(() => {
    const out: number[] = [];
    const count = 16000;
    for (let i = 0; i < count; i++) {
      const y = 1 - (2 * (i + 0.5)) / count,
        lat = (Math.asin(y) * 180) / Math.PI,
        lng = ((i * 137.507764) % 360) - 180;
      if (geoContains(earth, [lng, lat]))
        out.push(...position(lat, lng, 1.006).toArray());
    }
    return new Float32Array(out);
  }, []);
  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color="#bac8e1" size={0.012} sizeAttenuation />
    </points>
  );
}
function GlobeCamera() {
  const { camera, size, invalidate } = useThree();
  useEffect(() => {
    const factor = Math.max(1, 1.3 / (size.width / size.height));
    camera.position.set(0.3 * factor, 1.8 * factor, 3.5 * factor);
    camera.lookAt(0, 0, 0);
    invalidate();
  }, [camera, size, invalidate]);
  return (
    <OrbitControls enableZoom={false} enablePan={false} enableDamping={false} />
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
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
      >
        <sphereGeometry args={[selected ? 0.028 : 0.017, 16, 12]} />
        <meshBasicMaterial color={selected ? "#ffffff" : "#6e98ff"} />
      </mesh>
    </group>
  );
}
export default function ResearchGlobe({
  findings,
  selected,
  onSelect,
  locationLabel = "sourced locations",
  locationNote,
}: {
  locationLabel?: string;
  locationNote?: string;
  findings: Finding[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const [ready, setReady] = useState(false),
    [rotation, setRotation] = useState(0);
  const [reset, setReset] = useState(0);
  const sites = useMemo(() => {
    const unique = new Map<string, Finding>();
    for (const f of findings.filter(knownLocation)) {
      const k = f.location.site_id;
      if (!unique.has(k) || f.event_id === selected) unique.set(k, f);
    }
    return [...unique.values()];
  }, [findings, selected]);
  return (
    <div className="research-globe" data-ready={ready}>
      <div className="globe-heading">
        <h2>Research connections</h2>
        <span>
          {sites.length} {locationLabel}
        </span>
      </div>
      <div className="globe-canvas">
        <GlobeBoundary>
          <Canvas
            frameloop="demand"
            dpr={[1, 1.5]}
            camera={{ position: [0.3, 1.8, 3.5], fov: 40 }}
            onCreated={() => setReady(true)}
          >
            <group rotation={[0, rotation, 0]}>
              <mesh>
                <sphereGeometry args={[1, 64, 40]} />
                <meshBasicMaterial color="#192331" />
              </mesh>
              <LandDots />
              {sites.map((f) => (
                <FindingArc
                  key={f.location.site_id}
                  finding={f}
                  selected={selected === f.event_id}
                  onSelect={() => onSelect(f.event_id)}
                />
              ))}
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
            </group>
            <GlobeCamera key={reset} />
          </Canvas>
        </GlobeBoundary>
      </div>
      <div className="globe-controls">
        <span>Drag to rotate</span>
        <button
          aria-label="Rotate globe left"
          onClick={() => setRotation((r) => r - 0.4)}
        >
          <ArrowLeft size={16} />
        </button>
        <button
          aria-label="Reset globe rotation"
          onClick={() => {
            setRotation(0);
            setReset((n) => n + 1);
          }}
        >
          Reset
        </button>
        <button
          aria-label="Rotate globe right"
          onClick={() => setRotation((r) => r + 0.4)}
        >
          <ArrowRight size={16} />
        </button>
      </div>
      <p>
        {locationNote ??
          "Lines link discovered locations to this investigation, not transport routes. Fixture locations are representative; unknown locations stay in the list."}
      </p>
    </div>
  );
}
