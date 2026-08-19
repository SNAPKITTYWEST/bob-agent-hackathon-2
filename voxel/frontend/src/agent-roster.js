export const DIGITAL_TWIN_COUNT = 15;

export const CHARACTER_SKINS = [
  {
    id: "orange-operative",
    name: "Orange Operative",
    asset: "assets/characters/snapkitty-orange-operative.png",
    accent: "#ff4fc3",
    materialId: "agent-orange",
  },
  {
    id: "blue-operative",
    name: "Blue Operative",
    asset: "assets/characters/snapkitty-blue-operative.png",
    accent: "#22b8cf",
    materialId: "agent-blue",
  },
  {
    id: "wireframe-operative",
    name: "Wireframe Prototype",
    asset: "assets/characters/snapkitty-wireframe-operative.jpg",
    accent: "#e8edf7",
    materialId: "agent-wireframe",
  },
];

const ROLES = ["Pioneer", "Architect", "Sentinel"];

const ROLE_TASKS = {
  Pioneer: ["Map circuit frontier", "Probe sparse voxel boundary", "Trace unknown chunk"],
  Architect: ["Place stabilizer scaffold", "Route gate corridor", "Compact chunk lattice"],
  Sentinel: ["Scan hazard vector", "Watch WORM ledger drift", "Guard measurement lane"],
};

const STATUS_BY_INDEX = ["active", "active", "simulated", "waiting-backend", "active"];

export function createQuantumDigitalTwins(count = DIGITAL_TWIN_COUNT) {
  return Array.from({ length: count }, (_, index) => {
    const role = ROLES[index % ROLES.length];
    const skin = CHARACTER_SKINS[index % CHARACTER_SKINS.length];
    const lane = Math.floor(index / 5);
    const slot = index % 5;
    const probability = Number((0.34 + ((index * 7) % 50) / 100).toFixed(2));
    const entropyNats = Number((0.08 + ((index * 3) % 9) / 100).toFixed(2));
    const taskOptions = ROLE_TASKS[role];

    return {
      id: `qdt-${String(index + 1).padStart(2, "0")}`,
      name: `SIOM-QDT-${String(index + 1).padStart(2, "0")}`,
      type: "QuantumEntity",
      entityKind: "DigitalTwinAgent",
      role,
      skinId: skin.id,
      skinName: skin.name,
      skinAsset: skin.asset,
      materialId: skin.materialId,
      accent: skin.accent,
      coordinate: { x: -5 + slot * 2, y: 0, z: 3 + lane * 2 },
      status: STATUS_BY_INDEX[index % STATUS_BY_INDEX.length],
      state: {
        basis: index % 2 === 0 ? "|0>" : "|1>",
        probability,
        entropyNats,
        backend: "offline-visualization",
        result: "not-executed",
      },
      task: {
        id: `task-${String(index + 1).padStart(2, "0")}`,
        label: taskOptions[index % taskOptions.length],
        progress: (index * 13) % 100,
      },
      route: {
        source: "Rust AgentRole mirror",
        requiredBackend: "quantum-world/bob_interface.py",
        fabricated: false,
      },
    };
  });
}

export function getSkinById(skinId) {
  return CHARACTER_SKINS.find((skin) => skin.id === skinId) || CHARACTER_SKINS[0];
}
