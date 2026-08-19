"use strict";
// =============================================================
// HUMANOID ENGINE — Embodiment First
// Spawn → Select → Walk → Collide → Navigate → Interact → AI
// =============================================================

export const TICK = 1 / 60;
export const WALK_SPEED = 2.8;
export const RUN_SPEED  = 6.0;
export const TURN_SPEED = 4.2;
export const GRAVITY    = -14;

// ── Vec3 ──────────────────────────────────────────────────────
export class Vec3 {
  constructor(x=0,y=0,z=0){ this.x=x; this.y=y; this.z=z; }
  clone(){ return new Vec3(this.x,this.y,this.z); }
  add(v){ return new Vec3(this.x+v.x,this.y+v.y,this.z+v.z); }
  sub(v){ return new Vec3(this.x-v.x,this.y-v.y,this.z-v.z); }
  scale(s){ return new Vec3(this.x*s,this.y*s,this.z*s); }
  len(){ return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z); }
  lenXZ(){ return Math.sqrt(this.x*this.x+this.z*this.z); }
  normXZ(){
    const l=this.lenXZ();
    return l>0.001 ? new Vec3(this.x/l,0,this.z/l) : new Vec3(0,0,0);
  }
  distXZ(v){ return Math.sqrt((this.x-v.x)**2+(this.z-v.z)**2); }
  copy(v){ this.x=v.x; this.y=v.y; this.z=v.z; return this; }
}

// ── Needs ─────────────────────────────────────────────────────
const NEED_DECAY = { hunger:2.4, energy:1.8, social:1.2, fun:0.9 };
export class Needs {
  constructor(){ this.hunger=100; this.energy=100; this.social=100; this.fun=100; }
  tick(dt){
    for(const k of Object.keys(NEED_DECAY)){
      this[k]=Math.max(0, this[k]-NEED_DECAY[k]*dt);
    }
  }
  mostUrgent(){
    let worst=null, min=101;
    for(const k of Object.keys(NEED_DECAY)) if(this[k]<min){ min=this[k]; worst=k; }
    return worst;
  }
}

// ── World Objects ─────────────────────────────────────────────
export const OBJECT_DEFS = {
  bed:      { color:0x8ecae6, w:1.4, h:0.55, d:2.0, interactOffset:new Vec3(0,0,1.2),  interactAngle:0,   action:'sleep',  needsTarget:'energy' },
  fridge:   { color:0xe0e0e0, w:0.8, h:1.9, d:0.7,  interactOffset:new Vec3(0,0,0.8),  interactAngle:0,   action:'eat',    needsTarget:'hunger' },
  sofa:     { color:0xd4a373, w:1.8, h:0.75,d:0.9,  interactOffset:new Vec3(0,0,0.9),  interactAngle:0,   action:'sit',    needsTarget:'fun'    },
  computer: { color:0x333333, w:0.6, h:1.1, d:0.5,  interactOffset:new Vec3(0,0,0.8),  interactAngle:0,   action:'browse', needsTarget:'fun'    },
  table:    { color:0xa0785a, w:1.2, h:0.75,d:0.8,  interactOffset:new Vec3(0,0,0.8),  interactAngle:0,   action:'sit',    needsTarget:'social' },
  door:     { color:0xc8956c, w:0.9, h:2.1, d:0.1,  interactOffset:new Vec3(0,0,0.6),  interactAngle:0,   action:'open',   needsTarget:null     },
  tree:     { color:0x2d6a4f, w:0.8, h:2.4, d:0.8,  interactOffset:new Vec3(0,0,1.0),  interactAngle:0,   action:'idle',   needsTarget:'fun'    },
};

let _eid = 1;
export class WorldObject {
  constructor(type, pos){
    this.id    = _eid++;
    this.type  = type;
    this.pos   = pos.clone();
    const def  = OBJECT_DEFS[type];
    this.def   = def;
    this.state = 'free';    // free | occupied
    this.occupant = null;
  }
  interactPoint(){
    const off = this.def.interactOffset;
    return new Vec3(this.pos.x+off.x, this.pos.y, this.pos.z+off.z);
  }
  halfExtents(){ const d=this.def; return new Vec3(d.w/2, d.h/2, d.d/2); }
}

