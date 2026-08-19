# SnapKitty Quantum Voxel Front End

This directory contains the browser-owned voxel UX layer for the Bob Agent Hackathon 2 repository.

## What is implemented

- Canonical serializable world state in `src/world-model.js`
- Deterministic coordinate, chunk, voxel, selection, action, event, and persistence primitives
- QIR-to-voxel mapping in `src/quantum-mapping.js`
- 15 SIOM quantum digital twin agents in `src/agent-roster.js`
- Three.js projection in `src/app.js`
- Character sprites sourced from `assets/characters/`
- Orbit camera, zoom, selection, placement, removal, execution markers, measurement markers, local save/load, status panels, agent inspection, task inspection, and event feedback

The front end does not claim QPU execution. Execution and measurement buttons create local visualization events only and label the backend as not connected.

## Run

```bash
cd voxel/frontend
npm test
npm run build
npm run dev
```

Then open `http://127.0.0.1:4173/`.

## Backend dependencies

- `quantum-world/bob_interface.py` for live Bob/agent routing
- `quantum-world/main.py` for Python simulation truth
- `sovereign-voxel-civilization/src/agents/agent.rs` for authoritative role semantics
- `voxel/emitter/qir_to_vox.py` for canonical QIR-to-voxel lowering

Until those interfaces provide browser-readable execution state, the UX remains an offline visualization and interaction layer.
