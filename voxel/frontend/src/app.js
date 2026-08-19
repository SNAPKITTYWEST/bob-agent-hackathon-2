import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  ACTIONS,
  MATERIALS,
  coordinateKey,
  createInitialWorld,
  deserializeWorld,
  dispatchWorldAction,
  getVoxel,
  listAgents,
  listVoxels,
  parseCoordinateKey,
  serializeWorld,
} from "./world-model.js";

const STORAGE_KEY = "snapkitty.quantumVoxelWorld.v1";
const VOXEL_SIZE = 0.86;

let world = createInitialWorld();
let interactionMode = "select";
let selectedMaterialId = "user-placed";
let voxelGroup = new THREE.Group();
let agentGroup = new THREE.Group();
let selectionGroup = new THREE.Group();
let feedbackTimer = null;

const canvas = document.getElementById("c");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111318);
scene.fog = new THREE.Fog(0x111318, 24, 60);

const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 220);
camera.position.set(8, 8, 14);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.07;
controls.target.set(0, 0.6, 3);
controls.update();

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const textureLoader = new THREE.TextureLoader();
const textureCache = new Map();
const voxelInstanceIndex = new Map();

const voxelGeometry = new THREE.BoxGeometry(VOXEL_SIZE, VOXEL_SIZE, VOXEL_SIZE);
const markerGeometry = new THREE.CylinderGeometry(0.46, 0.46, 0.08, 18);
const selectionGeometry = new THREE.BoxGeometry(VOXEL_SIZE + 0.08, VOXEL_SIZE + 0.08, VOXEL_SIZE + 0.08);
const selectionMaterial = new THREE.MeshBasicMaterial({
  color: 0xffd166,
  wireframe: true,
  transparent: true,
  opacity: 0.9,
});

const ground = buildGround();
scene.add(ground);
scene.add(new THREE.GridHelper(34, 34, 0x3a3d46, 0x252832));
scene.add(voxelGroup);
scene.add(agentGroup);
scene.add(selectionGroup);
setupLights();
setupUi();
renderWorld();
animate();

function setupLights() {
  scene.add(new THREE.HemisphereLight(0xeaf6ff, 0x17191d, 0.85));

  const key = new THREE.DirectionalLight(0xfff1d6, 1.4);
  key.position.set(10, 14, 9);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.left = -18;
  key.shadow.camera.right = 18;
  key.shadow.camera.top = 18;
  key.shadow.camera.bottom = -18;
  scene.add(key);

  const rim = new THREE.DirectionalLight(0x32c7df, 0.55);
  rim.position.set(-10, 6, -8);
  scene.add(rim);
}