// ── A* on a flat nav grid ─────────────────────────────────────
const CELL = 0.5; // nav grid resolution
export class NavGrid {
  constructor(wx, wz, obstacles){
    this.wx = wx; this.wz = wz;
    this.cx = Math.ceil(wx/CELL); this.cz = Math.ceil(wz/CELL);
    this.blocked = new Uint8Array(this.cx*this.cz);
    for(const ob of obstacles) this._blockObject(ob);
  }
  _idx(cx,cz){ return cz*this.cx+cx; }
  _world2cell(x,z){
    return [Math.floor((x+this.wx/2)/CELL), Math.floor((z+this.wz/2)/CELL)];
  }
  _cell2world(cx,cz){
    return new Vec3((cx+0.5)*CELL-this.wx/2, 0, (cz+0.5)*CELL-this.wz/2);
  }
  _blockObject(ob){
    const he = ob.halfExtents();
    const [cx0,cz0]=this._world2cell(ob.pos.x-he.x-0.15, ob.pos.z-he.z-0.15);
    const [cx1,cz1]=this._world2cell(ob.pos.x+he.x+0.15, ob.pos.z+he.z+0.15);
    for(let cz=Math.max(0,cz0);cz<=Math.min(this.cz-1,cz1);cz++)
      for(let cx=Math.max(0,cx0);cx<=Math.min(this.cx-1,cx1);cx++)
        this.blocked[this._idx(cx,cz)]=1;
  }
  findPath(from, to){
    const [sx,sz]=this._world2cell(from.x,from.z);
    const [ex,ez]=this._world2cell(to.x,  to.z  );
    if(sx===ex&&sz===ez) return [to.clone()];
    const h=(cx,cz)=>Math.abs(cx-ex)+Math.abs(cz-ez);
    const key=(cx,cz)=>cz*this.cx+cx;
    const open=new Map(), closed=new Set();
    const g=new Map(), par=new Map();
    open.set(key(sx,sz),{cx:sx,cz:sz,f:h(sx,sz)});
    g.set(key(sx,sz),0);
    const dirs=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]];
    for(let iter=0;iter<4000&&open.size;iter++){
      // pop lowest f
      let best=null, bestF=Infinity;
      for(const [k,n] of open){ if(n.f<bestF){bestF=n.f;best=k;} }
      const {cx,cz}=open.get(best); open.delete(best); closed.add(best);
      if(cx===ex&&cz===ez){
        // reconstruct
        const path=[this._cell2world(cx,cz)];
        let cur=best;
        while(par.has(cur)){ cur=par.get(cur); path.unshift(this._cell2world(cur%this.cx, (cur/this.cx)|0)); }
        path.push(to.clone());
        return path;
      }
      for(const [dx,dz] of dirs){
        const nx=cx+dx, nz=cz+dz;
        if(nx<0||nx>=this.cx||nz<0||nz>=this.cz) continue;
        if(this.blocked[this._idx(nx,nz)]) continue;
        const nk=key(nx,nz); if(closed.has(nk)) continue;
        const ng=(g.get(best)||0)+(dx&&dz?1.4:1);
        if(!g.has(nk)||ng<g.get(nk)){
          g.set(nk,ng); par.set(nk,best);
          open.set(nk,{cx:nx,cz:nz,f:ng+h(nx,nz)});
        }
      }
    }
    return [to.clone()]; // fallback straight line
  }
}

