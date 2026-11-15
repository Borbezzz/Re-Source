"""Prepare the licensed Khronos lamp as three selectable visual groups.

Blender --background --factory-startup --python frontend/models/prepare_desk_lamp.py -- SOURCE.glb
The authored groups and scale are presentation aids, not engineering measurements.
"""
import hashlib
import sys
from pathlib import Path

import bpy
from mathutils import Vector

source = Path(sys.argv[-1])
assert hashlib.sha256(source.read_bytes()).hexdigest() == "b9a95cd0e17dea5284117e54807b49b746960038457a31a0011b9344acc11104", "Unexpected source revision"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
assert len(meshes) == 3
# Original mesh bounds uniquely distinguish the frame, flat base insert and shade.
for obj in meshes:
    points = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
    height = max(v.z for v in points) - min(v.z for v in points)
    obj.name = "Lamp_Frame" if height > 1 else "Lamp_BaseInsert" if height < .01 else "Lamp_Shade"
    obj["provenance"] = "prepared_visual_group"
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.select_set(False)
for obj in list(bpy.context.scene.objects):
    if obj.type != "MESH":
        bpy.data.objects.remove(obj, do_unlink=True)
for obj in meshes:
    for vertex in obj.data.vertices:
        vertex.co *= 2
for image in bpy.data.images:
    if max(image.size) > 1024:
        ratio = 1024 / max(image.size)
        image.scale(max(1, int(image.size[0] * ratio)), max(1, int(image.size[1] * ratio)))
out = Path(__file__).resolve().parents[1] / "public/models/desk-lamp.glb"
bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", export_animations=False, export_extras=True)
print("Prepared", out, [(o.name, len(o.data.vertices)) for o in meshes])
