# Astra (gpt-6-astra) 3D art-direction review

The main gap is **reflection control and visual hierarchy**, not more effects. Image 2 reads as chrome; 3–4 as layered X-ray noise; 5 loses the thermal colors to white overdraw. The reference is quieter: broad silver highlights, dark cavities, readable silhouettes.

The code ends inside `Rig`, so the camera/Canvas recommendations below are replacements rather than assumptions about the missing configuration.

### 1. Lock a neutral rendering baseline

Use AgX to retain metallic highlight detail; remove colored environment lighting and full-screen bloom while tuning.

```tsx
<Canvas
  dpr={[1, 1.75]}
  camera={{ fov: 30, near: 0.05, far: 100 }}
  gl={{ antialias: true }}
  onCreated={({ gl }) => {
    gl.toneMapping = THREE.AgXToneMapping;
    gl.toneMappingExposure = 0.95;
    gl.outputColorSpace = THREE.SRGBColorSpace;
    gl.localClippingEnabled = true;
  }}
>
  <color attach="background" args={["#121314"]} />
</Canvas>
```

Keep HTML/UI accents outside tone mapping. **Cheap-looking:** blue ambient fill, crushed-black metal, bloom on every bright edge.

### 2. Replace generic illumination with four neutral studio reflection cards

These dimensions assume your approximately 9-unit-long engine. Broad cards produce readable blade curvature; narrow cards define edges.

```tsx
<Environment frames={1} resolution={512}>
  {/* Top softbox */}
  <Lightformer
    position={[0, 6, 2]} scale={[11, 4, 1]}
    color="#fff5e9" intensity={3}
    onUpdate={o => o.lookAt(0, 0, 0)}
  />
  {/* Camera-side strip */}
  <Lightformer
    position={[-2, 2, 6]} scale={[8, 1.2, 1]}
    color="#ffffff" intensity={1.8}
    onUpdate={o => o.lookAt(0, 0, 0)}
  />
  {/* Rear rim */}
  <Lightformer
    position={[2, 3, -5]} scale={[9, 0.7, 1]}
    color="#eef2f5" intensity={2.2}
    onUpdate={o => o.lookAt(0, 0, 0)}
  />
  {/* Intake fill */}
  <Lightformer
    position={[-6, 0, 1]} scale={[3, 3, 1]}
    color="#ffffff" intensity={0.65}
    onUpdate={o => o.lookAt(0, 0, 0)}
  />
</Environment>
```

Remove the previous HDRI during calibration; don’t stack both. Avoid strong ambient light—it flattens cavities. Reserve cyan/violet lighting for **neither** the environment nor ordinary metal.

### 3. Make the assembly satin metal, not chrome

Start with these exact values; all use `clearcoat: 0`, `envMapIntensity: 1`. Uncoated engineering metal does not need the fan’s current `clearcoat: 0.4`.

| Material | Color | Metalness | Roughness |
|---|---|---:|---:|
| Fan | `#b9bec3` | 1 | 0.34 |
| Compressor | `#a7adb2` | 1 | 0.39 |
| Combustor | `#938a7e` | 1 | 0.46 |
| Turbine | `#a49787` | 1 | 0.42 |
| Nozzle | `#858a90` | 1 | 0.47 |
| Shaft | `#747a80` | 1 | 0.38 |
| Casing | `#aab0b5` | 0.95 | 0.40 |
| Details | `#c2c5c8` | 1 | 0.30 |

```ts
metal("#b9bec3", 0.34, 1, {
  ...common, clearcoat: 0, envMapIntensity: 1,
});
```

Optionally introduce **stable, per-part** roughness variation of ±0.025 using a small shared material palette. Avoid random per-triangle noise or invented scratches.

### 4. Fix the cutaway’s silhouette and physical thickness

The half-cylinder cut currently gives the intake a broken, open-sheet appearance. Preserve the **complete intake lip and front fan silhouette**, then cut only the downstream bypass shell.

```ts
// Prefer explicit prepared-model metadata over name guessing.
const cutThisMesh =
  mesh.userData.role === "bypassShell" &&
  !mesh.userData.preserveIntakeLip;

mesh.material = cutThisMesh ? shellCutMaterial : shellFullMaterial;
```

If lip and shell are one mesh, split them in preparation. `DoubleSide` reveals backsides but **does not create wall thickness or cap clipping cuts**. Add real cut-edge thickness/bevels offline; reserve double-sided rendering for the shell, not every casing fastener.

The reference also has richer tubing and small hardware. Lighting cannot manufacture geometry missing from the GLB.

### 5. Frame by live component bounds—not cached centers

For explore, use a restrained intake-side three-quarter view: direction from target approximately `[-0.55, 0.22, 1]`, FOV `30°`. Fit the assembly to approximately **85% of the unobstructed viewport width**.

For selection, recompute a world-space box after transforms, then fit its bounding sphere:

```ts
root.updateMatrixWorld(true);
const box = new THREE.Box3();
selectedNodes.forEach(n => box.expandByObject(n));
const sphere = box.getBoundingSphere(new THREE.Sphere());

const usableAspect = (width - leftInset - rightInset) / height;
const v = THREE.MathUtils.degToRad(camera.fov / 2);
const h = Math.atan(Math.tan(v) * usableAspect);
const distance = sphere.radius / Math.sin(Math.min(v, h)) * 1.3;
```

