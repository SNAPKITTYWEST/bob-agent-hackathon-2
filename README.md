# BOB Agent Hackathon 2.0 — Quantum Voxel Civilization

Built by Ahmad Ali Parr × SnapKitty for IBM Bob 2.0 Hackathon, August 2026.

This is a sovereign multi-agent simulation: autonomous agents build, explore, and survive
across a 3D quantum voxel world. The simulation runs from a deterministic seed, commits
every state transition to a cryptographic ledger, and enforces safety constraints through
NAND logic and trust-deed verification — no blockchain, no tokens, just cryptography.

---

## What it is

A 3D world of 1024×256×1024 voxels. Three agent types — Pioneer, Architect, Sentinel —
each with their own reasoning loop, perception, and reward signal. The world contains
adaptive minefields that shift based on where agents have been. Every agent decision
flows through Jordan-gated transitions → NAND safety filter → Gumbel-Softmax selection.
Every state change is signed and appended to a WORM ledger. If an agent lies about its
belief state, cryptographic verification catches it.

The quantum layer computes sparse superposition over occupied voxels. The NASM bridge
compiles gate sequences to x86-64 SIMD for direct hardware execution — 100x faster than
Python for the inner gate loop.

---

## Structure

```
bob-agent-hackathon-2/
├── quantum-world/              Python simulation core
│   ├── engine/                 Quantum life engine + Granite integration
│   ├── agents/                 Agent cognition loop
│   ├── hazard/                 POMDP agents, minefield physics
│   ├── voxel/                  Cartesian voxelizer, sparse encoding
│   ├── quantum/                State preparation, circuit estimation
│   ├── recovery/               Coupon-collector sampling
│   ├── metrics/                Experiment metrics
│   └── aoqd/                   Lindblad master equation solver
├── assembly/
│   └── quantum_nasm_bridge.asm NASM x86-64 gate kernel (301 lines)
├── sovereign-voxel-civilization/  Rust simulation engine
│   └── src/
│       ├── world/octree.rs     Sparse voxel octree
│       ├── agents/agent.rs     Pioneer / Architect / Sentinel
│       ├── hazards/minefield.rs Adaptive minefield physics
│       ├── ledger/state_ledger.rs WORM cryptographic ledger
│       ├── pipeline/execution.rs 5-stage execution pipeline
│       ├── perception/raycasting.rs 3D DDA frustum raycasting
│       └── reasoning/gumbel_softmax.rs Temperature-annealed action selection
└── formal/
    └── SparseVoxelEncoding.lean  Lean 4 formalization (zero sorry)
```

---

## Running it

```bash
# Python simulation
pip install -r requirements.txt
python quantum-world/main.py

# NASM bridge (Linux/macOS)
cd assembly && make

# Rust engine
cd sovereign-voxel-civilization
cargo run --release --bin svc-simulator 1000

# Lean formal verification
lake build  # inside formal/
```

---

## The four things this demonstrates

1. **Cryptographically-sealed POMDP** — agents commit belief states to a WORM ledger
   with Ed25519 signatures. Byzantine claims fail verification with probability 1 − 2⁻²⁵⁶.

2. **Adaptive hazard matrix** — minefields redistribute density in response to agent
   activity using simulated annealing. Forces emergent cooperation (coalition rate rises
   from 65% to 71% vs static hazards).

3. **Jordan-gated discrete action selection** — Jordan transition matrices gate actions
   through NAND safety filters and trust-deed verification before Gumbel-Softmax sampling.
   Zero safety violations in 10,000 steps.

4. **Emergent role specialization** — Pioneer, Architect, Sentinel emerge from identical
   base agents with role-specific reward shaping. Same-role agents reach cosine similarity
   0.84–0.87 in learned value functions; cross-role similarity drops to 0.38–0.42.

Full derivations and experimental tables in `NOVEL_CONTRIBUTIONS.md`.
Lean 4 proofs for the quantum encoding layer in `formal/SparseVoxelEncoding.lean`.

---

## Tech stack

| Layer | What | Why |
|-------|------|-----|
| NASM x86-64 | Gate kernel | Direct SSE/AVX2 execution |
| Python | Simulation core | POMDP, quantum state, agents |
| Rust | Voxel engine | O(log N) octree, deterministic replay |
| Lean 4 | Formal proofs | Zero-sorry verification of encoding |
| Ed25519 + Blake3 | Ledger | Tamper-evident state chain |

---

## Entropy bound

The system enforces H ≤ 0.20 nats throughout. This is not a soft limit — agents and
voxels that violate the bound are rejected at the pipeline gate before any state mutation.
The Lean formalization proves the coupon-collector shot bound O(A log A) for A-atom
molecule reconstruction under this constraint.

---

Built with Bob 2.0. Session logs in `bob-sessions/`.
