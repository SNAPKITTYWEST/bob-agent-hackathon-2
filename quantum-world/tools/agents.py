"""
Agent Management Tools
Tools for creating, managing, and interacting with agents
"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class GetAgentStateInput(BaseModel):
    """Input schema for get_agent_state tool"""
    agent_id: str = Field(description="Unique identifier for the agent")
    include_memory: bool = Field(
        default=False,
        description="Include full memory trace"
    )
    include_lisp: bool = Field(
        default=True,
        description="Include LISP core program"
    )


class SpawnAgentInput(BaseModel):
    """Input schema for spawn_agent tool"""
    agent_id: str = Field(description="Unique identifier for new agent")
    role: str = Field(
        description="Agent role: 'builder', 'explorer', 'philosopher', 'scientist', 'artist'"
    )
    x: int = Field(description="Initial X position")
    y: int = Field(description="Initial Y position")
    z: int = Field(description="Initial Z position")
    initial_energy: float = Field(default=100.0, description="Starting energy")
    personality_override: Optional[Dict[str, float]] = Field(
        default=None,
        description="Custom personality traits"
    )


class BroadcastGossipInput(BaseModel):
    """Input schema for broadcast_gossip tool"""
    sender_id: str = Field(description="Agent sending the message")
    message: str = Field(description="Message content")
    target: str = Field(
        default="all",
        description="Target: 'all', specific agent_id, or 'nearby'"
    )
    priority: str = Field(
        default="normal",
        description="Priority: 'low', 'normal', 'high', 'emergency'"
    )


@tool(args_schema=GetAgentStateInput)
def get_agent_state(
    agent_id: str,
    include_memory: bool = False,
    include_lisp: bool = True
) -> Dict[str, Any]:
    """
    Get the complete state of an agent including LISP trace, energy, inventory, and position.
    
    Returns detailed information about:
    - Current quantum state
    - Energy level and resource inventory
    - Position in voxel lattice
    - LISP cognition program
    - Memory trace (if requested)
    - Entanglement partners
    - Active goals
    - Personality traits
    
    This is essential for Bob to understand what an agent is doing and why.
    """
    # This would query the actual agent registry
    agent_state = {
        "agent_id": agent_id,
        "role": "builder",  # Would be actual role
        "position": {"x": 42, "y": 42, "z": 10},
        "energy": 87.5,
        "max_energy": 100.0,
        "inventory": {
            "quantum_crystal": 5,
            "energy_cell": 2
        },
        "quantum_signature": "a1b2c3d4e5f6",
        "entanglement_partners": ["alice", "charlie"],
        "entanglement_degree": 2,
        "active_goals": [
            "build_tower",
            "gather_resources"
        ],
        "personality_traits": {
            "order": 0.9,
            "creativity": 0.3,
            "curiosity": 0.5
        },
        "status": "active",
        "cycles_alive": 1547,
        "last_action": "build",
        "last_action_success": True
    }
    
    if include_lisp:
        agent_state["lisp_core"] = "(define purpose (lambda () (build (find-empty-space))))"
        agent_state["current_perception"] = {
            "nearby_voxels": 26,
            "nearby_agents": 2,
            "energy_level": "high"
        }
        agent_state["current_plan"] = {
            "primary_action": "build",
            "reasoning": "Continue tower construction",
            "expected_cost": 5.0
        }
    
    if include_memory:
        agent_state["memory"] = [
            {
                "timestamp": 1547,
                "action": "build",
                "details": {"at": (42, 42, 11), "material": "quantum_crystal"},
                "energy_after": 87.5
            },
            {
                "timestamp": 1546,
                "action": "move",
                "details": {"to": (42, 42, 10)},
                "energy_after": 92.5
            }
        ]
        agent_state["memory_size"] = len(agent_state["memory"])
    
    return agent_state


@tool(args_schema=SpawnAgentInput)
def spawn_agent(
    agent_id: str,
    role: str,
    x: int,
    y: int,
    z: int,
    initial_energy: float = 100.0,
    personality_override: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Create a new agent with specified role and personality.
    
    Roles:
    - builder: Constructs structures, seeks order
    - explorer: Maps the universe, seeks knowledge
    - philosopher: Contemplates existence, seeks meaning
    - scientist: Studies quantum mechanics, seeks truth
    - artist: Creates beauty, seeks harmony
    
    The agent will be initialized with:
    - Role-specific LISP cognition program
    - Personality traits
    - Starting position and energy
    - Unique quantum signature
    
    Returns the new agent's complete state.
    """
    # This would create an actual agent in the system
    from quantum_world.agents.cognition import create_agent, AgentRole
    
    # Map string role to enum
    role_map = {
        "builder": AgentRole.BUILDER,
        "explorer": AgentRole.EXPLORER,
        "philosopher": AgentRole.PHILOSOPHER,
        "scientist": AgentRole.SCIENTIST,
        "artist": AgentRole.ARTIST
    }
    
    agent_role = role_map.get(role.lower(), AgentRole.BUILDER)
    
    result = {
        "success": True,
        "agent_id": agent_id,
        "role": role,
        "position": {"x": x, "y": y, "z": z},
        "initial_energy": initial_energy,
        "quantum_signature": f"sig_{agent_id}",
        "lisp_core": f"(define purpose (lambda () ({role} (find-target))))",
        "personality_traits": personality_override or {
            "order": 0.5,
            "creativity": 0.5,
            "curiosity": 0.5
        },
        "message": f"Agent {agent_id} spawned successfully as {role}",
        "timestamp": _get_quantum_time()
    }
    
    # Log for Bob's observation
    _log_spawn_for_bob(result)
    
    return result


