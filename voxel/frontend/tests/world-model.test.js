import test from "node:test";
import assert from "node:assert/strict";
import {
  ACTIONS,
  chunkAddressForCoordinate,
  chunkKeyForCoordinate,
  coordinateKey,
  createInitialWorld,
  deserializeWorld,
  dispatchWorldAction,
  getVoxel,
  listAgents,
  listVoxels,
  removeVoxel,
  replaceVoxel,
  serializeWorld,
  setVoxel,
} from "../src/world-model.js";
import { qirToVoxels } from "../src/quantum-mapping.js";

test("coordinate and chunk keys are deterministic", () => {
  assert.equal(coordinateKey({ x: 1, y: 2, z: 3 }), "1,2,3");
  assert.deepEqual(chunkAddressForCoordinate({ x: 17, y: 0, z: 0 }), { x: 2, y: 0, z: 0 });
  assert.deepEqual(chunkAddressForCoordinate({ x: -1, y: 0, z: 0 }), { x: -1, y: 0, z: 0 });
  assert.equal(chunkKeyForCoordinate({ x: 8, y: 8, z: 8 }), "1:1:1");
});

test("voxel insertion, replacement, and removal preserve canonical state", () => {
  let world = createInitialWorld();
  const coordinate = { x: 9, y: 0, z: 0 };

  world = setVoxel(world, { coordinate, materialId: "user-placed" });
  assert.equal(getVoxel(world, coordinate).materialId, "user-placed");

  world = replaceVoxel(world, coordinate, { materialId: "hazard", state: "test-hazard" });
  assert.equal(getVoxel(world, coordinate).materialId, "hazard");
  assert.equal(getVoxel(world, coordinate).state, "test-hazard");

  world = removeVoxel(world, coordinate);
  assert.equal(getVoxel(world, coordinate), null);
});

test("chunk boundaries organize voxels across chunks", () => {
  let world = createInitialWorld();
  world = setVoxel(world, { coordinate: { x: 7, y: 0, z: 0 }, materialId: "user-placed" });
  world = setVoxel(world, { coordinate: { x: 8, y: 0, z: 0 }, materialId: "user-placed" });
  assert.ok(world.chunks["0:0:0"]);
  assert.ok(world.chunks["1:0:0"]);
});

test("world serialization round-trips without hidden render state", () => {
  const world = createInitialWorld();
  const roundTrip = deserializeWorld(serializeWorld(world));
  assert.equal(listAgents(roundTrip).length, 15);
  assert.equal(listVoxels(roundTrip).length, listVoxels(world).length);
});

test("selection and interaction transitions are explicit actions", () => {
  let world = createInitialWorld();
  const coordinate = { x: 0, y: 0, z: 0 };
  world = dispatchWorldAction(world, { type: ACTIONS.SELECT, coordinate });
  assert.equal(world.selection.type, "voxel");

  world = dispatchWorldAction(world, { type: ACTIONS.PLACE, coordinate: { x: 11, y: 0, z: 0 } });
  assert.equal(getVoxel(world, { x: 11, y: 0, z: 0 }).source, "user-action");
});

test("Bell-state quantum mapping keeps operation semantics", () => {
  const voxels = qirToVoxels({
    ops: [
      { type: "gate", name: "H", qubits: [0] },
      { type: "gate", name: "CX", qubits: [0, 1] },
      { type: "measure", qubit: 0 },
      { type: "measure", qubit: 1 },
    ],
  });

  assert.equal(voxels.length, 5);
  assert.deepEqual(
    voxels.map((voxel) => [voxel.coordinate.x, voxel.coordinate.y, voxel.coordinate.z, voxel.colorIndex]),
    [
      [0, 0, 0, 3],
      [1, 0, 0, 4],
      [1, 1, 0, 6],
      [2, 0, 0, 5],
      [3, 1, 0, 5],
    ],
  );
});

test("15 quantum digital twin agents use the supplied character skin set", () => {
  const world = createInitialWorld({ agentCount: 15 });
  const agents = listAgents(world);
  assert.equal(agents.length, 15);
  assert.deepEqual([...new Set(agents.map((agent) => agent.skinId))].sort(), [
    "blue-operative",
    "orange-operative",
    "wireframe-operative",
  ]);
  assert.deepEqual([...new Set(agents.map((agent) => agent.role))].sort(), ["Architect", "Pioneer", "Sentinel"]);
});

test("execution event creates a visible world update without fabricating backend results", () => {
  let world = createInitialWorld();
  const coordinate = { x: 12, y: 0, z: 0 };
  world = dispatchWorldAction(world, { type: ACTIONS.EXECUTE, coordinate });
  const voxel = getVoxel(world, coordinate);

  assert.equal(voxel.source, "execution-event");
  assert.equal(world.events.at(-1).kind, "SIMULATED_EXECUTION_EVENT");
  assert.equal(world.events.at(-1).fabricated, false);
  assert.equal(world.events.at(-1).backend, "not-connected");
});

test("end-to-end action flow mutates state and visualizable event data", () => {
  let world = createInitialWorld();
  const placed = { x: 13, y: 0, z: 0 };
  const execution = { x: 14, y: 0, z: 0 };

  world = dispatchWorldAction(world, { type: ACTIONS.PLACE, coordinate: placed, materialId: "user-placed" });
  world = dispatchWorldAction(world, { type: ACTIONS.SELECT, coordinate: placed });
  world = dispatchWorldAction(world, { type: ACTIONS.EXECUTE, coordinate: execution });

  assert.equal(getVoxel(world, placed).materialId, "user-placed");
  assert.equal(getVoxel(world, execution).state, "execution-event");
  assert.equal(world.selection.type, "voxel");
});
