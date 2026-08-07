"""
LangChain Custom Tools for Quantum Living World
Complete tool suite for agent-world interaction with Bob by SnapKitty
"""

# Voxel interaction tools
from .voxel import (
    voxel_action,
    get_voxel_state,
    mine_voxel,
    build_voxel,
    harvest_energy
)

# Agent management tools
from .agents import (
    get_agent_state,
    spawn_agent,
    broadcast_gossip,
    trade_resources,
    form_alliance,
    coordinate_action
)

__all__ = [
    # Voxel tools
    'voxel_action',
    'get_voxel_state',
    'mine_voxel',
    'build_voxel',
    'harvest_energy',

    # Agent tools
    'get_agent_state',
    'spawn_agent',
    'broadcast_gossip',
    'trade_resources',
    'form_alliance',
    'coordinate_action',

    # Utility
    'get_all_tools',
]


def get_all_tools():
    """Return all LangChain tools for Bob agent orchestration."""
    return [
        # Voxel interaction (5 tools)
        voxel_action,
        get_voxel_state,
        mine_voxel,
        build_voxel,
        harvest_energy,

        # Agent management (6 tools)
        get_agent_state,
        spawn_agent,
        broadcast_gossip,
        trade_resources,
        form_alliance,
        coordinate_action,
    ]


# Made with Bob
