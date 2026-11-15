# Prepared Toy Car assembly

Source: [Khronos glTF Sample Assets / ToyCar](https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/ToyCar).
Original car: Guido Odendahl (2020). Extensions/scene composition: Eric Chadwick (2020). Both CC0-1.0, per the source metadata. ReSource removes the presentation fabric, separates connected geometry, groups wheel assemblies/body/glazing/bumpers, sets origins, authors 1–90 frame explosion and exports GLB. Eight visual groups are not a certified bill of materials. No dimensions, materials, tolerances or compatibility are inferred from this geometry.

Reproduce with Blender 4.4.3:

```sh
curl -fL https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models/ToyCar/glTF-Binary/ToyCar.glb -o /tmp/ToyCar.glb
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python frontend/models/prepare_toy_car.py -- /tmp/ToyCar.glb
```

Source SHA-256: `01a60862de55cd4b9f3acfab0b0def86451800f9c42467fcd61052c16cb9838c` (checked by the script). Outputs: `toy-car.blend`, `../public/models/toy-car.glb`, `../src/product/toy-car.json`. Browser uses the same authored separation vectors and stable node/component IDs, with reduced-motion/direct controls. The exported GLB contains the authored animation as well.