@tool(args_schema=BroadcastGossipInput)
def broadcast_gossip(
    sender_id: str,
    message: str,
    target: str = "all",
    priority: str = "normal"
) -> Dict[str, Any]:
    """
    Send a message through the agent gossip protocol.
    
    The gossip protocol enables:
    - Information sharing between agents
    - Collective knowledge building
    - Social bond formation
    - Emergency broadcasts
    
    Targets:
    - 'all': Broadcast to all agents
    - 'nearby': Only agents within range
    - specific agent_id: Direct message
    
    Priority levels affect propagation speed and persistence.
    """
    # This would send through the actual gossip network
    result = {
        "success": True,
        "sender_id": sender_id,
        "message": message,
        "target": target,
        "priority": priority,
        "timestamp": _get_quantum_time(),
        "propagation_estimate": _estimate_propagation(target, priority),
        "recipients": _get_recipients(target),
        "message_id": f"msg_{sender_id}_{_get_quantum_time()}"
    }
    
    # Log for Bob's observation
    _log_gossip_for_bob(result)
    
    return result


# Helper functions

def _get_quantum_time() -> int:
    """Get current quantum simulation time"""
    import time
    return int(time.time() * 1000)


def _estimate_propagation(target: str, priority: str) -> Dict[str, Any]:
    """Estimate message propagation"""
    base_time = 10  # time steps
    
    priority_multipliers = {
        "low": 2.0,
        "normal": 1.0,
        "high": 0.5,
        "emergency": 0.1
    }
    
    multiplier = priority_multipliers.get(priority, 1.0)
    
    return {
        "estimated_time_steps": int(base_time * multiplier),
        "estimated_reach": "all" if target == "all" else "targeted",
        "priority_boost": priority != "normal"
    }


def _get_recipients(target: str) -> List[str]:
    """Get list of message recipients"""
    if target == "all":
        return ["alice", "charlie", "diana", "eve", "frank"]  # Would be actual agent list
    elif target == "nearby":
        return ["alice", "charlie"]  # Would be calculated from positions
    else:
        return [target]


def _log_spawn_for_bob(spawn_result: Dict[str, Any]) -> None:
    """Log agent spawn for Bob's observation"""
    # This would add to Bob's observation queue
    pass


def _log_gossip_for_bob(gossip_result: Dict[str, Any]) -> None:
    """Log gossip message for Bob's observation"""
    # This would add to Bob's observation queue
    pass


# ============================================================================
# Advanced Agent Interaction Tools
# ============================================================================

class TradeResourcesInput(BaseModel):
    """Input for trade_resources tool"""
    sender_id: str = Field(description="Agent initiating trade")
    receiver_id: str = Field(description="Agent receiving trade")
    offer: Dict[str, int] = Field(description="Resources offered: {resource: quantity}")
    request: Dict[str, int] = Field(description="Resources requested: {resource: quantity}")


@tool(args_schema=TradeResourcesInput)
def trade_resources(
    sender_id: str,
    receiver_id: str,
    offer: Dict[str, int],
    request: Dict[str, int]
) -> Dict[str, Any]:
    """
    Execute a trade between two agents.

    Resources that can be traded:
    - quantum_crystal: Basic building material
    - dark_matter: Advanced material
    - composite: Mixed material
    - energy_cell: Stored energy
    - knowledge_token: Information

    Returns:
        success: bool
        trade_id: str
        offer_accepted: bool
        resources_exchanged: dict
        net_value_change: float (for each agent)
    """
    result = {
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "trade_id": f"trade_{sender_id}_{receiver_id}_{_get_quantum_time()}",
        "offer": offer,
        "request": request,
        "success": True,
        "offer_accepted": True,  # Would check acceptability
        "timestamp": _get_quantum_time()
    }

    # Calculate trade fairness
    sender_value = sum(v * _get_resource_value(k) for k, v in offer.items())
    receiver_value = sum(v * _get_resource_value(k) for k, v in request.items())

    result.update({
        "sender_value_sent": sender_value,
        "sender_value_received": receiver_value,
        "net_sender_gain": receiver_value - sender_value,
        "trade_fairness": min(sender_value, receiver_value) / max(sender_value, receiver_value, 0.01),
        "resources_exchanged": {
            "from_sender": offer,
            "from_receiver": request
        }
    })

    return result


