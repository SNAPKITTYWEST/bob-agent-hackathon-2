"use strict";
// =============================================================
// SIMS RENDERER — Three.js bridge for the Humanoid Engine
// =============================================================
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { OBJECT_DEFS, WALK_SPEED, RUN_SPEED } from "./sims-engine.js";

const TAU = Math.PI * 2;

// ── Scene setup ───────────────────────────────────────────────
export function createScene(canvas){
  const renderer = new THREE.WebGLRenderer({ canvas, antialias:true });
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type    = THREE.PCFSoftShadowMap;
  renderer.toneMapping       = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1a2035);
  scene.fog = new THREE.Fog(0x1a2035, 28, 60);

  const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 200);
  camera.position.set(0, 14, 18);

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true; controls.dampingFactor = 0.06;
  controls.target.set(0,1,0); controls.update();

  // Lights
  scene.add(new THREE.HemisphereLight(0xd0e8ff, 0x1a1a2e, 0.9));
  const sun = new THREE.DirectionalLight(0xfff4e0, 1.5);
  sun.position.set(12,18,10); sun.castShadow=true;
  sun.shadow.mapSize.set(2048,2048);
  sun.shadow.camera.left=-20; sun.shadow.camera.right=20;
  sun.shadow.camera.top=20;   sun.shadow.camera.bottom=-20;
  scene.add(sun);
  const rim = new THREE.DirectionalLight(0x3488ee, 0.4);
  rim.position.set(-8,6,-10); scene.add(rim);

  // Ground
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(64,64),
    new THREE.MeshStandardMaterial({ color:0x2d4a3e, roughness:0.85, metalness:0.0 })
  );
  ground.rotation.x = -Math.PI/2; ground.receiveShadow=true; scene.add(ground);

  // Grid subtle
  scene.add(new THREE.GridHelper(64,64,0x2a3a52,0x2a3a52));

  return { renderer, scene, camera, controls };
}

// ── Object mesh builder ───────────────────────────────────────
export function buildObjectMesh(obj){
  const def = obj.def;
  const mat = new THREE.MeshStandardMaterial({ color:def.color, roughness:0.7, metalness:0.05 });
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(def.w, def.h, def.d), mat);
  mesh.position.set(obj.pos.x, obj.pos.y + def.h/2, obj.pos.z);
  mesh.castShadow = true; mesh.receiveShadow = true;
  mesh.userData.objectId = obj.id;

  // Interaction point indicator
  const ip = obj.interactPoint();
  const marker = new THREE.Mesh(
    new THREE.CircleGeometry(0.18,8),
    new THREE.MeshBasicMaterial({ color:0xffd166, transparent:true, opacity:0.55, depthWrite:false })
  );
  marker.rotation.x=-Math.PI/2; marker.position.set(ip.x, 0.01, ip.z);
  marker.userData.isMarker=true;
  const group = new THREE.Group();
  group.add(mesh); group.add(marker);
  return group;
}

