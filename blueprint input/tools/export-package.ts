import * as T from 'three';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { buildPreparedTurbofan } from './vendor/prepared-turbofan.ts';

// GLTFExporter needs only these FileReader operations for this texture-free scene.
class BlobReader {
 result: ArrayBuffer | string | null = null;
 onloadend: (()=>void) | null = null;
 onerror: ((e:unknown)=>void) | null = null;
 readAsArrayBuffer(blob: Blob){blob.arrayBuffer().then(b=>{this.result=b;this.onloadend?.();}).catch(e=>this.onerror?.(e));}
 readAsDataURL(blob: Blob){blob.arrayBuffer().then(b=>{this.result=`data:${blob.type};base64,${Buffer.from(b).toString('base64')}`;this.onloadend?.();}).catch(e=>this.onerror?.(e));}
}
(globalThis as any).FileReader=BlobReader;
const out=fileURLToPath(new URL('../input-package/',import.meta.url));
await mkdir(out,{recursive:true});
const config=JSON.parse(await readFile(new URL('./package-config.json',import.meta.url),'utf8'));
const threeVersion=JSON.parse(await readFile(new URL('./node_modules/three/package.json',import.meta.url),'utf8')).version;
const buildFingerprint=createHash('sha256').update(await readFile(new URL('./vendor/prepared-turbofan.ts',import.meta.url))).update(await readFile(new URL('./export-package.ts',import.meta.url))).update(threeVersion).digest('hex');
let previous:any=null;try{previous=JSON.parse(await readFile(out+'manifest.json','utf8'));}catch(e){if((e as any).code!=='ENOENT')throw e;}
if(previous?.packageVersion===config.packageVersion&&previous.buildFingerprint&&previous.buildFingerprint!==buildFingerprint)throw new Error('Build changed: increment packageVersion in tools/package-config.json before exporting.');
async function writeVersioned(name:string,bytes:string|Buffer){
 const expected=previous?.packageVersion===config.packageVersion?previous.files.find((f:any)=>f.path===name)?.sha256:null;
 if(expected&&createHash('sha256').update(bytes).digest('hex')!==expected)throw new Error(`Refusing to change ${name} under existing packageVersion; increment version first.`);
 await writeFile(out+name,bytes);
}
const {root:original,rotors}=buildPreparedTurbofan();
const rotorSet=new Set(rotors);
const exported=new T.Group();exported.name='ReSource demo turbofan';
exported.userData={packageId:'rs-mechanica-turbofan-v1',dataMode:'fictional_demo',sourceCommit:'a1d52be81b5e9ea125df337a3b30039ff996edc8',physicalScaleValidated:false};
const allPieces:any[]=[];const groups:Record<string,T.Object3D>={};
const attachments=new Map<string,string>();
let transformSerial=0;
function copyNode(source:T.Object3D,parent:T.Object3D){
 source.updateMatrix();
 if(source instanceof T.Mesh){
  const count=source instanceof T.InstancedMesh?source.count:1;
  for(let i=0;i<count;i++){
   const local=source.matrix.clone();
   if(source instanceof T.InstancedMesh){const instance=new T.Matrix4();source.getMatrixAt(i,instance);local.multiply(instance);}
   const stableId=`rs-mech-tf-v1.${source.userData.part}.m${String(source.userData.sourceMeshIndex).padStart(3,'0')}.i${String(i).padStart(3,'0')}`;
   const label=source.userData.pieceName??'Component';
   const material=(source.material as T.MeshStandardMaterial).clone();material.clippingPlanes=[];material.userData={};
   const mesh=new T.Mesh(source.geometry,material);mesh.name=stableId;
   local.decompose(mesh.position,mesh.quaternion,mesh.scale);
   mesh.userData={stableId,parentAssemblyId:source.userData.part,displayName:label,sourceMeshIndex:source.userData.sourceMeshIndex,sourceInstanceIndex:i,upstreamPieceId:`${source.userData.part}:${source.userData.upstreamFirstPieceSerial+i}`,dataMode:'fictional_demo'};
   parent.add(mesh);allPieces.push({stableId,parentAssemblyId:source.userData.part,displayName:label,upstreamPieceId:mesh.userData.upstreamPieceId,sourceMeshIndex:source.userData.sourceMeshIndex,sourceInstanceIndex:i,sourceAttachToUuid:source.userData.attachTo??null,sourceUuid:source.uuid});
   if(!(source instanceof T.InstancedMesh))attachments.set(source.uuid,stableId);
  }
 }else{
  const group=new T.Group();group.name=source.userData.id?`rs-mech-tf-v1.group.${source.userData.id}`:`rs-mech-tf-v1.transform.${transformSerial++}`;
  group.position.copy(source.position);group.quaternion.copy(source.quaternion);group.scale.copy(source.scale);
  group.userData={stableId:group.name,...(source.userData.id?{assemblyId:source.userData.id,displayName:source.userData.displayName}:{})};
  if(rotorSet.has(source))group.userData.rotationAxis='x';
  parent.add(group);if(source.userData.id)groups[source.userData.id]=group;
  for(const child of source.children)copyNode(child,group);
 }
}
for(const child of original.children)copyNode(child,exported);
for(const piece of allPieces){if(piece.sourceAttachToUuid)piece.attachedToStableId=attachments.get(piece.sourceAttachToUuid);delete piece.sourceUuid;delete piece.sourceAttachToUuid;}
const primary=allPieces.find(p=>p.parentAssemblyId==='combustor'&&p.displayName==='Fuel injector');
const blade=allPieces.find(p=>p.parentAssemblyId==='fan'&&p.displayName==='Rotor blade'&&p.sourceInstanceIndex===0);
if(!primary||!blade||!groups.nozzle)throw new Error('Required demo geometry not found.');
const cases=[
 {componentId:'RS-TF-FUEL-INJECTOR',role:'secondary',name:'Fuel injectors',partNumber:'RS-DEMO-FI-001',revision:'C',parentAssemblyId:'combustor',nodeIds:allPieces.filter(p=>p.parentAssemblyId==='combustor'&&p.displayName==='Fuel injector').map(p=>p.stableId),assemblyQuantity:18,condition:'new',requirementSet:'REQ-FI-C'},
 {componentId:'RS-TF-FAN-BLADE',role:'primary',name:'Front fan blades',partNumber:'RS-DEMO-FB-001',revision:'B',parentAssemblyId:'fan',nodeIds:allPieces.filter(p=>p.parentAssemblyId==='fan'&&p.displayName==='Rotor blade').map(p=>p.stableId),assemblyQuantity:24,condition:'new',requirementSet:'REQ-FB-B'},
 {componentId:'RS-TF-CORE-NOZZLE',role:'secondary',name:'Core exhaust nozzle assembly',partNumber:'RS-DEMO-NZ-001',revision:'A',parentAssemblyId:'nozzle',nodeIds:[groups.nozzle.name],assemblyQuantity:1,condition:'new',requirementSet:'REQ-NZ-A'}
];
// Explicit fictional part families for the expanded browser. Repeated geometry
// shares a demo identity only where this manifest deliberately assigns it.
function addCase(id:string,name:string,assembly:string,pieces:typeof allPieces){
 cases.push({componentId:`RS-TF-${id}`,role:'secondary',name,partNumber:`RS-DEMO-${id}`,revision:'A',parentAssemblyId:assembly,nodeIds:pieces.map(p=>p.stableId),assemblyQuantity:pieces.length,condition:'new',requirementSet:`REQ-${id}-A`});
}
addCase('FAN-VANE','Fan guide vanes','fan',allPieces.filter(p=>p.parentAssemblyId==='fan'&&p.displayName==='Stator vane'));
addCase('SPINNER','Fan spinner','fan',allPieces.filter(p=>p.parentAssemblyId==='fan'&&p.displayName==='Spinner / cone'));
for(const assembly of ['compressor','turbine']){
 for(const [label,code] of [['Rotor blade','ROTOR'],['Stator vane','STATOR']]){
  const pieces=allPieces.filter(p=>p.parentAssemblyId===assembly&&p.displayName===label);
  const stages=[...new Set(pieces.map(p=>p.sourceMeshIndex))];
  stages.forEach((index,i)=>addCase(`${assembly==='compressor'?'CP':'TB'}-${code}-${String(i+1).padStart(2,'0')}`,`${assembly==='compressor'?'Compressor':'Turbine'} stage ${i+1} ${label==='Rotor blade'?'rotor blades':'stator vanes'}`,assembly,pieces.filter(p=>p.sourceMeshIndex===index)));
 }
}
addCase('COMBUSTOR-LINER','Combustor liners','combustor',allPieces.filter(p=>p.parentAssemblyId==='combustor'&&p.displayName==='Housing'));
addCase('FUEL-TUBE','Fuel feed tubes','combustor',allPieces.filter(p=>p.parentAssemblyId==='combustor'&&p.displayName==='Tube'));
addCase('CASING','Engine casing sections','casing',allPieces.filter(p=>p.parentAssemblyId==='casing'&&p.displayName==='Housing'));
addCase('SHAFT','Shafts and sleeves','shaft',allPieces.filter(p=>p.parentAssemblyId==='shaft'&&p.displayName==='Shaft / sleeve'));
// Complete the independent-piece inventory with explicit demo specifications.
// Distinct source meshes keep distinct identities; repeated instances share one
// family. Attached surface decorations remain part of their parent's purchase.
const mappedPieces=new Set(cases.flatMap(c=>c.nodeIds));
const missingFamilies=new Map<string,typeof allPieces>();
for(const piece of allPieces){
 if(piece.attachedToStableId||mappedPieces.has(piece.stableId))continue;
 const key=`${piece.parentAssemblyId}:${piece.sourceMeshIndex}`;
 const family=missingFamilies.get(key)??[];family.push(piece);missingFamilies.set(key,family);
}
const assemblyNames:Record<string,string>={fan:'Fan',compressor:'Compressor',combustor:'Combustor',turbine:'Turbine',nozzle:'Nozzle',casing:'Casing',shaft:'Shaft'};
const assemblyCodes:Record<string,string>={fan:'FAN',compressor:'CP',combustor:'CB',turbine:'TB',nozzle:'NZ',casing:'CA',shaft:'SH'};
const kindCodes:Record<string,string>={'Retaining ring':'RING','Housing':'HOUSING','Fastener':'FASTENER','Tube':'TUBE','Stator vane':'VANE'};
const familyCounts=new Map<string,number>();const familySerials=new Map<string,number>();
for(const pieces of missingFamilies.values()){const p=pieces[0],key=`${p.parentAssemblyId}:${p.displayName}`;familyCounts.set(key,(familyCounts.get(key)??0)+1);}
for(const pieces of missingFamilies.values()){
 const p=pieces[0],assembly=p.parentAssemblyId,key=`${assembly}:${p.displayName}`;
 const serial=(familySerials.get(key)??0)+1;familySerials.set(key,serial);
 const noun=p.displayName.toLowerCase()+(pieces.length>1?'s':'');
 const name=`${assemblyNames[assembly]} ${noun}${familyCounts.get(key)!>1?' '+String(serial).padStart(2,'0'):''}`;
 addCase(`${assemblyCodes[assembly]}-${kindCodes[p.displayName]}-M${String(p.sourceMeshIndex).padStart(3,'0')}`,name,assembly,pieces);
}
const caseByNode=new Map(cases.flatMap(c=>c.nodeIds.map(id=>[id,c.componentId] as const)));
if(allPieces.some(p=>!p.attachedToStableId&&!caseByNode.has(p.stableId)))throw new Error('Independent piece lacks a sourcing specification.');
exported.traverse(o=>{if(caseByNode.has(o.name))o.userData.componentId=caseByNode.get(o.name);const piece=allPieces.find(p=>p.stableId===o.name);if(piece?.attachedToStableId)o.userData.attachedToStableId=piece.attachedToStableId;});
exported.updateMatrixWorld(true);
const box=new T.Box3().setFromObject(exported);
const inventory=cases.map(c=>{
 const nodes=c.nodeIds.map(id=>exported.getObjectByName(id)!);const bounds=new T.Box3();for(const node of nodes)bounds.union(new T.Box3().setFromObject(node));
 return {...c,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray(),size:bounds.getSize(new T.Vector3()).toArray(),unit:'visualization_unit',provenance:'derived_from_prepared_geometry_not_physical_measurement'},dataMode:'fictional_demo'};
});
const requirements={schemaVersion:'1.0',dataMode:'fictional_demo',authority:'buyer_defined_hackathon_fixture',engineeringApprovalStatus:'not_established',sets:inventory.map(c=>({id:c.requirementSet,componentId:c.componentId,partNumber:c.partNumber,revision:c.revision,sourcingRoute:'exact_demo_part',condition:'new',mandatoryChecks:[{id:'identity',kind:'exact_match',fields:['partNumber','revision'],provenance:'fictional_demo_identity'},{id:'applicability',kind:'document_review',requiredEvidence:'Document linking the offered part/revision to this demo assembly configuration',provenance:'buyer_defined_demo_requirement'},{id:'traceability',kind:'document_review',requiredEvidence:'Supplier identity, manufacturer/origin, serial or lot identifier, and supporting release/quality records appropriate to transaction',provenance:'buyer_defined_demo_requirement'},{id:'site',kind:'site_evidence',requiredEvidence:'Evidence relevant to the supplying site and the offered activity',provenance:'buyer_defined_demo_requirement'},{id:'availability',kind:'supplier_confirmation',requiredEvidence:'Quantity and dispatch commitment for the requested part/revision',provenance:'buyer_defined_demo_requirement'},{id:'arrival',kind:'date_comparison',against:'request.requiredArrivalDate',provenance:'user_sourcing_request'}],manufacturingTolerances:null,materialGrade:null,notes:'Educational geometry supplies visual identity only. Missing mandatory evidence remains awaiting verification. These fixtures do not supply real approved-part applicability or manufacturing acceptance.'}))};
const csvHeader=['component_id','role','name','part_number','revision','parent_assembly_id','node_ids','assembly_quantity','requirement_set','data_mode'];
const quote=(x:unknown)=>'"'+String(x).replaceAll('"','""')+'"';
const csv=csvHeader.join(',')+'\n'+inventory.map(c=>[c.componentId,c.role,c.name,c.partNumber,c.revision,c.parentAssemblyId,c.nodeIds.join('|'),c.assemblyQuantity,c.requirementSet,'fictional_demo'].map(quote).join(',')).join('\n')+'\n';
await writeVersioned('components.csv',csv);
await writeVersioned('requirements.json',JSON.stringify(requirements,null,2)+'\n');
const buffer=await new GLTFExporter().parseAsync(exported,{binary:true,onlyVisible:false,trs:true});
if(!(buffer instanceof ArrayBuffer))throw new Error('GLB export did not return binary.');
await writeVersioned('assembly.glb',Buffer.from(buffer));
const digest=async(file:string)=>createHash('sha256').update(await readFile(out+file)).digest('hex');
const manifest={schemaVersion:'1.0',packageId:'rs-mechanica-turbofan-v1',displayName:'ReSource prepared turbofan demo',packageVersion:config.packageVersion,buildFingerprint,toolchain:{node:process.versions.node,three:threeVersion},dataMode:'fictional_demo',source:{repository:'https://github.com/PouyanJay/mechanica',commit:'a1d52be81b5e9ea125df337a3b30039ff996edc8',license:'MIT'},geometry:{file:'assembly.glb',kind:'prepared_visualization_assembly',isManufacturingCAD:false,unit:'visualization_unit',gltfCoordinateConvention:'glTF coordinates use the metre convention; physical correspondence is not validated',physicalScaleValidated:false,upAxis:'Y',engineAxis:'X',bounds:{min:box.min.toArray(),max:box.max.toArray()},meshOccurrences:allPieces.length,independentPieces:allPieces.filter(p=>!p.attachedToStableId).length,containsExternalTextures:false},files:await Promise.all(['assembly.glb','components.csv','requirements.json','LICENSE-Mechanica.txt','ATTRIBUTION.md'].map(async path=>({path,sha256:await digest(path)}))),components:inventory,selectionContract:{resolve:'Nearest ancestor with userData.componentId; otherwise inspect group without starting a sourcing case',stableIdentity:'Persist exported stableId and componentId with package version; do not regenerate serial-only IDs',homeTransforms:'Keep loaded GLB transforms unchanged as canonical home; animate clones or store/restore every transform',assemblyQuantity:'Count in assembly, not quantity being purchased'},sourcingInputs:{required:['reason','quantity','requiredArrivalDate','deliveryDestination'],defaults:{reason:'faulty_component',quantity:1},providedBy:'UI after component selection; company/contact profile before outreach, commercial details before commitment'}};
await writeFile(out+'manifest.json',JSON.stringify(manifest,null,2)+'\n');
await writeFile(fileURLToPath(new URL('../verification/piece-inventory.json',import.meta.url)),JSON.stringify(allPieces,null,2)+'\n');
console.log(JSON.stringify({glbBytes:buffer.byteLength,meshOccurrences:allPieces.length,independentPieces:manifest.geometry.independentPieces,cases:inventory.map(c=>({id:c.componentId,nodes:c.nodeIds}))},null,2));
