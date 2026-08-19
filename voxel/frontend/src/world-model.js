import { BELL_STATE_QIR, executionEventToVoxel, qirToVoxels } from "./quantum-mapping.js";
import { DIGITAL_TWIN_COUNT, createQuantumDigitalTwins } from "./agent-roster.js";

export const CHUNK_SIZE = 8;

export const ACTIONS = {
  SELECT: "SELECT",
  SELECT_AGENT: "SELECT_AGENT",
  PLACE: "PLACE",
  REMOVE: "REMOVE",
  INSPECT: "INSPECT",
  EXECUTE: "EXECUTE",
  MEASURE: "MEASURE",
  RESET: "RESET",
  PAUSE: "PAUSE",
  RESUME: "RESUME",
};

export const MATERIALS = {
  "qubit-one": { id: "qubit-one", label: "|1> flip", color: "#e63946", colorIndex: 1 },
  "qubit-zero": { id: "qubit-zero", label: "|0> reset", color: "#457b9d", colorIndex: 2 },
  superposition: { id: "superposition", label: "superposition", color: "#f1faee", colorIndex: 3 },
  "gate-active": { id: "gate-active", label: "gate active", color: "#ffb703", colorIndex: 4 },
  measured: { id: "measured", label: "measured", color: "#2dc653", colorIndex: 5 },
  entangled: { id: "entangled", label: "entangled", color: "#8338ec", colorIndex: 6 },
  "worm-sealed": { id: "worm-sealed", label: "worm sealed", color: "#fb5607", colorIndex: 7 },
  "agent-cyan": { id: "agent-cyan", label: "sovereign agent", color: "#00b4d8", colorIndex: 8 },
  "agent-orange": { id: "agent-orange", label: "orange twin", color: "#ff4fc3", colorIndex: 8 },
  "agent-blue": { id: "agent-blue", label: "blue twin", color: "#22b8cf", colorIndex: 8 },
  "agent-wireframe": { id: "agent-wireframe", label: "wireframe twin", color: "#e8edf7", colorIndex: 8 },
  "user-placed": { id: "user-placed", label: "user placed", color: "#60d394", colorIndex: 4 },
  "execution-marker": { id: "execution-marker", label: "execution marker", color: "#ffd166", colorIndex: 8 },
  hazard: { id: "hazard", label: "hazard", color: "#ef476f", colorIndex: 1 },
};

export function coordinateKey(coordinate) {
  assertCoordinate(coordinate);
  return `${coordinate.x},${coordinate.y},${coordinate.z}`;
}

export function parseCoordinateKey(key) {
  const [x, y, z] = key.split(",").map((value) => Number.parseInt(value, 10));
  return { x, y, z };
}

export function chunkAddressForCoordinate(coordinate, chunkSize = CHUNK_SIZE) {
  assertCoordinate(coordinate);
  return {
    x: Math.floor(coordinate.x / chunkSize),
    y: Math.floor(coordinate.y / chunkSize),
    z: Math.floor(coordinate.z / chunkSize),
  };
}

export function chunkKeyForCoordinate(coordinate, chunkSize = CHUNK_SIZE) {
  const chunk = chunkAddressForCoordinate(coordinate, chunkSize);
  return `${chunk.x}:${chunk.y}:${chunk.z}`;
}

export function createWorld(metadata = {}) {
  return {
    schemaVersion: 1,
    chunkSize: CHUNK_SIZE,
    clock: 0,
    status: "paused",
    simulationStatus: "backend-unavailable",
    simulationMode: "offline-visualization",
    metadata: {
      name: "SnapKitty Quantum Voxel UX",
      backendTruth: "quantum infrastructure is authoritative; browser UX is visualization",
      agentTargetCount: DIGITAL_TWIN_COUNT,
      ...metadata,
    },
    chunks: {},
    entities: {},
    agents: {},
    tasks: {},
    events: [],
    selection: null,
    errors: [],
    materials: MATERIALS,
  };
}

export function createVoxel({
  id,
  coordinate,
  materialId = "user-placed",
  colorIndex,
  state = "stable",
  quantumRef = null,
  agentId = null,
  source = "frontend",
}) {
  assertCoordinate(coordinate);
  const material = MATERIALS[materialId] || MATERIALS["user-placed"];
  return {
    id: id || `voxel-${coordinateKey(coordinate)}`,
    coordinate: { ...coordinate },
    materialId: material.id,
    colorIndex: colorIndex || material.colorIndex,
    state,
    quantumRef,
    agentId,
    source,
  };
}

