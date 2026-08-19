export const QUANTUM_COLORS = {
  1: "#e63946",
  2: "#457b9d",
  3: "#f1faee",
  4: "#ffb703",
  5: "#2dc653",
  6: "#8338ec",
  7: "#fb5607",
  8: "#00b4d8",
};

export const QUANTUM_LABELS = {
  1: "|1> flip",
  2: "|0> reset",
  3: "superposition",
  4: "gate active",
  5: "measured",
  6: "entangled",
  7: "worm sealed",
  8: "sovereign agent",
};

export const COLOR_INDEX_TO_MATERIAL = {
  1: "qubit-one",
  2: "qubit-zero",
  3: "superposition",
  4: "gate-active",
  5: "measured",
  6: "entangled",
  7: "worm-sealed",
  8: "agent-cyan",
};

export const BELL_STATE_QIR = {
  version: "0.1.0",
  source_lang: "quipper",
  qubits: 2,
  cbits: 2,
  ops: [
    { type: "gate", name: "H", params: [], qubits: [0] },
    { type: "gate", name: "CX", params: [], qubits: [0, 1] },
    { type: "measure", qubit: 0, cbit: 0 },
    { type: "measure", qubit: 1, cbit: 1 },
  ],
  metadata: {
    source_lang: "quipper",
    version: "0.1.0",
    unsupported: [
      "higher-order circuit parameters represented as flat gate sequence",
      "dynamic lifting represented as measurement-only visualization",
    ],
  },
  resources: { gate_count: 2, depth: 3, t_count: 0, width: 2 },
};

export function gateColorIndex(name, role = "solo") {
  if (name === "H") return 3;
  if (["X", "Y", "Z"].includes(name)) return 1;
  if (["CX", "CNOT", "CZ"].includes(name)) {
    return role === "control" ? 4 : 6;
  }
  if (["T", "Tdg", "S", "Sdg", "Rx", "Ry", "Rz", "U1", "U2", "U3", "CCX"].includes(name)) {
    return 4;
  }
  return 4;
}

export function qirToVoxels(qir) {
  const metadata = qir.metadata || qir.meta || {};
  const wormSealed = Boolean(metadata.worm_sealed);
  const voxels = [];
  let t = 0;

  for (const op of qir.ops || []) {
    const opType = op.type || op.op || "";

    if (opType === "barrier") continue;

    if (opType === "gate") {
      const qubits = op.qubits || [];
      if (qubits.length === 0) {
        t += 1;
        continue;
      }

      if (qubits.length === 1) {
        const colorIndex = wormSealed ? 7 : gateColorIndex(op.name, "solo");
        voxels.push(makeQuantumVoxel(t, qubits[0], colorIndex, op));
      } else {
        const controlColor = wormSealed ? 7 : gateColorIndex(op.name, "control");
        const targetColor = wormSealed ? 7 : gateColorIndex(op.name, "target");
        voxels.push(makeQuantumVoxel(t, qubits[0], controlColor, op, "control"));
        for (let i = 1; i < qubits.length; i += 1) {
          voxels.push(makeQuantumVoxel(t, qubits[i], targetColor, op, "target"));
        }
      }
    } else if (opType === "measure") {
      const colorIndex = wormSealed ? 7 : 5;
      voxels.push(makeQuantumVoxel(t, op.qubit, colorIndex, op, "measurement"));
    } else if (opType === "reset") {
      const colorIndex = wormSealed ? 7 : 2;
      voxels.push(makeQuantumVoxel(t, op.qubit, colorIndex, op, "reset"));
    }

    t += 1;
  }

  return voxels;
}

export function executionEventToVoxel(event) {
  const colorIndex = event.kind === "MEASUREMENT_EVENT" ? 5 : 8;
  return {
    id: `event-${event.id}`,
    coordinate: event.coordinate,
    materialId: COLOR_INDEX_TO_MATERIAL[colorIndex],
    colorIndex,
    state: "execution-event",
    quantumRef: {
      type: event.kind,
      eventId: event.id,
      mode: event.mode || "offline-visualization",
    },
  };
}

function makeQuantumVoxel(t, qubit, colorIndex, op, role = "solo") {
  return {
    id: `qir-${t}-${qubit}-${role}`,
    coordinate: { x: t, y: qubit, z: 0 },
    materialId: COLOR_INDEX_TO_MATERIAL[colorIndex],
    colorIndex,
    state: QUANTUM_LABELS[colorIndex],
    quantumRef: {
      type: op.type || op.op,
      gate: op.name || null,
      qubits: op.qubits || (Number.isInteger(op.qubit) ? [op.qubit] : []),
      role,
      time: t,
    },
  };
}
