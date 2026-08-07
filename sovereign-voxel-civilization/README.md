# Sovereign Voxel Civilization Engine

A DeepMind-inspired neural-symbolic hybrid simulation framework implementing autonomous emergent civilization building across a 3D voxel grid with dynamic cryptographic minefield topology.

## Architecture Overview

### Core Paradigm
- **World Model**: Spatial-Latent predictive coding network
- **Agent Framework**: Multi-Agent Reinforcement Learning (MARL)
- **Physics**: Neural-symbolic hybrid simulation
- **Determinism**: Cryptographic bit-for-bit replay via seed chaining

### System Constraints
- **Entropy Bound**: H ≤ 0.20
- **Memory Model**: Externalized WORM spatial ledger
- **Determinism**: Strict cryptographic replay capability

## Components

### 1. World Model (`src/world/`)
- **3D Sparse Voxel Octree**: 1024×256×1024 grid
- **Voxel Attributes**:
  - Density (float32)
  - Material ID (uint16)
  - Hazard Potential (probability distribution)
  - Owner Agent ID (UUID v4)
- **Latent Dynamics**: Predictive coding network for environmental forecasting

### 2. Agent Swarm (`src/agents/`)
Three specialized agent roles:
- **Pioneer**: Exploration, spatial mapping, active inference probing
- **Architect**: Structure compilation, resource consolidation, macro-layout planning
- **Sentinel**: Minefield detection, threat mitigation, trust-deed enforcement

**Architecture**:
- Perception: Local 3D frustum raycasting + latent embedding encoder
- Reasoning: Jordan-gated transition functions with Gumbel-Softmax action selection
- Coordination: Decentralized POMDP via shared mmap message passing

### 3. Minefield Physics (`src/hazards/`)
- **Trigger Mechanics**: Volume intersection with high-entropy voxel nodes
- **Consequences**: State vaporization, ledger slash, structural collapse
- **Adaptive Density**: Dynamic redistribution via simulated annealing
- **Probabilistic Obscurity**: Non-linear noise masking requiring multi-agent consensus

### 4. Execution Pipeline (`src/pipeline/`)
1. Perceive local spatial tensor and update latent world model
2. Compute prediction error and evaluate epistemic value
3. Filter actions through NAND-based safety and trust-deed constraints
4. Execute atomic voxel mutation (build, mine, navigate, fortify)
5. Commit state transition and cryptographic proof to immutable audit chain

### 5. Cryptographic Ledger (`src/ledger/`)
- WORM (Write-Once-Read-Many) spatial state storage
- Deterministic replay via seed chaining
- Immutable audit trail for all state transitions

## Technology Stack

- **Language**: Rust (performance-critical components) + Python (ML/RL training)
- **ML Framework**: PyTorch for neural networks
- **Spatial Indexing**: Custom octree implementation
- **Cryptography**: SHA-3, Ed25519 signatures
- **Visualization**: WebGPU-based 3D renderer

## Project Structure

```
sovereign-voxel-civilization/
├── src/
│   ├── world/           # Voxel octree and world model
│   ├── agents/          # MARL agent implementations
│   ├── hazards/         # Minefield physics engine
│   ├── ledger/          # Cryptographic state ledger
│   ├── pipeline/        # Execution pipeline
│   ├── perception/      # Raycasting and encoding
│   ├── reasoning/       # Decision-making modules
│   └── visualization/   # 3D rendering
├── models/              # Trained neural network weights
├── configs/             # Simulation configurations
├── tests/               # Unit and integration tests
└── examples/            # Example simulations
```

## Getting Started

See `QUICKSTART.md` for installation and usage instructions.

## Research Context

This implementation draws from:
- DeepMind's spatial-latent world models
- Multi-agent reinforcement learning research
- Neural-symbolic integration techniques
- Cryptographic state machine design

## License

MIT License - See LICENSE file for details