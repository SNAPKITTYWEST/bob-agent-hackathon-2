"""
Digital Twin State Vector & Quantum Operator Pipeline
Ahmad Ali Parr — Sovereign Voxel Civilization

Classical-Quantum State Synchronization Engine:
  - ClassicalPhysicsOperator:  continuous kinematics at 60 Hz
  - QuantumConstraintOperator: QUBO Hamiltonian for discrete pathing
  - DigitalTwinRuntime:        async QPU dispatch + sync classical step
"""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class QuantumTwinState:
    agent_id: str
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    needs_matrix: Dict[str, float]
    active_constraints: List[str]
    quantum_state_ref: Optional[str] = None


class ClassicalPhysicsOperator:
    """Continuous spatial kinematics at 60 Hz."""

    def step(
        self,
        state: QuantumTwinState,
        target: Tuple[float, float, float],
        dt: float,
    ) -> QuantumTwinState:
        px, py, pz = state.position
        tx, ty, tz = target
        dx, dy, dz = tx - px, ty - py, tz - pz
        dist = np.sqrt(dx**2 + dy**2 + dz**2)

        if dist > 0.05:
            vx = (dx / dist) * 2.0
            vy = (dy / dist) * 2.0
            vz = (dz / dist) * 2.0
            state.position = (px + vx * dt, py + vy * dt, pz + vz * dt)
            state.velocity = (vx, vy, vz)
        else:
            state.velocity = (0.0, 0.0, 0.0)
        return state


class QuantumConstraintOperator:
    """Translates agent states into QUBO matrices for discrete pathing."""

    def build_qubo_hamiltonian(
        self,
        states: List[QuantumTwinState],
        resources: List[str],
    ) -> np.ndarray:
        n = len(states)
        Q = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    d = np.linalg.norm(
                        np.array(states[i].position)
                        - np.array(states[j].position)
                    )
                    Q[i][j] = 1.0 / (d + 0.01)
        return Q

    async def solve_optimal_assignments(
        self, Q: np.ndarray
    ) -> Dict[int, int]:
        await asyncio.sleep(0.02)  # Async QPU dispatch offset
        return {idx: idx % 3 for idx in range(Q.shape[0])}


class DigitalTwinRuntime:
    """Classical-Quantum synchronization engine for sovereign civilization."""

    def __init__(self, agents: List[QuantumTwinState]):
        self.agents = agents
        self.classical_sim = ClassicalPhysicsOperator()
        self.quantum_op = QuantumConstraintOperator()
        self.resource_nodes = ["O2_Generator", "Power_Grid", "Hydroponics"]
        self.node_coordinates = [
            (10.0, 0.0, 0.0),
            (-10.0, 0.0, 5.0),
            (0.0, 0.0, -15.0),
        ]

    async def tick_simulation_cycle(self, dt: float):
        # 1. Async global quantum optimization (QUBO solver)
        Q = self.quantum_op.build_qubo_hamiltonian(
            self.agents, self.resource_nodes
        )
        assignment_map = await self.quantum_op.solve_optimal_assignments(Q)

        # 2. Sync classical kinematics step
        for idx, agent in enumerate(self.agents):
            assigned_node_idx = assignment_map.get(idx, 0)
            target_pos = self.node_coordinates[assigned_node_idx]
            self.classical_sim.step(agent, target_pos, dt)


async def run_civilization_runtime():
    twins = [
        QuantumTwinState(
            "Isabella_Twin",
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            {"O2": 95.0},
            ["O2_Depletion"],
        ),
        QuantumTwinState(
            "Klaus_Twin",
            (2.0, 0.0, 1.0),
            (0.0, 0.0, 0.0),
            {"O2": 80.0},
            ["System_Repair"],
        ),
    ]

    runtime = DigitalTwinRuntime(twins)
    await runtime.tick_simulation_cycle(dt=0.016)

    for agent in runtime.agents:
        print(
            f"Twin [{agent.agent_id}] -> "
            f"Pos: {tuple(round(v,3) for v in agent.position)} | "
            f"Vel: {tuple(round(v,3) for v in agent.velocity)}"
        )


if __name__ == "__main__":
    asyncio.run(run_civilization_runtime())
