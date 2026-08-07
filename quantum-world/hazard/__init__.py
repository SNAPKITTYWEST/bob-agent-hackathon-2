"""
Sovereign Voxel Civilization - Hazard Matrix Engine
Complete orchestration of MARL + minefield physics + agent roles

Made with Bob
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

from .minefield import (
    HazardMatrixEngine,
    MineFieldConfig,
    MineFieldDensity,
    TriggerEvent,
    Vec3,
    VoxelHazard,
)
from .pomdp_agents import (
    AgentBeliefState,
    AgentPerception,
    AgentRole,
    JordanGateTransition,
    PODMPAction,
    PODMPAgent,
    SafetyConstraint,
)
from .pomdp_agents import (
    ArchitectAgent,
    MacroLayout,
    PioneerAgent,
    ResourceNode,
    SentinelAgent,
    StructureBlueprint,
)

__all__ = [
    "HazardMatrixEngine",
    "VoxelHazard",
    "MineFieldDensity",
    "MineFieldConfig",
    "TriggerEvent",
    "PODMPAgent",
    "AgentRole",
    "AgentPerception",
    "AgentBeliefState",
    "JordanGateTransition",
    "PODMPAction",
    "SafetyConstraint",
    "PioneerAgent",
    "ArchitectAgent",
    "SentinelAgent",
    "StructureBlueprint",
    "MacroLayout",
    "ResourceNode",
    "SovereignVoxelCivilization",
]


# =============================================================================
# INTEGRATED HAZARD MATRIX SYSTEM
# =============================================================================

class SovereignVoxelCivilization:
    def __init__(self, config: MineFieldConfig, seed: int = 42) -> None:
        self.hazard_engine = HazardMatrixEngine(config, seed)
        self.agents: Dict[str, PODMPAgent] = {}
        self.step_count: int = 0
        self.trigger_log: List[TriggerEvent] = []

    def spawn_agent(
        self,
        agent_id: str,
        role: AgentRole,
        position: Tuple[float, float, float],
    ) -> PODMPAgent:
        """Spawn an agent with the specified role."""
        if role == "Pioneer":
            agent: PODMPAgent = PioneerAgent(agent_id, role, position)
        elif role == "Architect":
            agent = ArchitectAgent(agent_id, position)
        elif role == "Sentinel":
            agent = SentinelAgent(agent_id, position)
        else:
            agent = PODMPAgent(agent_id, role, position)
        self.agents[agent_id] = agent
        return agent

    def simulate_step(self) -> Dict:
        """
        Execute one simulation step for all agents.
        1. Perceive
        2. Reason (compute action distribution)
        3. Filter through NAND safety & trust-deed constraints
        4. Execute actions
        5. Check triggers & update hazards
        6. Process messages
        7. Commit state to ledger
        """
        self.step_count += 1
        agent_actions: Dict[str, str] = {}
        new_triggers: List[TriggerEvent] = []

        for agent_id, agent in self.agents.items():
            local_hazards = self._get_local_hazards(agent)
            all_other_ids = [aid for aid in self.agents if aid != agent_id]
            perception = AgentPerception(
                local_frustum=27,
                visible_hazards=len(local_hazards),
                hazard_signatures=[h.cryptographic_seal for h in local_hazards],
                visible_agents=all_other_ids,
                resource_density=random.random() * 0.5,
                structural_integrity=1.0,
                energy_level=80.0,
                timestamp=self.step_count,
            )

            agent.perceive(perception)

            actions = agent.compute_action_distribution("explore")
            selected_action = self._select_action_gumbel(actions)
            agent_actions[agent_id] = selected_action.action

            self._execute_agent_action(agent_id, selected_action)

            belief = agent.get_belief()
            trigger = self.hazard_engine.check_trigger(
                agent_id,
                Vec3(
                    x=belief.position[0],
                    y=belief.position[1],
                    z=belief.position[2],
                ),
            )
            if trigger is not None:
                new_triggers.append(trigger)
                self.trigger_log.append(trigger)

            agent.process_messages()

        if self.step_count % 10 == 0:
            activity_map: Dict[str, float] = {
                aid: random.random() for aid in self.agents
            }
            self.hazard_engine.adaptive_density_reschedule(activity_map)

        density = self.hazard_engine.get_density_info()
        return {
            "step": self.step_count,
            "agent_actions": agent_actions,
            "trigger_events": new_triggers,
            "density_update": {
                "level": density.adaptive_level,
                "active_mines": density.active_mines,
            },
        }

    def run_simulation(self, num_steps: int) -> List[Dict]:
        """Run complete simulation for N steps."""
        return [self.simulate_step() for _ in range(num_steps)]

    def get_statistics(self) -> Dict:
        """Return aggregate simulation statistics."""
        density = self.hazard_engine.get_density_info()
        triggered_mines = self.hazard_engine.get_triggered_mines()

        most_vulnerable: Optional[str] = None
        max_vulnerability = 0.0

        for agent_id, agent in self.agents.items():
            belief = agent.get_belief()
            vulnerability = 0.0
            for mine in triggered_mines:
                dist = math.hypot(
                    belief.position[0] - mine.position.x,
                    belief.position[1] - mine.position.y,
                    belief.position[2] - mine.position.z,
                )
                vulnerability += math.exp(-dist / 10.0)
            if vulnerability > max_vulnerability:
                max_vulnerability = vulnerability
                most_vulnerable = agent_id

        return {
            "total_steps": self.step_count,
            "total_triggers": len(self.trigger_log),
            "agent_count": len(self.agents),
            "hazard_density": density.density_ratio,
            "most_vulnerable_agent": most_vulnerable,
            "critical_zones": len(triggered_mines),
        }

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _get_local_hazards(self, agent: PODMPAgent) -> List[VoxelHazard]:
        belief = agent.get_belief()
        return [
            h
            for h in self.hazard_engine.get_triggered_mines()
            if math.hypot(
                belief.position[0] - h.position.x,
                belief.position[1] - h.position.y,
                belief.position[2] - h.position.z,
            )
            < 20.0
        ]

    def _select_action_gumbel(self, actions: List[PODMPAction]) -> PODMPAction:
        r = random.random()
        for action in actions:
            r -= action.probability
            if r <= 0:
                return action
        return actions[-1]

    def _execute_agent_action(
        self, agent_id: str, action: PODMPAction
    ) -> None:
        # Update agent state, resources, structures, etc.
        pass
