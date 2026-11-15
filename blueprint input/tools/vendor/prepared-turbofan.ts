// Derived from Mechanica, MIT, pinned commit a1d52be81b5e9ea125df337a3b30039ff996edc8.
// Original geometry retained; browser UI, renderer and other engine families excluded.
import * as T from 'three';
export function buildPreparedTurbofan(){
 const TAU=Math.PI*2;
 const root=new T.Group();root.name='mechanica-turbofan';
 const groups:Record<string,T.Group>={};
 const names:Record<string,string>={fan:'Fan and inlet',compressor:'Axial compressor',combustor:'Annular combustor',turbine:'Turbine stages',nozzle:'Core exhaust nozzle',casing:'Casing and bypass',shaft:'Shafts and bearings'};
 for(const [id,name] of Object.entries(names)){const g=new T.Group();g.name=id;g.userData={id,displayName:name};root.add(g);groups[id]=g;}
 const materials:T.MeshStandardMaterial[]=[],rotors:T.Group[]=[];
 const clip=new T.Plane(new T.Vector3(0,-1,0),.15);
 let triangles=0;
 const fan=true,power=false,kind='turbofan';
  function material(color:number,rough=.33,metal=.88,clipped=false){const m=new T.MeshStandardMaterial({color,roughness:rough,metalness:metal,side:T.DoubleSide,clippingPlanes:clipped?[clip]:[]});m.userData.base=new T.Color(color);materials.push(m);return m;}
  function mesh(g:T.BufferGeometry,m:T.Material,parent:T.Object3D){const o=new T.Mesh(g,m);o.castShadow=true;o.receiveShadow=true;parent.add(o);triangles+=(g.index?.count??g.attributes.position.count)/3;return o;}
  // Surface of revolution around X. The profile is [axial position, radius].
  function lathe(profile:number[][],m:T.Material,parent:T.Object3D){const g=new T.LatheGeometry(profile.map(p=>new T.Vector2(p[1],p[0])),128);g.rotateZ(-Math.PI/2);const o=mesh(g,m,parent);o.userData.pieceName=profile[0][1]===0?'Spinner / cone':'Housing';return o;}
  function cyl(x:number,len:number,r:number,m:T.Material,parent:T.Object3D,r2=r){const g=new T.CylinderGeometry(r2,r,len,80);g.rotateZ(-Math.PI/2);const o=mesh(g,m,parent);o.position.x=x;o.userData.pieceName=r<.1?'Fuel injector':'Shaft / sleeve';return o;}
  function ring(x:number,r:number,t:number,m:T.Material,parent:T.Object3D){const g=new T.TorusGeometry(r,t,10,112);g.rotateY(Math.PI/2);const o=mesh(g,m,parent);o.position.x=x;o.userData.pieceName='Retaining ring';return o;}
  // Closed, swept airfoil with spanwise twist. This is original reference geometry.
  function blade(inner:number,outer:number,chord:number,sweep:number,twist:number){const verts:number[]=[],idx:number[]=[];const spans=18,around=32;
   for(let i=0;i<=spans;i++){const t=i/spans,r=inner+(outer-inner)*t,c=chord*(1-.38*t),ang=twist*(1-t)+.2;
    for(let j=0;j<around;j++){const a=j/around*TAU,u=(1-Math.cos(a))*.5;const thick=5*.105*(.2969*Math.sqrt(u)-.126*u-.3516*u*u+.2843*u*u*u-.1036*u*u*u*u)*Math.sign(Math.sin(a));const camber=.05*Math.sin(Math.PI*u),xx=(u-.5)*c,zz=(thick+camber)*c;
     verts.push(xx*Math.cos(ang)-zz*Math.sin(ang)+sweep*t*t,r,xx*Math.sin(ang)+zz*Math.cos(ang)+.14*t*t);
    }
   }for(let i=0;i<spans;i++)for(let j=0;j<around;j++){const a=i*around+j,b=i*around+(j+1)%around,c=a+around,d=b+around;idx.push(a,b,c,b,d,c);}for(let j=1;j<around-1;j++){idx.push(0,j+1,j);const b=spans*around;idx.push(b,b+j,b+j+1);}
   const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(verts,3));g.setIndex(idx);g.computeVertexNormals();return g;}
  function blades(parent:T.Group,x:number,inner:number,outer:number,count:number,chord:number,m:T.Material,rotating:boolean,sweep=.15,twist=.7){const group=new T.Group();group.position.x=x;parent.add(group);if(rotating)rotors.push(group);const geo=blade(inner,outer,chord,sweep,twist);const batch=new T.InstancedMesh(geo,m,count);const mat=new T.Matrix4();for(let i=0;i<count;i++){mat.makeRotationX(i/count*TAU);batch.setMatrixAt(i,mat);}batch.userData.pieceName=rotating?'Rotor blade':'Stator vane';batch.userData.inventoryFlat=true;batch.castShadow=true;batch.receiveShadow=true;group.add(batch);triangles+=(geo.index?.count??0)/3*count;return group;}
  function bolts(parent:T.Group,x:number,r:number,count:number,m:T.Material){const g=new T.CylinderGeometry(.042,.042,.065,6);g.rotateZ(Math.PI/2);const b=new T.InstancedMesh(g,m,count),mat=new T.Matrix4();for(let i=0;i<count;i++){const a=i/count*TAU;mat.makeTranslation(x,Math.sin(a)*r,Math.cos(a)*r);b.setMatrixAt(i,mat);}b.userData.pieceName='Fastener';parent.add(b);}
  function pipe(points:T.Vector3[],r:number,m:T.Material,parent:T.Object3D){const o=mesh(new T.TubeGeometry(new T.CatmullRomCurve3(points),32,r,8,false),m,parent);o.userData.pieceName='Tube';o.userData.inventoryFlat=true;return o;}
   const titanium=material(0xb0bdc9,.29),silver=material(0xced4d7,.25),dark=material(0x59636d,.37),steel=material(0x929ba3,.3),warm=material(0x9c8271,.42),nickel=material(0xa8a399,.32),shell=material(0xaab5c0,.34,.8,true),shellDark=material(0x4f5c67,.4,.85,true),liner=material(0x97826c,.5,.8,true);
   const fg=groups.fan;
   if(fan){blades(fg,-3.02,.53,2.13,24,.94,titanium,true,.3,1.05);lathe([[-4.03,0],[-3.98,.13],[-3.8,.32],[-3.5,.47],[-3.13,.54],[-2.85,.52]],silver,fg);ring(-3.1,.53,.04,dark,fg);blades(fg,-2.55,.65,2.1,36,.36,dark,false,.05,-.5);}
   else if(power){blades(groups.compressor,-2.77,.49,1.27,30,.4,titanium,true);mechanism=buildShaftOutput(kind as 'turboprop'|'turboshaft',{groups,clip,materials});}
   else{lathe([[-3.6,0],[-3.35,.25],[-2.95,.45],[-2.6,.52]],silver,fg);blades(fg,-2.77,.49,1.27,30,.4,titanium,true);}
   const cg=groups.compressor;
   lathe([[-2.7,.44],[-2.4,.57],[-1.5,.7],[-.5,.78],[.55,.83],[.75,.8]],dark,cg);
   for(let i=0;i<9;i++){const x=-2.35+i*.335,outer=1.25-i*.036,inner=.56+i*.033;blades(cg,x,inner,outer,36+i*2,.27,i%2?steel:silver,true,.035,.68);ring(x,inner,.044,steel,cg);if(i<8)blades(cg,x+.17,inner+.025,outer+.015,40+i*2,.16,dark,false,0,-.7);ring(x,outer+.035,.035,shellDark,cg);}
   const bg=groups.combustor;
   const combustionLiner=lathe([[.7,.98],[.88,1.07],[1.1,1.1],[2.1,1.03],[2.34,.91],[2.34,.85],[2.08,.97],[1.1,1.04],[.88,1.01],[.7,.92]],liner,bg);
   lathe([[.75,.53],[.95,.6],[1.9,.63],[2.3,.55]],warm,bg);ring(.9,1.09,.06,nickel,bg);ring(2.22,.97,.055,nickel,bg);
   // Injector heads and small liner perforation collars, arranged around the annulus.
   for(let i=0;i<18;i++){const a=i/18*TAU;const inj=cyl(.91,.2,.085,nickel,bg);inj.position.y=Math.sin(a)*.84;inj.position.z=Math.cos(a)*.84;pipe([new T.Vector3(.9,Math.sin(a)*.84,Math.cos(a)*.84),new T.Vector3(.68,Math.sin(a)*1.13,Math.cos(a)*1.13),new T.Vector3(.5,Math.sin(a)*1.13,Math.cos(a)*1.13)],.025,steel,bg);}
   const holeGeo=new T.CircleGeometry(.025,9),holes=new T.InstancedMesh(holeGeo,material(0x242424,.95,.1,true),240),dummy=new T.Object3D();for(let i=0;i<240;i++){const a=(i%48)/48*TAU,x=1.12+Math.floor(i/48)*.19;dummy.position.set(x,Math.sin(a)*1.078,Math.cos(a)*1.078);dummy.lookAt(x,Math.sin(a)*2,Math.cos(a)*2);dummy.updateMatrix();holes.setMatrixAt(i,dummy.matrix);}holes.userData.attachTo=combustionLiner.uuid;bg.add(holes);
   const tg=groups.turbine;lathe([[2.35,.52],[2.7,.61],[3.2,.64],[3.75,.53]],dark,tg);
   for(let i=0;i<5;i++){const x=2.38+i*.29,r=.98-i*.015;const rotor=blades(tg,x,.56,r,52,.22,i<2?warm:nickel,true,.025,.65);rotor.userData.rate=(fan||power)&&i>=2?.7:1.1;ring(x,.58,.065,steel,tg);if(i<4)blades(tg,x+.16,.58,r,48,.13,dark,false,0,-.6);ring(x,r+.07,.035,shellDark,tg);}
   const ng=groups.nozzle;
   if(power){lathe([[3.78,1.03],[4.3,1.03],[4.3,.97],[3.78,.97]],shellDark,ng);for(const side of (kind==='turboprop'?[-1,1]:[1]))pipe([new T.Vector3(4.0,0,0),new T.Vector3(4.3,0,side*.8),new T.Vector3(4.4,.2,side*1.65)],.38,warm,ng);ring(3.84,1.02,.05,steel,ng);bolts(ng,3.84,1.04,36,silver);}
   else {lathe([[3.78,1.03],[4.1,1],[4.7,.81],[5.1,.64],[5.1,.59],[4.7,.76],[4.1,.95],[3.78,.98]],shellDark,ng);lathe([[3.65,.48],[3.9,.46],[4.35,.32],[4.85,.04],[4.9,0]],nickel,ng);ring(3.84,1.02,.05,steel,ng);bolts(ng,3.84,1.04,36,silver);}

   const sg=groups.shaft;cyl(.05,7.1,.13,silver,sg);if(fan||power)cyl(.62,5.1,.205,dark,sg);[-2.64,.58,3.71].forEach(x=>{ring(x,.25,.065,silver,sg);blades(sg,x,.25,.5,8,.16,dark,false,0,0);});
   const casing=groups.casing;
   if(fan){lathe([[-3.62,2.21],[-3.67,2.29],[-3.57,2.36],[-3.32,2.38],[-2.6,2.34],[-1.6,2.2],[.2,1.92],[1.2,1.67],[1.2,1.6],[.2,1.85],[-1.6,2.13],[-2.6,2.27],[-3.32,2.3],[-3.5,2.28],[-3.62,2.21]],shell,casing);[-3.25,-2.5,-1.2,.5].forEach((x,i)=>{ring(x,[2.35,2.32,2.14,1.85][i],.035,shellDark,casing);bolts(casing,x,[2.35,2.32,2.14,1.85][i],48,shellDark);});}
   else if(power)lathe([[-2.8,1.32],[-2.5,1.32],[-2.5,1.25],[-2.8,1.25]],shell,casing);
   else lathe([[-3.6,1.32],[-3.65,1.39],[-3.4,1.45],[-2.8,1.38],[-2.5,1.32],[-2.5,1.26],[-3.4,1.38],[-3.6,1.32]],shell,casing);
   lathe([[-2.5,1.3],[-1.5,1.22],[.6,1.13],[.85,1.19],[2.2,1.13],[2.4,1.1],[3.8,1.09],[3.8,1.03],[2.4,1.04],[2.2,1.07],[.85,1.13],[.6,1.07],[-1.5,1.16],[-2.5,1.24]],shell,casing);
   [-2.4,-.2,.7,2.2,3.75].forEach((x,i)=>{const r=[1.3,1.17,1.15,1.14,1.09][i];ring(x,r,.06,shellDark,casing);bolts(casing,x,r,40,shellDark);});
   for(let i=0;i<8;i++){const a=i/8*TAU+.1,pts=[-.4,.3,1.1,2,2.5].map((x,j)=>new T.Vector3(x,Math.sin(a)*[1.22,1.2,1.28,1.24,1.17][j],Math.cos(a)*[1.22,1.2,1.28,1.24,1.17][j]));pipe(pts,.018,shellDark,casing);}
   
 let meshIndex=0,serial=0;
 root.traverse(o=>{if(o instanceof T.Mesh){
   let p:T.Object3D|null=o;while(p&&!p.userData.id)p=p.parent;
   o.userData.part=p?.userData.id;
   o.userData.sourceMeshIndex=meshIndex++;
   o.userData.upstreamFirstPieceSerial=serial;
   serial+=o instanceof T.InstancedMesh?o.count:1;
 }});
 root.updateMatrixWorld(true);
 return {root,groups,rotors,materials,triangles};
}
