# Quantum Living World

**A biomimetic quantum simulation engine that synthesizes living agent behavior through 4-layer integration of NASM x86-64 machine code, IBM Granite LLM reasoning, quantum state evolution, and multi-agent orchestration.**

## What It Does

Quantum Living World brings agents to life by embedding intentional cognition into quantum superposition. A 3D voxel lattice represents a shared world where agents emerge, perceive, reason, and interact—all behavior encoded in quantum gates compiled to native machine code, guided by IBM Granite LLM cognition models, and verified through an immutable ledger.

The system demonstrates:
- **Layer 1:** Quantum gate compilation from operator algebra to x86-64 SIMD instructions
- **Layer 2:** IBM Granite LLM agent perception, memory, and goal-setting
- **Layer 3:** Adaptive Operator Quantum Dissipation (AOQD) world physics
- **Layer 4:** Multi-agent lifecycle, learning, and WORM-sealed record-keeping

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Compile NASM quantum gates to x86-64 object files
cd assembly && make && cd ..

# Run the simulation
python quantum-world/main.py

# Expected output: Voxel lattice tick, agent populations, fitness metrics
```

## Technology Stack

| Layer | Tech | Purpose |
|-------|------|---------|
| 1 | NASM x86-64 + SSE/AVX2 | Quantum gate execution |
| 2 | IBM Granite 8B/34B (Bedrock) | Agent cognition |
| 3 | NumPy/SciPy + Lindblad | Quantum state evolution |
| 4 | Python + Ed25519/Blake3 | Agent orchestration + WORM ledger |

## Key Features

- **Quantum Agents:** Agents represented as entangled voxel states; measurement collapse instantiates phenotypes
- **Cognition Loop:** Granite LLM reasoning over agent perception (niche, neighbors, memory) drives behavior
- **Deterministic Chaos:** Seeded randomness ensures reproducible multi-run validation
- **Immutable History:** All events recorded to WORM ledger (append-only, Blake3-signed)
- **Native Execution:** Gate sequences compiled to x86-64 for 100x speedup on voxel updates
- **Zero Blockchain:** No tokens, no NFTs—cryptography only (Ed25519, Blake3)

## Architecture

See `docs/ARCHITECTURE.md` for full 4-layer design, data flow, and tech stack details. ASCII diagram included.

## Project Structure

```
ibm-bob-2.0-hackathon/
├── assembly/              # NASM x86-64 quantum gate kernels
├── quantum-world/         # Python simulation engine
│   ├── engine/            # Quantum physics + Granite integration
│   ├── agents/            # Agent lifecycle & cognition
│   ├── aoqd/              # Lindblad master equation solver
│   └── tools/             # Utilities (voxel, agents, ledger)
├── docs/ARCHITECTURE.md   # Full technical design
└── requirements.txt       # Python dependencies
```

## Development

Built with IBM Bob 2.0 for full codebase context during hackathon. Every file and design decision tracked and assisted.

## Team

SnapKitty — quantum formalization + sovereign runtime engineering

## License

MIT

---

**Quantum Living World v1.0 | IBM Bob 2.0 Hackathon 2026**