class FormAlllianceInput(BaseModel):
    """Input for form_alliance tool"""
    initiator_id: str = Field(description="Agent initiating alliance")
    partners: List[str] = Field(description="Agent IDs to partner with")
    alliance_type: str = Field(
        description="Type: 'trade_pact', 'research_alliance', 'defense_pact', 'building_collective'"
    )
    duration: int = Field(default=100, description="Duration in time steps")


@tool(args_schema=FormAlllianceInput)
def form_alliance(
    initiator_id: str,
    partners: List[str],
    alliance_type: str,
    duration: int = 100
) -> Dict[str, Any]:
    """
    Form an alliance between multiple agents.

    Alliance types and benefits:
    - trade_pact: 10% resource value bonus
    - research_alliance: 15% knowledge gain bonus
    - defense_pact: +20% durability for shared structures
    - building_collective: 25% construction speed bonus

    Returns:
        alliance_id: str
        members: list
        type: str
        benefits: dict
        duration_steps: int
    """
    result = {
        "success": True,
        "initiator_id": initiator_id,
        "alliance_id": f"alliance_{initiator_id}_{_get_quantum_time()}",
        "members": [initiator_id] + partners,
        "alliance_type": alliance_type,
        "duration_steps": duration,
        "timestamp": _get_quantum_time()
    }

    # Calculate benefits based on alliance type
    benefits_map = {
        "trade_pact": {"resource_bonus": 0.10, "trade_speed": 1.5},
        "research_alliance": {"knowledge_bonus": 0.15, "research_speed": 2.0},
        "defense_pact": {"durability_bonus": 0.20, "protection_range": 10},
        "building_collective": {"construction_speed": 1.25, "material_efficiency": 0.20}
    }

    benefits = benefits_map.get(alliance_type, {})
    result.update({
        "benefits": benefits,
        "member_count": len(result["members"]),
        "collective_strength": len(result["members"]) * 1.5  # Synergy multiplier
    })

    return result


class CoordinateActionInput(BaseModel):
    """Input for coordinate_action tool"""
    coordinator_id: str = Field(description="Agent coordinating")
    action: str = Field(description="Action: 'synchronized_build', 'resource_relay', 'collective_mine'")
    participants: List[str] = Field(description="Participating agent IDs")
    target_location: Dict[str, int] = Field(description="Target: {x, y, z}")


@tool(args_schema=CoordinateActionInput)
def coordinate_action(
    coordinator_id: str,
    action: str,
    participants: List[str],
    target_location: Dict[str, int]
) -> Dict[str, Any]:
    """
    Coordinate a multi-agent action.

    Actions:
    - synchronized_build: All agents build simultaneously, 2x speed
    - resource_relay: Chain pass resources, no energy loss over distance
    - collective_mine: Pool mining efforts, 3x yield

    Returns:
        coordination_id: str
        action: str
        participants: list
        efficiency_multiplier: float
        expected_completion_time: int
    """
    result = {
        "success": True,
        "coordinator_id": coordinator_id,
        "coordination_id": f"coord_{coordinator_id}_{_get_quantum_time()}",
        "action": action,
        "participants": [coordinator_id] + participants,
        "target": target_location,
        "timestamp": _get_quantum_time()
    }

    # Calculate efficiency based on participation
    participant_count = len(result["participants"])
    base_efficiency = {
        "synchronized_build": 2.0,
        "resource_relay": 1.0,
        "collective_mine": 3.0
    }

    multiplier = base_efficiency.get(action, 1.0)
    # Diminishing returns beyond 5 agents
    if participant_count > 5:
        multiplier *= (5.0 / participant_count)

    result.update({
        "participant_count": participant_count,
        "efficiency_multiplier": multiplier,
        "expected_completion_time": int(100 / multiplier),
        "energy_cost_per_agent": 10.0 / participant_count  # Shared cost
    })

    return result


def _get_resource_value(resource: str) -> float:
    """Get the base value of a resource"""
    values = {
        "quantum_crystal": 1.0,
        "dark_matter": 3.0,
        "composite": 2.0,
        "energy_cell": 0.5,
        "knowledge_token": 2.5
    }
    return values.get(resource, 1.0)


# Made with Bob