// ── Skeleton rig (procedural bone transforms) ─────────────────
export class Skeleton {
  constructor(){
    this.bones = {
      root:{rx:0,ry:0,tx:0,ty:0}, spine:{rx:0,ry:0},
      head:{rx:0,ry:0}, neck:{rx:0},
      upperArmL:{rx:0,rz:0}, lowerArmL:{rx:0},
      upperArmR:{rx:0,rz:0}, lowerArmR:{rx:0},
      upperLegL:{rx:0},      lowerLegL:{rx:0},
      upperLegR:{rx:0},      lowerLegR:{rx:0},
      tail:{rx:0,rz:0}
    };
  }
  applyIdle(t){
    const s=Math.sin, b=s(t*2.1)*0.012;
    this.bones.root.ty=b;
    this.bones.spine.rx=s(t*1.0)*0.03;
    this.bones.head.rx=s(t*0.9)*0.02;
    this.bones.upperArmL.rx=s(t*1.1)*0.04; this.bones.upperArmR.rx=-s(t*1.1)*0.04;
    this.bones.tail.rz=s(t*1.8)*0.18;
    this.bones.upperLegL.rx=0; this.bones.upperLegR.rx=0;
    this.bones.lowerLegL.rx=0; this.bones.lowerLegR.rx=0;
  }
  applyWalk(t, speed){
    const s=Math.sin, ph=t*speed*4.5;
    this.bones.spine.rx=s(ph)*0.06; this.bones.spine.ry=s(ph)*0.04;
    this.bones.head.ry=-s(ph)*0.03;
    this.bones.upperArmL.rx= s(ph+Math.PI)*0.55; this.bones.lowerArmL.rx=Math.max(0,s(ph+Math.PI))*0.3;
    this.bones.upperArmR.rx= s(ph)*0.55;          this.bones.lowerArmR.rx=Math.max(0,s(ph))*0.3;
    this.bones.upperLegL.rx= s(ph)*0.65;          this.bones.lowerLegL.rx=Math.max(0,-s(ph))*0.5;
    this.bones.upperLegR.rx= s(ph+Math.PI)*0.65;  this.bones.lowerLegR.rx=Math.max(0,-s(ph+Math.PI))*0.5;
    this.bones.root.ty=Math.abs(s(ph))*0.04-0.02;
    this.bones.tail.rz=s(ph+Math.PI)*0.25;
  }
  applyRun(t, speed){
    const s=Math.sin, ph=t*speed*5.5;
    this.bones.spine.rx=0.08+s(ph)*0.08;
    this.bones.upperArmL.rx= s(ph+Math.PI)*0.85; this.bones.lowerArmL.rx=Math.max(0,s(ph+Math.PI))*0.55;
    this.bones.upperArmR.rx= s(ph)*0.85;          this.bones.lowerArmR.rx=Math.max(0,s(ph))*0.55;
    this.bones.upperLegL.rx= s(ph)*0.95;          this.bones.lowerLegL.rx=Math.max(0,-s(ph))*0.7;
    this.bones.upperLegR.rx= s(ph+Math.PI)*0.95;  this.bones.lowerLegR.rx=Math.max(0,-s(ph+Math.PI))*0.7;
    this.bones.root.ty=Math.abs(s(ph))*0.07-0.035;
    this.bones.tail.rz=s(ph+Math.PI)*0.38; this.bones.tail.rx=0.22;
  }
  applySit(t){
    this.bones.upperLegL.rx=1.4; this.bones.upperLegR.rx=1.4;
    this.bones.lowerLegL.rx=-1.5; this.bones.lowerLegR.rx=-1.5;
    this.bones.spine.rx=-0.15;
    this.bones.tail.rz=Math.sin(t*1.2)*0.12;
  }
  applySleep(t){
    this.bones.root.rx=1.5; this.bones.head.rx=0.4;
    this.bones.upperLegL.rx=0.6; this.bones.upperLegR.rx=0.6;
    this.bones.spine.rx=Math.sin(t*0.6)*0.04;
  }
  applyInteract(t){
    this.bones.upperArmR.rx=-1.1; this.bones.lowerArmR.rx=0.6;
    this.bones.head.rx=-0.1; this.bones.spine.rx=0.08;
    this.bones.upperArmL.rx=Math.sin(t*3)*0.1;
  }
}

// ── CharacterController ───────────────────────────────────────
export const ANIM_STATES = ['idle','walk','run','sit','sleep','interact'];
export class CharacterController {
  constructor(id, name, color, pos){
    this.id        = id;
    this.name      = name;
    this.color     = color;
    this.pos       = pos.clone();
    this.vel       = new Vec3();
    this.yRot      = 0;       // facing radians
    this.speed     = 0;
    this.onGround  = true;
    this.vy        = 0;
    this.animState = 'idle';
    this.animTime  = 0;
    this.skeleton  = new Skeleton();
    this.needs     = new Needs();
    this.path      = [];
    this.pathTarget= null;
    this.interactingWith = null;
    this.interactTimer   = 0;
    this.selected  = false;
    this.home      = null;    // WorldObject ref
    this.memory    = [];      // {t, event}
    this.aiController = null; // optional
    this.thinkTimer= 0;
  }

  // Called by input or AI
  setMoveDir(dx, dz, wantRun=false){
    const len = Math.sqrt(dx*dx+dz*dz);
    if(len<0.001){ this.vel.x=0; this.vel.z=0; this.speed=0; return; }
    const nx=dx/len, nz=dz/len;
    const spd = wantRun ? RUN_SPEED : WALK_SPEED;
    this.vel.x = nx*spd; this.vel.z = nz*spd; this.speed = spd;
    this.yRot = Math.atan2(nx, nz);
  }

  stopMoving(){ this.vel.x=0; this.vel.z=0; this.speed=0; }

  navigateTo(target, nav){
    this.path = nav.findPath(this.pos, target);
    this.pathTarget = target.clone();
    this.interactingWith = null;
  }

  tickPath(){
    if(!this.path.length){ this.stopMoving(); return; }
    const next = this.path[0];
    const dx = next.x - this.pos.x, dz = next.z - this.pos.z;
    const d  = Math.sqrt(dx*dx+dz*dz);
    if(d < 0.22){ this.path.shift(); if(!this.path.length) this.stopMoving(); return; }
    this.setMoveDir(dx, dz, d > 4);
  }

  startInteract(obj){
    this.interactingWith = obj;
    this.interactTimer   = 0;
    obj.state    = 'occupied';
    obj.occupant = this;
    this.path    = [];
    this.stopMoving();
    this.animState = obj.def.action === 'sleep' ? 'sleep' : obj.def.action === 'sit' ? 'sit' : 'interact';
  }

