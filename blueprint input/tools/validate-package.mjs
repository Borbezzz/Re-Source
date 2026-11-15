import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import * as T from 'three';
const dir=new URL('../input-package/',import.meta.url);
const manifest=JSON.parse(await readFile(new URL('manifest.json',dir),'utf8'));
const req=JSON.parse(await readFile(new URL('requirements.json',dir),'utf8'));
for(const file of manifest.files){const bytes=await readFile(new URL(file.path,dir));assert.equal(createHash('sha256').update(bytes).digest('hex'),file.sha256,file.path);}
const bytes=await readFile(new URL('assembly.glb',dir));assert.equal(bytes.toString('ascii',0,4),'glTF');assert.equal(bytes.readUInt32LE(4),2);assert.equal(bytes.readUInt32LE(8),bytes.length);
const jsonLength=bytes.readUInt32LE(12);const gltfJson=JSON.parse(bytes.subarray(20,20+jsonLength).toString());
assert(!gltfJson.buffers.some(b=>b.uri));assert(!gltfJson.images?.length);
const buffer=bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
const gltf=await new GLTFLoader().parseAsync(buffer,'');const scene=gltf.scene;scene.updateMatrixWorld(true);
const stable=new Set(),byStableId=new Map();let meshes=0;scene.traverse(o=>{if(o.userData.stableId){assert(!stable.has(o.userData.stableId),'Duplicate stable ID');stable.add(o.userData.stableId);byStableId.set(o.userData.stableId,o);}if(o.isMesh)meshes++;});
assert.equal(meshes,manifest.geometry.meshOccurrences);assert.equal(manifest.components.length,35);
const csv=(await readFile(new URL('components.csv',dir),'utf8')).trim().split(/\r?\n/);
assert.equal(csv[0],'component_id,role,name,part_number,revision,parent_assembly_id,node_ids,assembly_quantity,requirement_set,data_mode');
assert.equal(csv.length,manifest.components.length+1);
for(let i=0;i<manifest.components.length;i++){
 const c=manifest.components[i];const fields=csv[i+1].match(/"(?:[^"]|"")*"|[^,]+/g).map(x=>x.startsWith('"')?x.slice(1,-1).replaceAll('""','"'):x);
 assert.deepEqual(fields,[c.componentId,c.role,c.name,c.partNumber,c.revision,c.parentAssemblyId,c.nodeIds.join('|'),String(c.assemblyQuantity),c.requirementSet,'fictional_demo'],'CSV/manifest inconsistency');
}
const caseIds=new Set();const checks=[];
for(const c of manifest.components){assert(!caseIds.has(c.componentId));caseIds.add(c.componentId);const r=req.sets.find(x=>x.id===c.requirementSet);assert(r);assert.equal(r.componentId,c.componentId);assert.equal(r.partNumber,c.partNumber);assert.equal(r.revision,c.revision);assert.equal(r.manufacturingTolerances,null);
 const box=new T.Box3();for(const id of c.nodeIds){const node=byStableId.get(id);assert(node,id);assert.equal(node.userData.componentId,c.componentId);box.union(new T.Box3().setFromObject(node));}
 const size=box.getSize(new T.Vector3()).toArray();size.forEach((v,i)=>assert(Math.abs(v-c.bounds.size[i])<1e-4,'Bounds changed after GLB round trip'));
 checks.push({componentId:c.componentId,nodeIds:c.nodeIds,roundTripBounds:size,status:'pass'});
}
// Check a source-specific independent reference: the upstream turbine fixture has 18 injector heads and 24 front fan blades.
const pieces=JSON.parse(await readFile(new URL('../verification/piece-inventory.json',import.meta.url),'utf8'));
assert.equal(pieces.filter(p=>p.parentAssemblyId==='combustor'&&p.displayName==='Fuel injector').length,18);
assert.equal(pieces.filter(p=>p.parentAssemblyId==='fan'&&p.displayName==='Rotor blade').length,24);
assert.equal(pieces.filter(p=>!p.attachedToStableId).length,1835);
const report={status:'pass',checks:['GLB header and byte length','SHA-256 file integrity','No external texture/buffer dependencies','GLTFLoader parse round trip','Unique persistent IDs','CSV/manifest component identity, role, counts and requirement consistency','Three component-to-node and requirement mappings','Round-trip bounds within 1e-4 visualization units','Upstream injector/blade occurrence counts','1835 independent pieces; attached decorations distinguished'],meshOccurrences:meshes,components:checks,notValidated:['physical dimensions','manufacturing tolerances','OEM applicability','supplier qualification','procurement integration','performance across devices']};
await writeFile(new URL('../verification/package-validation.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
