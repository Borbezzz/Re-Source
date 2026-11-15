import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Lightformer, useGLTF } from "@react-three/drei";
import { Suspense, useMemo, useRef } from "react";
import * as THREE from "three";

/**
 * Renders the *actual* selected component from the package GLB (same asset,
 * same identity) as a compact anchor thumbnail — never a generated image.
 */
function Part({ url, nodeIds }: { url: string; nodeIds: string[] }) {
  const gltf = useGLTF(url);
  const ref = useRef<THREE.Group>(null);
  const group = useMemo(() => {
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
    gltf.scene.traverse((o) => {
      if (!nodeIds.includes(o.userData?.stableId)) return;
      o.traverse((m) => {
        const mesh = m as THREE.Mesh;
        if (!mesh.isMesh) return;
        const copy = new THREE.Mesh(mesh.geometry, mat);
        copy.applyMatrix4(mesh.matrixWorld);
        g.add(copy);
      });
    });
    const box = new THREE.Box3().setFromObject(g);
    const c = box.getCenter(new THREE.Vector3());
    const s = 1.7 / Math.max(...box.getSize(new THREE.Vector3()).toArray(), 0.001);
    g.children.forEach((ch) => ch.position.sub(c));
    const wrap = new THREE.Group();
    wrap.add(g);
    wrap.scale.setScalar(s);
    return wrap;
  }, [gltf, nodeIds]);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.5;
  });
  return (
    <group ref={ref} rotation={[0.35, 0.6, 0]}>
      <primitive object={group} />
    </group>
  );
}

export function ComponentThumb({ url, nodeIds, label }: { url: string; nodeIds: string[]; label: string }) {
  return (
    <div className="rs-thumb" role="img" aria-label={`${label} — rendered from the package model`}>
      <Canvas dpr={[1, 2]} camera={{ position: [0, 0, 3.2], fov: 32 }} gl={{ alpha: true, antialias: true }}>
        <Suspense fallback={null}>
          <Environment resolution={64} frames={1}>
            <Lightformer intensity={2.2} position={[0, 4, 3]} scale={[8, 2, 1]} />
            <Lightformer intensity={1} position={[-4, 0, 2]} scale={[2, 6, 1]} color="#bae6fd" />
            <Lightformer intensity={1} position={[4, 0, -2]} scale={[2, 6, 1]} color="#fed7aa" />
          </Environment>
          <ambientLight intensity={0.6} />
          <directionalLight position={[2, 3, 4]} intensity={1.6} />
          <directionalLight position={[-3, -1, -2]} intensity={0.6} color="#c4b5fd" />
          <Part url={url} nodeIds={nodeIds} />
        </Suspense>
      </Canvas>
    </div>
  );
}