  tickInteract(dt){
    if(!this.interactingWith) return;
    this.interactTimer += dt;
    const dur = this.interactingWith.def.action === 'sleep' ? 8 : 4;
    if(this.interactTimer >= dur){
      // restore need
      const nt = this.interactingWith.def.needsTarget;
      if(nt) this.needs[nt] = Math.min(100, this.needs[nt]+55);
      this.memory.push({t: this.animTime, event:`used ${this.interactingWith.type}`});
      this.interactingWith.state   = 'free';
      this.interactingWith.occupant= null;
      this.interactingWith = null;
      this.animState = 'idle';
    }
  }

  tick(dt, nav, objects){
    this.animTime += dt;
    this.needs.tick(dt);

    // AI think
    if(this.aiController && !this.interactingWith && !this.path.length){
      this.thinkTimer -= dt;
      if(this.thinkTimer <= 0){
        this.aiController.think(this, objects, nav);
        this.thinkTimer = 1.5 + Math.random();
      }
    }

    // Path follow
    if(this.path.length) this.tickPath();

    // Interaction
    this.tickInteract(dt);

    // Physics
    if(!this.onGround){ this.vy += GRAVITY*dt; }
    this.pos.x += this.vel.x*dt;
    this.pos.z += this.vel.z*dt;
    this.pos.y += this.vy*dt;
    if(this.pos.y <= 0){ this.pos.y=0; this.vy=0; this.onGround=true; }

    // Smooth facing
    if(this.speed>0.1){
      let diff = this.yRot - this._smoothRot;
      while(diff>Math.PI) diff-=Math.PI*2; while(diff<-Math.PI) diff+=Math.PI*2;
      this._smoothRot += diff * Math.min(1, TURN_SPEED*dt);
    }

    // Animation state from speed
    if(!this.interactingWith){
      if(this.speed >= RUN_SPEED-0.1)       this.animState='run';
      else if(this.speed >= WALK_SPEED-0.1) this.animState='walk';
      else                                   this.animState='idle';
    }

    // Apply skeleton
    const sk = this.skeleton;
    if(this.animState==='idle')     sk.applyIdle(this.animTime);
    else if(this.animState==='walk')sk.applyWalk(this.animTime, this.speed);
    else if(this.animState==='run') sk.applyRun(this.animTime, this.speed);
    else if(this.animState==='sit') sk.applySit(this.animTime);
    else if(this.animState==='sleep')sk.applySleep(this.animTime);
    else if(this.animState==='interact')sk.applyInteract(this.animTime);
  }

  _smoothRot = 0;
}

// ── AI Controller ──────────────────────────────────────────────
export class BasicAI {
  think(char, objects, nav){
    if(char.interactingWith) return;
    const urgent = char.needs.mostUrgent();
    const targets = objects.filter(o=> o.def.needsTarget===urgent && o.state==='free');
    if(!targets.length){
      // wander
      const wx=(Math.random()-0.5)*14, wz=(Math.random()-0.5)*14;
      char.navigateTo(new Vec3(wx,0,wz), nav);
      return;
    }
    // nearest
    targets.sort((a,b)=>char.pos.distXZ(a.pos)-char.pos.distXZ(b.pos));
    const obj = targets[0];
    const ip  = obj.interactPoint();
    const path = nav.findPath(char.pos, ip);
    char.path = path;
    char.pathTarget = ip.clone();
    // hook: when path done, interact
    char._pendingInteract = obj;
  }
}

// ── World ──────────────────────────────────────────────────────
export class World {
  constructor(wx=32, wz=32){
    this.wx = wx; this.wz = wz;
    this.objects    = [];
    this.characters = [];
    this.nav        = null;
    this.t          = 0;
    this._selectedId = null;
  }
  addObject(type, pos){ const o=new WorldObject(type,pos); this.objects.push(o); return o; }
  spawnCharacter(name, color, pos, withAI=true){
    const c = new CharacterController(_eid++, name, color, pos);
    if(withAI) c.aiController = new BasicAI();
    this.characters.push(c);
    return c;
  }
  buildNav(){
    this.nav = new NavGrid(this.wx, this.wz, this.objects);
  }
  get selected(){ return this.characters.find(c=>c.id===this._selectedId)||null; }
  select(id){ this._selectedId=id; this.characters.forEach(c=>c.selected=(c.id===id)); }
  tick(dt){
    this.t += dt;
    for(const c of this.characters){
      c.tick(dt, this.nav, this.objects);
      // check if reached pending interact
      if(c._pendingInteract && !c.path.length && !c.interactingWith){
        if(c.pos.distXZ(c._pendingInteract.interactPoint()) < 1.0){
          c.startInteract(c._pendingInteract);
          c._pendingInteract = null;
        }
      }
    }
  }
}