function buildGround() {
  const geometry = new THREE.PlaneGeometry(42, 42);
  const material = new THREE.MeshStandardMaterial({
    color: 0x1d2026,
    roughness: 0.62,
    metalness: 0.12,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.y = -0.5;
  mesh.receiveShadow = true;
  mesh.userData.kind = "ground";
  return mesh;
}

function setupUi() {
  document.querySelectorAll(".mode-button").forEach((button) => {
    button.addEventListener("click", () => setInteractionMode(button.dataset.mode));
  });

  document.querySelectorAll("[data-command]").forEach((button) => {
    button.addEventListener("click", () => runCommand(button.dataset.command));
  });

  canvas.addEventListener("pointerup", handleCanvasPointer);
  window.addEventListener("resize", resize);
  window.addEventListener("keydown", handleKeyboard);

  buildMaterialGrid();
  resize();
}

function buildMaterialGrid() {
  const grid = document.getElementById("material-grid");
  grid.innerHTML = "";
  const visibleMaterials = Object.values(MATERIALS).filter((material) =>
    ["qubit-one", "qubit-zero", "superposition", "gate-active", "measured", "entangled", "user-placed", "hazard"].includes(
      material.id,
    ),
  );

  for (const material of visibleMaterials) {
    const button = document.createElement("button");
    button.className = `material-swatch${material.id === selectedMaterialId ? " active" : ""}`;
    button.title = material.label;
    button.innerHTML = `
      <span class="swatch-chip" style="background:${material.color}"></span>
      <span class="swatch-label">${escapeHtml(material.label)}</span>
    `;
    button.addEventListener("click", () => {
      selectedMaterialId = material.id;
      buildMaterialGrid();
      showFeedback(`Material set to ${material.label}.`);
    });
    grid.appendChild(button);
  }
}

function setInteractionMode(mode) {
  interactionMode = mode;
  document.querySelectorAll(".mode-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === mode);
  });
  showFeedback(`Mode: ${mode}.`);
}

function runCommand(command) {
  if (command === "save") {
    localStorage.setItem(STORAGE_KEY, serializeWorld(world));
    showFeedback("World serialized to local storage.");
    return;
  }

  if (command === "load") {
    const serialized = localStorage.getItem(STORAGE_KEY);
    if (!serialized) {
      showFeedback("No saved world exists yet.", true);
      return;
    }
    world = deserializeWorld(serialized);
    renderWorld();
    showFeedback("World restored from local storage.");
    return;
  }

  const commandToAction = {
    execute: { type: ACTIONS.EXECUTE },
    measure: { type: ACTIONS.MEASURE },
    pause: { type: ACTIONS.PAUSE },
    resume: { type: ACTIONS.RESUME },
    reset: { type: ACTIONS.RESET },
  };

  if (!commandToAction[command]) return;
  world = dispatchWorldAction(world, commandToAction[command]);
  renderWorld();
  showFeedback(`${command} applied.`);
}

function handleKeyboard(event) {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
  if (event.key === "1") setInteractionMode("select");
  if (event.key === "2") setInteractionMode("place");
  if (event.key === "3") setInteractionMode("remove");
  if (event.key.toLowerCase() === "e") runCommand("execute");
  if (event.key.toLowerCase() === "m") runCommand("measure");
  if (event.key.toLowerCase() === "r") runCommand("reset");
}

function handleCanvasPointer(event) {
  const hit = pick(event);
  if (!hit) return;

  if (hit.kind === "agent") {
    world = dispatchWorldAction(world, { type: ACTIONS.SELECT_AGENT, agentId: hit.agentId });
    renderWorld();
    return;
  }

  if (interactionMode === "place") {
    const coordinate = hit.kind === "voxel" ? adjacentCoordinate(hit.voxel.coordinate, hit.normal) : hit.coordinate;
    world = dispatchWorldAction(world, {
      type: ACTIONS.PLACE,
      coordinate,
      materialId: selectedMaterialId,
    });
    renderWorld();
    return;
  }

  if (hit.kind === "voxel" && interactionMode === "remove") {
    world = dispatchWorldAction(world, { type: ACTIONS.REMOVE, coordinate: hit.voxel.coordinate });
    renderWorld();
    return;
  }

  if (hit.kind === "voxel") {
    world = dispatchWorldAction(world, { type: ACTIONS.SELECT, coordinate: hit.voxel.coordinate });
    renderWorld();
  }
}

function pick(event) {
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);

  const objects = [...agentGroup.children, ...voxelGroup.children, ground];
  const hits = raycaster.intersectObjects(objects, true);
  for (const hit of hits) {
    const object = findPickObject(hit.object);
    if (!object) continue;

    if (object.userData.kind === "agent") {
      return { kind: "agent", agentId: object.userData.agentId };
    }

    if (object.userData.kind === "voxel") {
      const keys = voxelInstanceIndex.get(object.uuid) || [];
      const key = keys[hit.instanceId];
      const coordinate = parseCoordinateKey(key);
      return {
        kind: "voxel",
        voxel: getVoxel(world, coordinate),
        normal: hit.face?.normal || new THREE.Vector3(0, 1, 0),
      };
    }

    if (object.userData.kind === "ground") {
      return {
        kind: "ground",
        coordinate: {
          x: Math.round(hit.point.x),
          y: 0,
          z: Math.round(hit.point.z),
        },
      };
    }
  }
  return null;
}

function findPickObject(object) {
  let current = object;
  while (current) {
    if (current.userData?.kind) return current;
    current = current.parent;
  }
  return null;
}

function adjacentCoordinate(coordinate, normal) {
  return {
    x: coordinate.x + Math.round(normal.x),
    y: coordinate.y + Math.round(normal.y),
    z: coordinate.z + Math.round(normal.z),
  };
}

function renderWorld() {
  rebuildVoxelMeshes();
  rebuildAgentSprites();
  rebuildSelection();
  updateUi();
}

