"""
World Simulation & Sims Character Import
Ahmad Ali Parr — Sovereign Voxel Civilization

Decoupled cognitive/physical agent architecture:
  - Macro loop (LLM planning): async, ~5s cadence
  - Micro loop (physics):      sync, 60 Hz frame rate

The two loops run independently — cognition never blocks rendering.
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class NeedType(Enum):
    HUNGER = "hunger"
    ENERGY = "energy"
    SOCIAL = "social"
    FUN = "fun"


@dataclass
class MemoryRecord:
    timestamp: float
    description: str
    importance: int  # 1-10 rating for reflection retrieval


@dataclass
class AgentState:
    name: str
    persona: str
    needs: Dict[NeedType, float] = field(
        default_factory=lambda: {
            NeedType.HUNGER: 100.0,
            NeedType.ENERGY: 100.0,
            NeedType.SOCIAL: 100.0,
            NeedType.FUN: 100.0,
        }
    )
    memory_stream: List[MemoryRecord] = field(default_factory=list)
    current_intention: Optional[str] = None
    target_location: Optional[str] = None


@dataclass
class Vector3:
    x: float
    y: float
    z: float


class PhysicalAvatar:
    """Low-level physics execution at 60 Hz."""

    def __init__(self, agent_id: str, start_pos: Vector3):
        self.agent_id = agent_id
        self.position = start_pos
        self.velocity = Vector3(0, 0, 0)
        self.current_animation = "idle"

    def update_physics(self, target_pos: Vector3, delta_time: float):
        dx = target_pos.x - self.position.x
        dz = target_pos.z - self.position.z
        distance = (dx**2 + dz**2) ** 0.5

        if distance > 0.1:
            speed = 2.5
            self.position.x += (dx / distance) * speed * delta_time
            self.position.z += (dz / distance) * speed * delta_time
            self.current_animation = "walking"
        else:
            self.current_animation = "interacting"


class RealityAgent:
    """Decoupled agent brain — cognitive loop async, physics loop sync."""

    def __init__(self, state: AgentState, avatar: PhysicalAvatar):
        self.state = state
        self.avatar = avatar

    async def evaluate_high_level_intent(self, world_context: Dict):
        self.state.needs[NeedType.HUNGER] -= 5.0

        if self.state.needs[NeedType.HUNGER] < 40.0:
            self.state.current_intention = "Eat food"
            self.state.target_location = "Kitchen:Refrigerator"
        else:
            self.state.current_intention = "Socialize in Park"
            self.state.target_location = "TownSquare:Bench"

        self.state.memory_stream.append(
            MemoryRecord(
                timestamp=world_context["time"],
                description=f"Formed intention: {self.state.current_intention}",
                importance=3,
            )
        )


class WorldSimulation:
    """Main simulation loop — imports character library, runs tick."""

    def __init__(self):
        self.agents: Dict[str, RealityAgent] = {}
        self.locations: Dict[str, Vector3] = {
            "Kitchen:Refrigerator": Vector3(2.0, 0.0, 8.0),
            "TownSquare:Bench": Vector3(15.0, 0.0, -4.0),
            "Bedroom:Bed": Vector3(-5.0, 0.0, 12.0),
        }
        self.sim_time = 0.0

    def import_sims_character_library(self):
        library = [
            ("Isabella_Rodriguez", "Cafe owner who loves hosting social events", Vector3(0, 0, 0)),
            ("Klaus_Mueller", "Obsessive research scientist investigating local lore", Vector3(5, 0, 2)),
            ("Maria_Lopez", "Ambitious interior designer and social organizer", Vector3(-2, 0, -1)),
        ]
        for name, persona, pos in library:
            state = AgentState(name=name, persona=persona)
            avatar = PhysicalAvatar(agent_id=name, start_pos=pos)
            self.agents[name] = RealityAgent(state=state, avatar=avatar)

    async def run_simulation_step(self, delta_time: float):
        self.sim_time += delta_time

        # Macro cognitive update (async, every 5 sim seconds)
        if int(self.sim_time) % 5 == 0:
            for agent in self.agents.values():
                asyncio.create_task(
                    agent.evaluate_high_level_intent({"time": self.sim_time})
                )

        # Micro spatial update (frame-rate physics)
        for agent in self.agents.values():
            if agent.state.target_location in self.locations:
                target_pos = self.locations[agent.state.target_location]
                agent.avatar.update_physics(target_pos, delta_time)


async def main():
    world = WorldSimulation()
    world.import_sims_character_library()
    print(f"Imported {len(world.agents)} reality agents into world context.")

    for _ in range(3):
        await world.run_simulation_step(delta_time=1.0)
        for name, agent in world.agents.items():
            print(
                f"[{name}] Intention: {agent.state.current_intention} | "
                f"Pos: ({agent.avatar.position.x:.1f}, {agent.avatar.position.z:.1f}) | "
                f"Anim: {agent.avatar.current_animation}"
            )


if __name__ == "__main__":
    asyncio.run(main())