// ── Humanoid mesh builder ─────────────────────────────────────
// Returns an object with named Three.js meshes matching skeleton bones
export function buildHumanoidMesh(color, accentColor){
  const c  = new THREE.Color(color);
  const ac = new THREE.Color(accentColor || color);
  const body = (col, rough=0.55)=> new THREE.MeshStandardMaterial({
    color:col, emissive:col, emissiveIntensity:0.06, roughness:rough, metalness:0.1
  });
  const white = new THREE.MeshStandardMaterial({ color:0xffffff, roughness:0.3 });
  const black = new THREE.MeshBasicMaterial({ color:0x080808 });
  const clothes = new THREE.MeshStandardMaterial({ color:accentColor||0x334466, roughness:0.8, metalness:0 });

  const root = new THREE.Group();

  // — Torso/spine group
  const spine = new THREE.Group(); root.add(spine);
  const torsoMesh = new THREE.Mesh(new THREE.BoxGeometry(0.5,0.54,0.26), clothes);
  torsoMesh.position.y = 0.27; torsoMesh.castShadow=true; spine.add(torsoMesh);

  // — Hips (connects torso & legs)
  const hips = new THREE.Group(); hips.position.y=0; spine.add(hips);
  const hipMesh = new THREE.Mesh(new THREE.BoxGeometry(0.46,0.26,0.24), body(c));
  hipMesh.position.y=0.13; hipMesh.castShadow=true; hips.add(hipMesh);

  // — Upper legs
  const ulL = new THREE.Group(); ulL.position.set(-0.13,0,0); hips.add(ulL);
  const ulR = new THREE.Group(); ulR.position.set( 0.13,0,0); hips.add(ulR);
  const upperLegGeo = new THREE.CylinderGeometry(0.1,0.09,0.42,8);
  const ulLm = new THREE.Mesh(upperLegGeo, body(c)); ulLm.position.y=-0.21; ulLm.castShadow=true; ulL.add(ulLm);
  const ulRm = new THREE.Mesh(upperLegGeo, body(c)); ulRm.position.y=-0.21; ulRm.castShadow=true; ulR.add(ulRm);

  // — Lower legs + feet
  const llL = new THREE.Group(); llL.position.y=-0.42; ulL.add(llL);
  const llR = new THREE.Group(); llR.position.y=-0.42; ulR.add(llR);
  const lowerLegGeo = new THREE.CylinderGeometry(0.085,0.075,0.4,8);
  const footGeo = new THREE.BoxGeometry(0.12,0.07,0.22);
  [llL,llR].forEach(ll=>{
    const m = new THREE.Mesh(lowerLegGeo, body(c)); m.position.y=-0.2; m.castShadow=true; ll.add(m);
    const f = new THREE.Mesh(footGeo, body(c,0.8)); f.position.set(0,-0.42,0.06); f.castShadow=true; ll.add(f);
  });

  // — Neck group (above torso)
  const neckGroup = new THREE.Group(); neckGroup.position.y=0.54; spine.add(neckGroup);
  const neckMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.09,0.10,0.15,8), body(c));
  neckMesh.position.y=0.075; neckGroup.add(neckMesh);

  // — Head
  const headGroup = new THREE.Group(); headGroup.position.y=0.15; neckGroup.add(headGroup);
  const headMesh = new THREE.Mesh(new THREE.SphereGeometry(0.22,12,10), body(c));
  headMesh.position.y=0.22; headMesh.castShadow=true; headGroup.add(headMesh);

  // Cat ears
  const earGeo = new THREE.ConeGeometry(0.075,0.18,6);
  const earL = new THREE.Mesh(earGeo, body(c)); earL.position.set(-0.13,0.46,0); earL.rotation.z=-0.22; headGroup.add(earL);
  const earR = new THREE.Mesh(earGeo, body(c)); earR.position.set( 0.13,0.46,0); earR.rotation.z= 0.22; headGroup.add(earR);

  // Eyes
  [-0.09,0.09].forEach(x=>{
    const e = new THREE.Mesh(new THREE.SphereGeometry(0.048,8,8), white); e.position.set(x,0.24,0.19); headGroup.add(e);
    const p = new THREE.Mesh(new THREE.SphereGeometry(0.032,8,8), black); p.position.set(x,0.24,0.22); headGroup.add(p);
    // Shine
    const s = new THREE.Mesh(new THREE.SphereGeometry(0.012,6,6),
      new THREE.MeshBasicMaterial({color:0xffffff})); s.position.set(x+0.014,0.254,0.236); headGroup.add(s);
  });

  // Nose
  const nose = new THREE.Mesh(new THREE.SphereGeometry(0.018,6,6),
    new THREE.MeshBasicMaterial({color:0xff8fab})); nose.position.set(0,0.19,0.215); headGroup.add(nose);

  // — Upper arms
  const uaL = new THREE.Group(); uaL.position.set(-0.3,0.46,0); spine.add(uaL);
  const uaR = new THREE.Group(); uaR.position.set( 0.3,0.46,0); spine.add(uaR);
  const upperArmGeo = new THREE.CylinderGeometry(0.075,0.07,0.36,8);
  const uaLm = new THREE.Mesh(upperArmGeo, clothes); uaLm.position.y=-0.18; uaLm.castShadow=true; uaL.add(uaLm);
  const uaRm = new THREE.Mesh(upperArmGeo, clothes); uaRm.position.y=-0.18; uaRm.castShadow=true; uaR.add(uaRm);

  // — Lower arms + hands
  const laL = new THREE.Group(); laL.position.y=-0.36; uaL.add(laL);
  const laR = new THREE.Group(); laR.position.y=-0.36; uaR.add(laR);
  const lowerArmGeo = new THREE.CylinderGeometry(0.065,0.055,0.32,8);
  const handGeo = new THREE.SphereGeometry(0.065,7,7);
  [laL,laR].forEach(la=>{
    const m = new THREE.Mesh(lowerArmGeo, body(c)); m.position.y=-0.16; m.castShadow=true; la.add(m);
    const h = new THREE.Mesh(handGeo, body(c)); h.position.y=-0.34; h.castShadow=true; la.add(h);
  });

  // — Tail
  const tailGroup = new THREE.Group(); tailGroup.position.set(-0.02,0.22,-0.14); spine.add(tailGroup);
  const tailMesh  = new THREE.Mesh(
    new THREE.TorusGeometry(0.24,0.046,7,18,Math.PI*1.15), body(c));
  tailMesh.rotation.x=0.5; tailMesh.rotation.y=0.3; tailGroup.add(tailMesh);

  // — Selection ring (hidden by default)
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(0.38,0.46,24),
    new THREE.MeshBasicMaterial({color:0xffd166, transparent:true, opacity:0.8, side:THREE.DoubleSide, depthWrite:false})
  );
  ring.rotation.x=-Math.PI/2; ring.position.y=0.01; ring.visible=false; root.add(ring);

  // Name label (canvas texture)
  root.userData.ring = ring;

  return {
    root, spine, neckGroup, headGroup,
    upperArmL:uaL, upperArmR:uaR,
    lowerArmL:laL, lowerArmR:laR,
    upperLegL:ulL, upperLegR:ulR,
    lowerLegL:llL, lowerLegR:llR,
    tailGroup
  };
}