function rebuildVoxelMeshes() {
  disposeGroup(voxelGroup);
  scene.remove(voxelGroup);
  voxelInstanceIndex.clear();
  voxelGroup = new THREE.Group();
  scene.add(voxelGroup);

  const groups = new Map();
  for (const voxel of listVoxels(world)) {
    const group = groups.get(voxel.materialId) || [];
    group.push(voxel);
    groups.set(voxel.materialId, group);
  }

  const dummy = new THREE.Object3D();
  for (const [materialId, voxels] of groups) {
    const materialDef = MATERIALS[materialId] || MATERIALS["user-placed"];
    const material = new THREE.MeshStandardMaterial({
      color: materialDef.color,
      emissive: materialDef.color,
      emissiveIntensity: materialId.startsWith("agent") ? 0.12 : 0.06,
      roughness: 0.56,
      metalness: 0.14,
    });
    const mesh = new THREE.InstancedMesh(voxelGeometry, material, voxels.length);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.userData.kind = "voxel";
    const keys = [];

    voxels.forEach((voxel, index) => {
      dummy.position.set(voxel.coordinate.x, voxel.coordinate.y, voxel.coordinate.z);
      dummy.updateMatrix();
      mesh.setMatrixAt(index, dummy.matrix);
      keys.push(coordinateKey(voxel.coordinate));
    });

    mesh.instanceMatrix.needsUpdate = true;
    voxelInstanceIndex.set(mesh.uuid, keys);
    voxelGroup.add(mesh);
  }
}

function rebuildAgentSprites() {
  disposeGroup(agentGroup);
  scene.remove(agentGroup);
  agentGroup = new THREE.Group();
  scene.add(agentGroup);

  for (const agent of listAgents(world)) {
    const materialDef = MATERIALS[agent.materialId] || MATERIALS["agent-cyan"];
    const base = new THREE.Mesh(
      markerGeometry,
      new THREE.MeshStandardMaterial({
        color: materialDef.color,
        emissive: materialDef.color,
        emissiveIntensity: 0.18,
        roughness: 0.44,
        metalness: 0.2,
      }),
    );
    base.position.set(agent.coordinate.x, agent.coordinate.y - 0.44, agent.coordinate.z);
    base.castShadow = true;
    base.receiveShadow = true;
    base.userData.kind = "agent";
    base.userData.agentId = agent.id;
    agentGroup.add(base);

    const sprite = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: textureFor(agent.skinAsset),
        transparent: true,
        depthWrite: false,
      }),
    );
    sprite.scale.set(1.35, 2.05, 1);
    sprite.position.set(agent.coordinate.x, agent.coordinate.y + 0.78, agent.coordinate.z);
    sprite.userData.kind = "agent";
    sprite.userData.agentId = agent.id;
    agentGroup.add(sprite);
  }
}

function rebuildSelection() {
  disposeGroup(selectionGroup);
  scene.remove(selectionGroup);
  selectionGroup = new THREE.Group();
  scene.add(selectionGroup);

  if (!world.selection?.coordinate) return;

  const material = world.selection.type === "agent"
    ? new THREE.MeshBasicMaterial({ color: 0x22b8cf, wireframe: true })
    : selectionMaterial;
  const mesh = new THREE.Mesh(selectionGeometry, material);
  mesh.position.set(world.selection.coordinate.x, world.selection.coordinate.y, world.selection.coordinate.z);
  selectionGroup.add(mesh);
}

function textureFor(asset) {
  if (textureCache.has(asset)) return textureCache.get(asset);
  const texture = textureLoader.load(asset, () => renderWorld());
  texture.colorSpace = THREE.SRGBColorSpace;
  textureCache.set(asset, texture);
  return texture;
}

function updateUi() {
  const voxels = listVoxels(world);
  const agents = listAgents(world);
  const lastEvent = world.events[world.events.length - 1];
  document.getElementById("hud-status").textContent = `${world.status} / ${world.simulationStatus}`;
  document.getElementById("hud-voxels").textContent = String(voxels.length);
  document.getElementById("hud-chunks").textContent = String(Object.keys(world.chunks).length);
  document.getElementById("hud-agents").textContent = String(agents.length);
  document.getElementById("hud-event").textContent = lastEvent?.kind || "-";

  updateSelectionCard();
  updateAgentList(agents);
  updateTaskList();
  updateEventLog();
}

