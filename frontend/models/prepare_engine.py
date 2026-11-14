"""Prepare licensed premade cutaway + authored component-study donors in Blender.
Usage: blender --background --factory-startup --python prepare_engine.py -- SOURCE.glb JET_LAB_ROOT
No requirements, engineering dimensions or manufacturing approval are derived here.
"""
import bpy, sys, json, hashlib, math
from pathlib import Path
from mathutils import Vector, Matrix
source=Path(sys.argv[-2]); donor=Path(sys.argv[-1]); root=Path(__file__).resolve().parents[1]
assert hashlib.sha256(source.read_bytes()).hexdigest()=='65ce366afd7fd46f254fef43363f7d4cd39b2cc75899e59c3933fc1dcbe02f88'
donor_hashes = {
 'combustor-manifold':'d85869131a98f6d0d9a2740e7691e94e9374ecbe64375808aae3e9d94d3c0aaf',
 'turbine-nozzle-guide':'342039d21250ef56988f6ad2b815d8e5c1ed806493dfae13c66750ed3142b6b8',
 'compressor-service-hardware':'fc2e2e745d47e967eb106f6489e01fa8ee16257c781daca41472a4dfdd834911',
}
for name, expected in donor_hashes.items():
 assert hashlib.sha256((donor/'public/assets/solidcraft'/f'{name}.glb').read_bytes()).hexdigest() == expected, name
bpy.ops.wm.read_factory_settings(use_empty=True)
modules=['Module_Fan','Module_LPC','Module_HPC','Module_Combustor','Module_HPT','Module_LPT','Module_Exhaust']
groups={}
for name in modules:
 obj=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(obj);obj['moduleName']=name;groups[name]=obj
bpy.ops.import_scene.gltf(filepath=str(source))
# Source centreline +Y in Blender; runtime +X, Y-up. Preserve shape, normalize presentation scale.
mat=Matrix(((0,1.24,0,0),(-1.3,0,0,0),(0,0,1.3,-1.04),(0,0,0,1)))
source_nodes=[];shells=[]
for obj in list(bpy.context.scene.objects):
 if obj.type!='MESH':continue
 old=obj.name;source_nodes.append(old);obj.data.transform(mat@obj.matrix_world);obj.parent=None;obj.matrix_world=Matrix.Identity(4)
 if old.startswith('Compressor_rotor_'):mod='Module_LPC' if int(old[-1])<=2 else 'Module_HPC'
 elif old in ['Fan_20_blades','Spinner','Nacelle']:mod='Module_Fan'
 elif 'Compressor' in old:mod='Module_HPC'
 elif 'combustor' in old.lower():mod='Module_Combustor'
 elif old.startswith('High_pressure') or old=='Turbine_case':mod='Module_HPT'
 elif old.startswith('Low_pressure'):mod='Module_LPT'
 else:mod='Module_Exhaust'
 obj.parent=groups[mod];obj['source_node']=old;obj['source_asset']='Innerscene turbofan quarter cutaway (CC0)'
 if old.endswith('_case') or old=='Nacelle':shells.append(obj)
 # Preserve hard CAD edges while smoothing curved surfaces, with weighted corner normals.
 for face in obj.data.polygons:face.use_smooth=True
 obj.data.set_sharp_from_angle(angle=math.radians(35))
 for material in obj.data.materials:
  if not material or not material.use_nodes:continue
  p=material.node_tree.nodes.get('Principled BSDF')
  if p:
   p.inputs['Metallic'].default_value=.74;p.inputs['Roughness'].default_value=.27
   if 'combustor' in old.lower():p.inputs['Base Color'].default_value=(.25,.16,.09,1)
# Remove original import-only empty after baking its world transform.
for obj in list(bpy.context.scene.objects):
 if obj.type=='EMPTY' and obj.name not in modules:bpy.data.objects.remove(obj,do_unlink=True)