// ── Apply skeleton to mesh rig ────────────────────────────────
export function applySkeleton(rig, sk){
  const b = sk.bones;
  rig.spine.rotation.x     = b.spine.rx;
  rig.spine.rotation.y     = b.spine.ry||0;
  rig.neckGroup.rotation.x = b.neck.rx||0;
  rig.headGroup.rotation.x = b.head.rx;
  rig.headGroup.rotation.y = b.head.ry||0;
  rig.upperArmL.rotation.x = b.upperArmL.rx; rig.upperArmL.rotation.z = 0.35+(b.upperArmL.rz||0);
  rig.upperArmR.rotation.x = b.upperArmR.rx; rig.upperArmR.rotation.z = -(0.35+(b.upperArmR.rz||0));
  rig.lowerArmL.rotation.x = b.lowerArmL.rx;
  rig.lowerArmR.rotation.x = b.lowerArmR.rx;
  rig.upperLegL.rotation.x = b.upperLegL.rx;
  rig.upperLegR.rotation.x = b.upperLegR.rx;
  rig.lowerLegL.rotation.x = b.lowerLegL.rx;
  rig.lowerLegR.rotation.x = b.lowerLegR.rx;
  rig.tailGroup.rotation.z = b.tail.rz;
  rig.tailGroup.rotation.x = b.tail.rx||0;
  rig.root.position.y      = b.root.ty||0;
}

// ── Speech bubble (DOM overlay) ───────────────────────────────
export function createBubble(parent){
  const el = document.createElement('div');
  el.style.cssText=`position:absolute;background:rgba(255,255,255,0.93);color:#111;
    padding:5px 9px;border-radius:8px;font:12px/1.4 "Segoe UI",sans-serif;
    max-width:160px;pointer-events:none;border:1.5px solid #ccc;display:none;
    box-shadow:0 2px 8px rgba(0,0,0,0.3)`;
  parent.appendChild(el);
  return el;
}

export function updateBubblePos(el, worldPos, camera, renderer, viewportEl){
  const v = worldPos.clone().project(camera);
  const rect = viewportEl.getBoundingClientRect();
  const x = (v.x*0.5+0.5)*rect.width;
  const y = (-v.y*0.5+0.5)*rect.height;
  el.style.left=(x-el.offsetWidth/2)+'px';
  el.style.top =(y-el.offsetHeight-8)+'px';
}