function updateSelectionCard() {
  const card = document.getElementById("selection-card");
  if (!world.selection) {
    card.textContent = "Nothing selected.";
    return;
  }

  if (world.selection.type === "agent") {
    const agent = world.agents[world.selection.id];
    card.innerHTML = `
      <strong>${escapeHtml(agent.name)}</strong><br>
      Role: ${escapeHtml(agent.role)}<br>
      Status: ${escapeHtml(agent.status)}<br>
      Basis: ${escapeHtml(agent.state.basis)} / P=${agent.state.probability}<br>
      Task: ${escapeHtml(agent.task.label)}<br>
      Backend: ${escapeHtml(agent.state.backend)}
    `;
    return;
  }

  const voxel = getVoxel(world, world.selection.coordinate);
  if (!voxel) {
    card.textContent = "Selected voxel no longer exists.";
    return;
  }
  const material = MATERIALS[voxel.materialId] || MATERIALS["user-placed"];
  const ref = voxel.quantumRef || {};
  card.innerHTML = `
    <strong>Voxel ${escapeHtml(coordinateKey(voxel.coordinate))}</strong><br>
    Material: ${escapeHtml(material.label)}<br>
    State: ${escapeHtml(voxel.state)}<br>
    Source: ${escapeHtml(voxel.source)}<br>
    Quantum ref: ${escapeHtml(ref.type || "none")} ${escapeHtml(ref.gate || "")}
  `;
}

function updateAgentList(agents) {
  const list = document.getElementById("agent-list");
  list.innerHTML = "";
  for (const agent of agents) {
    const row = document.createElement("button");
    row.className = `agent-row${world.selection?.id === agent.id ? " active" : ""}`;
    row.dataset.agentId = agent.id;
    row.innerHTML = `
      <img src="${escapeAttribute(agent.skinAsset)}" alt="${escapeAttribute(agent.skinName)}">
      <span>
        <span class="agent-name">${escapeHtml(agent.name)}</span>
        <span class="agent-meta">${escapeHtml(agent.role)} / ${escapeHtml(agent.skinName)}</span>
        <span class="agent-status">${escapeHtml(agent.status)} / ${escapeHtml(agent.state.result)}</span>
      </span>
    `;
    row.addEventListener("click", () => {
      world = dispatchWorldAction(world, { type: ACTIONS.SELECT_AGENT, agentId: agent.id });
      renderWorld();
    });
    list.appendChild(row);
  }
}

function updateTaskList() {
  const list = document.getElementById("task-list");
  list.innerHTML = "";
  for (const task of Object.values(world.tasks).slice(0, 15)) {
    const agent = world.agents[task.ownerAgentId];
    const row = document.createElement("div");
    row.className = "task-row";
    row.innerHTML = `
      <strong>${escapeHtml(agent?.name || task.ownerAgentId)}</strong><br>
      ${escapeHtml(task.label)}<br>
      ${escapeHtml(task.status)} / ${task.progress}%
    `;
    list.appendChild(row);
  }
}

function updateEventLog() {
  const log = document.getElementById("event-log");
  log.innerHTML = "";
  const events = world.events.slice(-7).reverse();
  for (const event of events) {
    const row = document.createElement("div");
    row.className = "event-row";
    row.innerHTML = `
      <strong>${escapeHtml(event.kind)}</strong><br>
      clock ${event.clock ?? "-"} / ${escapeHtml(event.mode || world.simulationMode)}<br>
      ${escapeHtml(event.message || event.payload?.message || "")}
    `;
    log.appendChild(row);
  }
}

function showFeedback(message, isError = false) {
  const feedback = document.getElementById("feedback");
  feedback.textContent = message;
  feedback.style.color = isError ? "var(--danger)" : "var(--green)";
  feedback.classList.add("visible");
  clearTimeout(feedbackTimer);
  feedbackTimer = setTimeout(() => feedback.classList.remove("visible"), 2400);
}

function resize() {
  const width = canvas.parentElement.clientWidth;
  const height = canvas.parentElement.clientHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  document.getElementById("cam-x").textContent = camera.position.x.toFixed(1);
  document.getElementById("cam-y").textContent = camera.position.y.toFixed(1);
  document.getElementById("cam-z").textContent = camera.position.z.toFixed(1);
  renderer.render(scene, camera);
}

function disposeGroup(group) {
  group.traverse((object) => {
    if (object.material) {
      if (Array.isArray(object.material)) {
        object.material.forEach((material) => material.dispose());
      } else {
        object.material.dispose();
      }
    }
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}
