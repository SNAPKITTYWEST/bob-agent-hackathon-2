# Sovereign Voxel Civilization — Rust Engine

The Rust core of the BOB Agent Hackathon 2.0 simulation. Handles the high-performance
side: sparse voxel storage, agent execution, minefield physics, cryptographic ledger,
and the 5-stage pipeline that runs every agent tick.

Works standalone or as the backend for the Python quantum layer above it.

---

## What's in here

### World (`src/world/octree.rs`)
Sparse voxel octree over a 1024×256×1024 grid. Only occupied nodes are stored.
Each voxel carries density, material ID, hazard potential, owner agent UUID, and a
SHA-3 hash of its current state. Spatial queries and radius searches run in O(log N).

### Agents (`src/agents/agent.rs`)
Three roles, one base type. Pioneer maximizes new voxels discovered. Architect
maximizes structure stability. Sentinel minimizes hazard encounters. All three share
the same POMDP belief state structure — role-specific reward shaping produces
the specialization, not separate code paths.

### Minefield (`src/hazards/minefield.rs`)
Mines trigger on volume intersection with high-entropy voxels. When triggered:
state energy drops proportional to hazard potential, past N ledger entries get slashed,
neighboring voxels suffer structural collapse with probability Φ(h).
Density redistributes every 10 ticks via simulated annealing toward high-activity zones.

### Ledger (`src/ledger/state_ledger.rs`)
WORM append-only log. Every state transition is Ed25519-signed. Merkle tree integrity
check on every block commit. Deterministic replay from genesis seed via ChaCha20 RNG —
same seed, same simulation, bit for bit.

### Pipeline (`src/pipeline/execution.rs`)
Five stages per agent per tick:
1. Perceive — 3D frustum raycasting, update latent world model
2. Predict — compute prediction error, evaluate epistemic value
3. Filter — NAND safety constraints + trust-deed verification
4. Execute — atomic voxel mutation (build / mine / navigate / fortify)
5. Commit — sign and append state transition to ledger

### Perception (`src/perception/raycasting.rs`)
DDA algorithm for 3D frustum raycasting. 90° horizontal, 60° vertical FOV.
32×24 rays per frame, max range 64 voxels.

### Reasoning (`src/reasoning/gumbel_softmax.rs`)
Gumbel-Softmax discrete action selection with temperature annealing.
τ = max(0.5, 1.0 − 0.001·t). Lower temperature as training progresses.

---

## Build and run

```bash
cargo build --release
cargo run --release --bin svc-simulator 1000   # 1000 ticks
cargo test
cargo run --release --example basic_simulation
```

---

## Entropy bound

`H ≤ 0.20` is enforced at the pipeline gate. Agents whose actions would push system
entropy above the bound are blocked before execution. This matches the constraint from
the Python quantum layer and the Lean 4 formal proof in `../formal/`.

---

## Notes

- No PyTorch, no neural network weights — reasoning is rule-based + Gumbel sampling.
  The architecture is designed to run on hardware without ML dependencies.
- `Cargo.lock` is committed so builds are reproducible.
- `[workspace]` table in `Cargo.toml` isolates this from the parent repo's workspace.
