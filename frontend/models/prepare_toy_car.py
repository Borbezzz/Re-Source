"""Prepare the CC0 Khronos Toy Car as selectable presentation groups.
Run: Blender --background --factory-startup --python frontend/models/prepare_toy_car.py -- SOURCE.glb
The input checksum is pinned; geometry is visual reference, not engineering requirements.
"""
import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
source=Path(sys.argv[-1]); root=Path(__file__).resolve().parents[1]
assert hashlib.sha256(source.read_bytes()).hexdigest() == '01a60862de55cd4b9f3acfab0b0def86451800f9c42467fcd61052c16cb9838c', 'Unexpected source revision'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
for obj in list(bpy.data.objects):
 if obj.type!='MESH' or obj.name=='Fabric': bpy.data.objects.remove(obj,do_unlink=True)
car=bpy.data.objects['ToyCar'];bpy.ops.object.select_all(action='DESELECT');car.select_set(True);bpy.context.view_layer.objects.active=car
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.remove_doubles(threshold=0.0000001);bpy.ops.mesh.separate(type='LOOSE');bpy.ops.object.mode_set(mode='OBJECT')
groups={k:[] for k in ['Body','Glazing','Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR','Bumper_F','Bumper_R']}
for obj in list(bpy.data.objects):
 if obj.type!='MESH':continue
 if obj.name=='Glass': groups['Glazing'].append(obj);continue
 vs=[obj.matrix_world@v.co for v in obj.data.vertices];lo=[min(v[i] for v in vs) for i in range(3)];hi=[max(v[i] for v in vs) for i in range(3)];c=[(lo[i]+hi[i])/2 for i in range(3)]
 if lo[2]>.0 and hi[2]<.0065 and abs(c[0])>.0055 and ((lo[1]>.0075 and hi[1]<.0136) or (lo[1]>-.0163 and hi[1]<-.0104)):
  name='Wheel_'+('F' if c[1]>0 else 'R')+('L' if c[0]<0 else 'R')
 elif lo[1]>.017: name='Bumper_F'
 elif hi[1]<-.017 and hi[2]<.006: name='Bumper_R'
 else:name='Body'
 groups[name].append(obj)
labels={'Body':'Body shell','Glazing':'Window glazing','Wheel_FL':'Front left wheel','Wheel_FR':'Front right wheel','Wheel_RL':'Rear left wheel','Wheel_RR':'Rear right wheel','Bumper_F':'Front bumper','Bumper_R':'Rear bumper'}
# Directions are in exported glTF axes (x, up, z), not source dimensions.
dirs={'Body':[0,.55,0],'Glazing':[0,1.55,0],'Wheel_FL':[-1.15,-.15,-.1],'Wheel_FR':[1.15,-.15,-.1],'Wheel_RL':[-1.15,-.15,.1],'Wheel_RR':[1.15,-.15,.1],'Bumper_F':[0,0,-1.2],'Bumper_R':[0,0,1.2]}
parts=[]
for name,objs in groups.items():
 if not objs: raise ValueError('Empty part '+name)
 bpy.ops.object.select_all(action='DESELECT')
 for obj in objs:obj.select_set(True)
 bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join();obj=bpy.context.object;obj.name='ToyCar_'+name
 for v in obj.data.vertices:v.co*=130
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY',center='BOUNDS')
 if len(obj.data.polygons)>3000:
  mod=obj.modifiers.new('Web geometry','DECIMATE');mod.ratio=.65;bpy.ops.object.modifier_apply(modifier=mod.name)
 obj['component_id']='toycar-'+name.lower().replace('_','-');obj['source_node']='Glass' if name=='Glazing' else 'ToyCar';obj['provenance']='curated_cc0_visual_group'
 start=obj.location.copy();obj.keyframe_insert(data_path='location',frame=1)
 dx,dy,dz=dirs[name];obj.location=start+Vector((dx,-dz,dy));obj.keyframe_insert(data_path='location',frame=90);obj.location=start
 parts.append({'component_id':obj['component_id'],'node_name':obj.name,'label':labels[name],'explode':dirs[name],'source_node':obj['source_node'],'requirements_status':'source_required'})
for img in bpy.data.images:
 if img.size[0]>1024: img.scale(1024,max(1,int(img.size[1]*1024/img.size[0])))
bpy.context.scene.frame_set(1);bpy.context.scene.frame_end=90
out=root/'public/models';out.mkdir(parents=True,exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(out/'toy-car.glb'),export_format='GLB',export_animations=True,export_extras=True,export_image_format='AUTO')
bpy.ops.wm.save_as_mainfile(filepath=str(root/'models/toy-car.blend'))
manifest={'assembly_id':'toy-car-demo','name':'Toy car assembly','asset_url':'/models/toy-car.glb','provenance':'Curated CC0 model, separated into visual groups in Blender. Not reconstructed from an uploaded blueprint.','source_url':'https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/ToyCar','license':'CC0-1.0','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'authors':['Guido Odendahl','Eric Chadwick'],'components':parts}
(root/'src/product/toy-car.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('RESOURCE_EXPORT='+json.dumps({'parts':len(parts),'bytes':(out/'toy-car.glb').stat().st_size,'sha256':manifest['source_sha256']}))
