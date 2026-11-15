import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Environment, Lightformer, useGLTF } from "@react-three/drei";
import { memo, Suspense, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { AssemblyInstances } from "./instances.ts";

// Card layout animations scale the DOM, not the thumbnail's actual drawing-buffer dimensions.
const THUMB_RESIZE = { offsetSize: true };

/**
 * Renders the *actual* selected component from the package GLB (same asset,
 * same identity) as a compact anchor thumbnail — never a generated image.
 */
function Part({ url, nodeIds, spin }: { url: string; nodeIds: string[]; spin: boolean }) {
  const gltf = useGLTF(url);
  const ref = useRef<THREE.Group>(null);
  const prepared = useMemo(() => {
    const g = new THREE.Group();
    gltf.scene.updateMatrixWorld(true);
    const mat = new THREE.MeshPhysicalMaterial({
      color: "#e4e5ea",
      metalness: 0.55,
      roughness: 0.32,
      iridescence: 0.55,
      iridescenceIOR: 1.6,
      iridescenceThicknessMinimum: 200,
      iridescenceThicknessMaximum: 700,
      envMapIntensity: 1.4,
    });
    const ids = new Set(nodeIds);
    const seen = new Set<THREE.Object3D>();
    gltf.scene.traverse((o) => {
      if (!ids.has(o.userData?.stableId)) return;
      o.traverse((m) => {
        const mesh = m as THREE.Mesh;
        if (!mesh.isMesh || seen.has(mesh)) return;
        seen.add(mesh);
        const copy = new THREE.Mesh(mesh.geometry, mat);
        copy.applyMatrix4(mesh.matrixWorld);
        g.add(copy);
      });
    });
    const box = new THREE.Box3().setFromObject(g);
    const c = box.getCenter(new THREE.Vector3());
    const s = 1.7 / Math.max(...box.getSize(new THREE.Vector3()).toArray(), 0.001);
    g.children.forEach((ch) => ch.position.sub(c));
    g.updateMatrixWorld(true);
    const instances = new AssemblyInstances(g.children as THREE.Mesh[]);
    instances.sync();
    const wrap = new THREE.Group();
    wrap.add(instances.root);
    wrap.scale.setScalar(s);
    return { wrap, instances, mat };
  }, [gltf, nodeIds]);
  useEffect(() => () => { prepared.instances.dispose(); prepared.mat.dispose(); }, [prepared]);
  // Rendered on demand: the thumbnail turns only while the pointer is over it.
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => { invalidate(); }, [invalidate, spin, prepared]);
  useFrame((state, dt) => {
    if (!spin || !ref.current) return;
    ref.current.rotation.y += Math.min(dt, 0.05) * 0.5;
    state.invalidate();
  });
  return (
    <group ref={ref} rotation={[0.35, 0.6, 0]}>
      <primitive object={prepared.wrap} />
    </group>
  );
}

const ThumbLighting = memo(function ThumbLighting() {
  return <>
    <Environment resolution={64} frames={1}>
      <Lightformer intensity={2.2} position={[0, 4, 3]} scale={[8, 2, 1]} />
      <Lightformer intensity={1} position={[-4, 0, 2]} scale={[2, 6, 1]} color="#bae6fd" />
      <Lightformer intensity={1} position={[4, 0, -2]} scale={[2, 6, 1]} color="#fed7aa" />
    </Environment>
    <ambientLight intensity={0.6} />
    <directionalLight position={[2, 3, 4]} intensity={1.6} />
    <directionalLight position={[-3, -1, -2]} intensity={0.6} color="#c4b5fd" />
  </>;
});

export const ComponentThumb = memo(function ComponentThumb({ url, nodeIds, label }: { url: string; nodeIds: string[]; label: string }) {
  const [spin, setSpin] = useState(false);
  return (
    <div className="rs-thumb" role="img" aria-label={`${label} — rendered from the package model`} onPointerEnter={() => setSpin(true)} onPointerLeave={() => setSpin(false)}>
      <Canvas resize={THUMB_RESIZE} frameloop="demand" dpr={[1, 1.5]} camera={{ position: [0, 0, 3.2], fov: 32 }} gl={{ alpha: true, antialias: true }}>
        <Suspense fallback={null}>
          <ThumbLighting />
          <Part url={url} nodeIds={nodeIds} spin={spin} />
        </Suspense>
      </Canvas>
    </div>
  );
});