Use `cc.setLookAt(...eye, ...center, true)` with `eye = center + direction * distance`. Set `smoothTime={0.35}`.

- **Blade:** about 55–65% viewport height.
- **Injector:** about 40–50%, with nearby mounting context—not the whole engine.
- **`wide`:** fit the assembly’s current animated bounds.
- Account for both side panels; a full-canvas perspective view offset can use `offsetX = (rightInset - leftInset) / 2`. Clear it when panels close.

The tiny purple injector in image 4 is primarily a framing failure.

### 6. Replace transparent-everything ghosting with deliberate isolation

`opacity: 0.16` across 2,075 meshes accumulates into the smoky spiderweb in images 3–4. Lowering opacity alone won’t solve sorting or overlap.

Default isolate mode:

- Show selected geometry.
- Retain only nearby mounting hardware, **opaque and subdued**.
- Hide distant assemblies.
- Disable raycasting on context-only objects.

```ts
const contextMat = new THREE.MeshStandardMaterial({
  color: "#45494d",
  metalness: 0.35,
  roughness: 0.75,
  envMapIntensity: 0.35,
  transparent: false,
  depthWrite: true,
});
```

For an optional X-ray mode, ghost **one simplified envelope**, not every internal mesh: `opacity: 0.055`, `metalness: 0`, `roughness: 1`, `depthWrite: false`, normal blending. Keep this secondary to a clean inspection view.

### 7. Keep selected parts metallic; add a narrow thermal Fresnel rim

Remove full-surface iridescence and the pulsing purple emissive. Both make the blade look like coated plastic.

```ts
const highlight = metal("#c4c8cc", 0.30, 1, {
  clearcoat: 0,
  envMapIntensity: 1,
  iridescence: 0,
  emissiveIntensity: 0,
  clippingPlanes: [clip],
});
```

Patch its standard lighting shader rather than replacing the entire material:

```glsl
// Insert immediately before #include <opaque_fragment>
float rim = pow(
  1.0 - clamp(dot(normalize(normal), normalize(vViewPosition)), 0.0, 1.0),
  4.5
);
outgoingLight += thermalLinear(uSelectionT) * rim * 0.45;
```

Add declarations/helper through `onBeforeCompile`, and give the patch a stable `customProgramCacheKey`. Supply thermal stops as `new THREE.Color("#38BDF8")`, etc.—these become linear RGB uniforms. Your existing GLSL literals are sRGB values, not linear colors.

Use a stable component-local gradient coordinate for `uSelectionT`/varying, not time. **No breathing glow.** Let the rim and selected UI row carry the brand.

### 8. Rebuild the scan as a thin moving band, not an additive cloud

Your reversed `smoothstep(edge0, edge1, x)` calls have undefined results. Correct them, narrow the front, and remove the second bright “hand” band:

```glsl
float behind = uReveal - vX;
if (behind < 0.0 || vX < uSolid) discard;

float front = 1.0 - smoothstep(0.0, 0.20, behind);
float trail = 1.0 - smoothstep(0.20, 0.85, behind);
float alpha = 0.015 + 0.24 * front + 0.035 * trail;

gl_FragColor = vec4(thermalLinear(t), alpha);
#include <tonemapping_fragment>
#include <colorspace_fragment>
```

```ts
scanMat.blending = THREE.NormalBlending;
scanMat.depthTest = true;
scanMat.depthWrite = false;
```

Further changes:

- Use a **simplified scan mesh**, not every bolt and triangle; suppress rear lines with a simplified depth-only occluder.
- Keep retained wire faint; put the gradient’s emphasis at the advancing front.
- Initialize `scanVal` and `solidVal` in the same centered world-X coordinates as their targets.
- Force the wire pass off at completion so no residual sliver remains.

**Cheap-looking:** the white/magenta ball in image 5. It is overdraw, not useful scan detail.

### 9. Keep the floating presentation; don’t add a showroom floor by default

The reference is suspended against charcoal. A glossy floor or strong circular shadow would change that art direction.

If you intentionally introduce a grounded presentation, use only a faint, broad contact shadow beneath the actual bounds:

```tsx
<ContactShadows
  position={[0, worldBounds.min.y - 0.04, 0]}
  scale={18}
  far={6}
  resolution={512}
  opacity={0.16}
  blur={2.8}
  color="#000000"
  frames={1}
/>
```

Refresh the capture after geometry movement, or update during transitions. Don’t leave a frozen shadow beneath an exploded assembly. Prefer no ground to an obviously fake floating oval.

### 10. Spend performance on stable edges and geometry—not extra passes

At 2,075 meshes, rendering metal + full ghost + full wire + shadows can erase the quality gain.

- Batch static opaque geometry by material/assembly; retain separately selectable components.
- Build the scan proxy offline and mount it only in scan mode.
- **Synchronize `scanRoot` transforms:** its cloned nodes currently do not follow the later explode/removal animation.
- Audit GLB normals; preserve hard edges and authored blade curvature. Add small bevels offline where appropriate rather than blindly recomputing smooth normals.
- Remove per-frame `Box3` allocation/traversal from every hotspot; cache local bounds and update only when transforms change.
- Dispose owned materials on replacement, but not shared cached GLTF geometries.

Prioritize **1–5 first**. They will move the explore screen toward the reference more than bloom, iridescence, or additional gradients.