// ── Needs bar HUD ─────────────────────────────────────────────
export function renderNeedsHUD(el, char){
  if(!char){ el.style.display='none'; return; }
  el.style.display='block';
  const needs = char.needs;
  const bar=(v,col)=>`<div style="display:flex;align-items:center;gap:6px;margin:3px 0">
    <span style="width:52px;font-size:11px;color:#aaa">${col.label}</span>
    <div style="flex:1;height:10px;background:#222;border-radius:4px;overflow:hidden">
      <div style="width:${v.toFixed(0)}%;height:100%;background:${col.color};transition:width 0.4s"></div>
    </div>
    <span style="font-size:10px;width:28px;text-align:right">${v.toFixed(0)}</span>
  </div>`;
  el.innerHTML=`<div style="font-weight:700;margin-bottom:6px;color:#fff">${char.name}</div>`+
    `<div style="font-size:11px;color:#888;margin-bottom:6px">${char.animState.toUpperCase()}</div>`+
    bar(needs.hunger,  {label:'Hunger', color:'#e63946'})+
    bar(needs.energy,  {label:'Energy', color:'#ffb703'})+
    bar(needs.social,  {label:'Social', color:'#22b8cf'})+
    bar(needs.fun,     {label:'Fun',    color:'#60d394'});
}

// ── Quantum voxel overlay ─────────────────────────────────────
const QC=[0x00ffff,0xff00ff,0xffff00,0x00ff00,0xff0000,0x0000ff,0xffffff,0x888888];
export function buildQuantumOverlay(){
  const g=new THREE.Group();
  const geo=new THREE.BoxGeometry(0.18,0.18,0.18);
  for(let x=0;x<3;x++) for(let y=0;y<3;y++) for(let z=0;z<3;z++){
    const m=new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
      color:QC[(x+y*3+z*9)%8], transparent:true, opacity:0.55, depthWrite:false
    }));
    m.position.set((x-1)*0.22,(y-1)*0.22,(z-1)*0.22); g.add(m);
  }
  return g;
}

// ── Raycasting helper ─────────────────────────────────────────
export function pickCharacter(e, canvas, camera, rigMap){
  const rect=canvas.getBoundingClientRect();
  const ptr=new THREE.Vector2(
    ((e.clientX-rect.left)/rect.width)*2-1,
    -((e.clientY-rect.top)/rect.height)*2+1
  );
  const rc=new THREE.Raycaster();
  rc.setFromCamera(ptr,camera);
  const meshes=[];
  for(const [id,rig] of rigMap) rig.root.traverse(c=>{if(c.isMesh)meshes.push(c);});
  const hits=rc.intersectObjects(meshes);
  if(!hits.length) return null;
  for(const [id,rig] of rigMap){
    let found=false; rig.root.traverse(c=>{if(c===hits[0].object)found=true;});
    if(found) return id;
  }
  return null;
}

export function pickGround(e, canvas, camera, groundMesh){
  const rect=canvas.getBoundingClientRect();
  const ptr=new THREE.Vector2(
    ((e.clientX-rect.left)/rect.width)*2-1,
    -((e.clientY-rect.top)/rect.height)*2+1
  );
  const rc=new THREE.Raycaster();
  rc.setFromCamera(ptr,camera);
  const hits=rc.intersectObject(groundMesh);
  if(!hits.length) return null;
  const p=hits[0].point;
  return {x:p.x, y:0, z:p.z};
}

export function pickObject(e, canvas, camera, objMeshes){
  const rect=canvas.getBoundingClientRect();
  const ptr=new THREE.Vector2(
    ((e.clientX-rect.left)/rect.width)*2-1,
    -((e.clientY-rect.top)/rect.height)*2+1
  );
  const rc=new THREE.Raycaster();
  rc.setFromCamera(ptr,camera);
  const allMeshes=[];
  for(const [id,mesh] of objMeshes) mesh.traverse(c=>{if(c.isMesh&&!c.userData.isMarker){c.userData._objId=id; allMeshes.push(c);}});
  const hits=rc.intersectObjects(allMeshes);
  if(!hits.length) return null;
  return hits[0].object.userData._objId;
}