export function createInitialWorld({ qir = BELL_STATE_QIR, agentCount = DIGITAL_TWIN_COUNT } = {}) {
  const world = createWorld({
    qirSource: qir.source_lang || qir.metadata?.source_lang || "unknown",
    qirVersion: qir.version || qir.metadata?.version || "unknown",
  });

  for (const voxel of qirToVoxels(qir)) {
    insertVoxelMutable(world, createVoxel({ ...voxel, source: "qir" }));
  }

  const agents = createQuantumDigitalTwins(agentCount);
  for (const agent of agents) {
    world.agents[agent.id] = agent;
    world.entities[agent.id] = {
      id: agent.id,
      type: agent.type,
      entityKind: agent.entityKind,
      coordinate: { ...agent.coordinate },
      role: agent.role,
      status: agent.status,
      quantumRef: {
        type: "agent-state",
        basis: agent.state.basis,
        probability: agent.state.probability,
        mode: agent.state.backend,
      },
    };
    world.tasks[agent.task.id] = {
      ...agent.task,
      ownerAgentId: agent.id,
      status: agent.status === "waiting-backend" ? "blocked" : "active",
    };
    insertVoxelMutable(
      world,
      createVoxel({
        id: `agent-marker-${agent.id}`,
        coordinate: agent.coordinate,
        materialId: agent.materialId,
        state: "digital-twin-marker",
        quantumRef: {
          type: "agent-marker",
          agentId: agent.id,
          fabricated: false,
        },
        agentId: agent.id,
        source: "agent-roster",
      }),
    );
  }

  world.events.push({
    id: "event-000",
    kind: "WORLD_INITIALIZED",
    mode: world.simulationMode,
    message: `Initialized ${agents.length} quantum digital twin agents and ${listVoxels(world).length} voxels.`,
    clock: world.clock,
  });

  return world;
}

export function getVoxel(world, coordinate) {
  const chunk = world.chunks[chunkKeyForCoordinate(coordinate, world.chunkSize)];
  return chunk?.voxels?.[coordinateKey(coordinate)] || null;
}

export function listVoxels(world) {
  return Object.values(world.chunks).flatMap((chunk) => Object.values(chunk.voxels));
}

export function listAgents(world) {
  return Object.values(world.agents);
}

export function setVoxel(world, voxel) {
  const next = cloneWorld(world);
  insertVoxelMutable(next, createVoxel(voxel));
  appendEventMutable(next, "VOXEL_SET", {
    coordinate: voxel.coordinate,
    materialId: voxel.materialId,
  });
  return next;
}

export function removeVoxel(world, coordinate) {
  const next = cloneWorld(world);
  const chunkKey = chunkKeyForCoordinate(coordinate, next.chunkSize);
  const chunk = next.chunks[chunkKey];
  if (!chunk || !chunk.voxels[coordinateKey(coordinate)]) {
    appendErrorMutable(next, `No voxel exists at ${coordinateKey(coordinate)}.`);
    return next;
  }
  delete chunk.voxels[coordinateKey(coordinate)];
  next.selection = null;
  appendEventMutable(next, "VOXEL_REMOVED", { coordinate });
  return next;
}

export function replaceVoxel(world, coordinate, patch) {
  const existing = getVoxel(world, coordinate);
  if (!existing) {
    const next = cloneWorld(world);
    appendErrorMutable(next, `Cannot replace missing voxel at ${coordinateKey(coordinate)}.`);
    return next;
  }
  return setVoxel(world, {
    ...existing,
    ...patch,
    coordinate: { ...coordinate },
  });
}

export function selectVoxel(world, coordinate) {
  const next = cloneWorld(world);
  const voxel = getVoxel(next, coordinate);
  next.selection = voxel
    ? { type: "voxel", key: coordinateKey(coordinate), coordinate: { ...coordinate }, id: voxel.id }
    : null;
  appendEventMutable(next, "VOXEL_SELECTED", { coordinate, found: Boolean(voxel) });
  return next;
}

export function selectAgent(world, agentId) {
  const next = cloneWorld(world);
  const agent = next.agents[agentId];
  next.selection = agent
    ? { type: "agent", id: agent.id, key: agent.id, coordinate: { ...agent.coordinate } }
    : null;
  appendEventMutable(next, "AGENT_SELECTED", { agentId, found: Boolean(agent) });
  return next;
}

export function applyExecutionEvent(world, event) {
  const next = cloneWorld(world);
  const voxel = executionEventToVoxel(event);
  insertVoxelMutable(next, createVoxel({ ...voxel, source: "execution-event" }));
  next.simulationStatus = event.status || "simulated";
  next.status = "running";
  next.clock += 1;
  next.events.push({
    ...event,
    clock: next.clock,
    fabricated: false,
    backend: event.backend || "not-connected",
  });
  return next;
}