def donor_part(file,node_name,component,group,anchor,filterfn,scale):
 before=set(bpy.context.scene.objects)
 path=donor/'public/assets/solidcraft'/f'{file}.glb'
 bpy.ops.import_scene.gltf(filepath=str(path))
 imported=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH']
 for obj in imported:
  bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
  bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=.000001);bpy.ops.mesh.separate(type='LOOSE');bpy.ops.object.mode_set(mode='OBJECT')
 selected=[]
 for obj in list(bpy.context.scene.objects):
  if obj in before:continue
  if obj.type!='MESH':bpy.data.objects.remove(obj,do_unlink=True);continue
  pts=[obj.matrix_world@v.co for v in obj.data.vertices];lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)];c=[(lo[i]+hi[i])/2 for i in range(3)]
  if filterfn(obj.name,c,lo,hi):selected.append(obj)
  else:bpy.data.objects.remove(obj,do_unlink=True)
 assert selected, file
 bpy.ops.object.select_all(action='DESELECT')
 for obj in selected:obj.select_set(True)
 bpy.context.view_layer.objects.active=selected[0];bpy.ops.object.join();obj=bpy.context.object
 bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY',center='BOUNDS')
 obj.scale=(scale,scale,scale);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 # These donor studies are visibly placed at the existing synthetic case markers.
 # They are representative counterparts, not exact OEM or numbered physical identities.
 obj.location=(anchor[0],-anchor[2],anchor[1]);obj.name=node_name;obj.parent=groups[group]
 obj['componentId']=component;obj['source_asset']=file;obj['provenance']='premade_component_study';obj['identity_note']='Representative counterpart to a synthetic case, not exact OEM geometry'
 return {'node_name':node_name,'component_id':component,'source_file':file+'.glb','source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mapping':'representative counterpart; synthetic position/part number remains in backend'}
parts=[]
parts.append(donor_part('combustor-manifold','Component_FuelNozzle_07','component-primary','Module_Combustor',[.05,.48,.18],lambda n,c,l,h:c[2]>.4 and abs(c[1])<.01,.55))
parts.append(donor_part('turbine-nozzle-guide','Component_NGV_Segment_12','component-secondary-a','Module_HPT',[.48,.34,-.12],lambda n,c,l,h:'heat' in n and c[2]>.5 and -.08<c[1]<-.05,.5))
parts.append(donor_part('compressor-service-hardware','Component_BleedDuct_HP','component-secondary-b','Module_HPC',[-.62,.48,.24],lambda n,c,l,h:'shell' in n and c[2]>.8 and abs(c[1])<.01,1.4))
# One authored sequence: lift casing first; spread modules second. Reverse uses the same keys.
def keys(obj,values):
 for frame,delta in values:
  obj.location=Vector(delta);obj.keyframe_insert(data_path='location',frame=frame)
 if obj.animation_data and obj.animation_data.action:
  for fc in obj.animation_data.action.fcurves:
   for k in fc.keyframe_points:k.interpolation='BEZIER';k.handle_left_type='AUTO_CLAMPED';k.handle_right_type='AUTO_CLAMPED'
for index,name in enumerate(modules):
 d=(index-3)*.52
 keys(groups[name],[(1,(0,0,0)),(25,(0,0,0)),(90,(d,0,0))])
for obj in shells:
 if obj.name=='Nacelle':offset=(1.1,1.8,.95)
 elif obj.name=='Compressor_case':offset=(0,.72,.8)
 elif obj.name=='Combustor_case':offset=(0,.65,.7)
 else:offset=(0,.6,.65)
 keys(obj,[(1,(0,0,0)),(35,offset),(90,offset)])
scene=bpy.context.scene;scene.render.fps=30;scene.frame_start=1;scene.frame_end=90;scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
# Store a useful studio view in the .blend for continued authored inspection.
bpy.ops.object.camera_add(location=(-5,-7,3));cam=bpy.context.object;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=8;scene.camera=cam
scene.world=bpy.data.worlds.new('Studio');scene.world.color=(.12,.12,.12)
for pos,power,size in [((-3,-4,6),1000,5),((2,3,4),1300,4),((-4,1,0),500,3)]:
 bpy.ops.object.light_add(type='AREA',location=pos);obj=bpy.context.object;obj.data.energy=power;obj.data.shape='DISK';obj.data.size=size;obj.rotation_euler=(-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.resolution_x=1440;scene.render.resolution_y=900;scene.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=str(root/'models/engine-cutaway.blend'))
bpy.ops.export_scene.gltf(filepath=str(root/'public/models/engine-cutaway.glb'),export_format='GLB',export_animations=True,export_animation_mode='SCENE',export_extras=True,export_cameras=False,export_lights=False)
manifest={'asset_url':'/models/engine-cutaway.glb','source_url':'https://www.innerscene.com/tools/library/3d-parts/turbofan-quarter-cutaway-e0184203','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'license':'CC0-1.0','donor_url':'https://github.com/AungMyoKyaw/jet-engine-lab/tree/07dc2651814ae4736f1ee2cbfd7f12c89d3b8b85','donor_license':'MIT','modules':modules,'source_nodes':source_nodes,'component_studies':parts,'note':'Prepared cutaway and component studies, not a complete production engine or source of requirements.'}
(root/'src/scene/prepared-engine.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('RESOURCE_ENGINE',json.dumps({'bytes':(root/'public/models/engine-cutaway.glb').stat().st_size,'parts':parts}))