export function dispatchWorldAction(world, action) {
  switch (action.type) {
    case ACTIONS.SELECT:
      return selectVoxel(world, action.coordinate);
    case ACTIONS.SELECT_AGENT:
      return selectAgent(world, action.agentId);
    case ACTIONS.PLACE:
      return setVoxel(world, {
        coordinate: action.coordinate,
        materialId: action.materialId || "user-placed",
        state: "user-placed",
        source: "user-action",
      });
    case ACTIONS.REMOVE:
      return removeVoxel(world, action.coordinate);
    case ACTIONS.INSPECT:
      return inspectSelection(world);
    case ACTIONS.EXECUTE:
      return applyExecutionEvent(world, createSimulatedExecutionEvent(world, action));
    case ACTIONS.MEASURE:
      return measureSelection(world, action);
    case ACTIONS.PAUSE:
      return updateStatus(world, "paused");
    case ACTIONS.RESUME:
      return updateStatus(world, "running");
    case ACTIONS.RESET:
      return createInitialWorld(action.payload || {});
    default: {
      const next = cloneWorld(world);
      appendErrorMutable(next, `Unsupported action ${action.type}.`);
      return next;
    }
  }
}

export function serializeWorld(world) {
  return JSON.stringify(world, null, 2);
}

export function deserializeWorld(serialized) {
  const world = JSON.parse(serialized);
  if (world.schemaVersion !== 1) {
    throw new Error(`Unsupported world schema ${world.schemaVersion}`);
  }
  return world;
}

function createSimulatedExecutionEvent(world, action) {
  const selected = world.selection;
  const agentId = action.agentId || (selected?.type === "agent" ? selected.id : listAgents(world)[0]?.id);
  const coordinate = action.coordinate || nextExecutionCoordinate(world);
  return {
    id: `exec-${String(world.clock + 1).padStart(3, "0")}`,
    kind: "SIMULATED_EXECUTION_EVENT",
    mode: world.simulationMode,
    status: "simulated",
    coordinate,
    agentId,
    message: "Local visualization step only. No QPU or backend execution was claimed.",
  };
}

function nextExecutionCoordinate(world) {
  const maxX = listVoxels(world).reduce((max, voxel) => Math.max(max, voxel.coordinate.x), 0);
  return { x: maxX + 1, y: -1, z: world.clock % 4 };
}

function measureSelection(world, action) {
  const selected = world.selection;
  if (selected?.type === "agent") {
    const next = cloneWorld(world);
    const agent = next.agents[selected.id];
    agent.status = "measured";
    agent.state = {
      ...agent.state,
      result: agent.state.probability >= 0.5 ? "1" : "0",
    };
    next.entities[selected.id].status = "measured";
    appendEventMutable(next, "AGENT_MEASURED", {
      agentId: selected.id,
      result: agent.state.result,
      mode: next.simulationMode,
    });
    return next;
  }

  const coordinate = action.coordinate || selected?.coordinate || { x: 0, y: 0, z: 0 };
  return applyExecutionEvent(world, {
    id: `measure-${String(world.clock + 1).padStart(3, "0")}`,
    kind: "MEASUREMENT_EVENT",
    mode: world.simulationMode,
    status: "simulated-measurement",
    coordinate,
    message: "Measurement visualization marker. Backend result unavailable.",
  });
}

function inspectSelection(world) {
  const next = cloneWorld(world);
  appendEventMutable(next, "INSPECTED", { selection: next.selection });
  return next;
}

function updateStatus(world, status) {
  const next = cloneWorld(world);
  next.status = status;
  appendEventMutable(next, status === "running" ? "WORLD_RESUMED" : "WORLD_PAUSED", {});
  return next;
}

function insertVoxelMutable(world, voxel) {
  const chunkKey = chunkKeyForCoordinate(voxel.coordinate, world.chunkSize);
  const chunkAddress = chunkAddressForCoordinate(voxel.coordinate, world.chunkSize);
  if (!world.chunks[chunkKey]) {
    world.chunks[chunkKey] = {
      key: chunkKey,
      origin: {
        x: chunkAddress.x * world.chunkSize,
        y: chunkAddress.y * world.chunkSize,
        z: chunkAddress.z * world.chunkSize,
      },
      voxels: {},
      dirty: true,
    };
  }
  world.chunks[chunkKey].voxels[coordinateKey(voxel.coordinate)] = voxel;
  world.chunks[chunkKey].dirty = true;
}

function appendEventMutable(world, kind, payload) {
  world.clock += 1;
  world.events.push({
    id: `event-${String(world.clock).padStart(3, "0")}`,
    kind,
    payload,
    clock: world.clock,
    mode: world.simulationMode,
  });
}

function appendErrorMutable(world, message) {
  world.errors.push({ message, clock: world.clock });
  appendEventMutable(world, "ERROR", { message });
}

function cloneWorld(world) {
  return JSON.parse(JSON.stringify(world));
}

function assertCoordinate(coordinate) {
  if (
    !coordinate ||
    !Number.isInteger(coordinate.x) ||
    !Number.isInteger(coordinate.y) ||
    !Number.isInteger(coordinate.z)
  ) {
    throw new TypeError("Coordinate must contain integer x, y, and z values.");
  }
}
