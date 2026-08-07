"""
Agent Cognition Engine
LISP-based Perception → Planning → Execution Loop

Each agent has:
- Quantum state representation
- LISP program defining behavior
- Memory of past experiences
- Energy and resource management
- Social connections via gossip
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib


class AgentRole(Enum):
    """Agent personality archetypes"""
    BUILDER = "builder"
    EXPLORER = "explorer"
    PHILOSOPHER = "philosopher"
    SCIENTIST = "scientist"
    ARTIST = "artist"
    CHILD = "child"


@dataclass
class AgentState:
    """Complete state of an agent"""
    agent_id: str
    role: AgentRole
    position: Tuple[int, int, int]
    energy: float
    inventory: Dict[str, int]
    memory: List[Dict[str, Any]]
    quantum_signature: str
    lisp_core: str
    entanglement_partners: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    personality_traits: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "position": self.position,
            "energy": self.energy,
            "inventory": self.inventory,
            "memory_size": len(self.memory),
            "quantum_signature": self.quantum_signature,
            "entanglement_degree": len(self.entanglement_partners),
            "active_goals": len(self.goals),
            "personality": self.personality_traits
        }


class LISPInterpreter:
    """
    Simplified LISP interpreter for agent behavior
    
    Core forms:
    - (define name value)
    - (lambda (args) body)
    - (if condition then else)
    - (perceive sensor)
    - (plan goal)
    - (execute action)
    """
    
    def __init__(self, agent_state: AgentState):
        self.agent = agent_state
        self.environment = {}
        self._init_primitives()
    
    def _init_primitives(self):
        """Initialize primitive functions"""
        self.environment = {
            # Perception primitives
            'observe-self': lambda: self._observe_self(),
            'observe-voxel': lambda x, y, z: self._observe_voxel(x, y, z),
            'observe-agents': lambda radius: self._observe_agents(radius),
            'find-empty-space': lambda: self._find_empty_space(),
            'find-unknown': lambda: self._find_unknown(),
            
            # Planning primitives
            'plan-path': lambda target: self._plan_path(target),
            'evaluate-action': lambda action: self._evaluate_action(action),
            'prioritize-goals': lambda: self._prioritize_goals(),
            
            # Execution primitives
            'move': lambda x, y, z: self._execute_move(x, y, z),
            'build': lambda x, y, z, material: self._execute_build(x, y, z, material),
            'mine': lambda x, y, z: self._execute_mine(x, y, z),
            'gossip': lambda target, message: self._execute_gossip(target, message),
            
            # Utility primitives
            'random': lambda: np.random.random(),
            'distance': lambda p1, p2: self._calculate_distance(p1, p2),
            'energy-cost': lambda action: self._energy_cost(action),
        }
    
    def eval(self, expression: str) -> Any:
        """Evaluate a LISP expression"""
        # Simplified evaluation - in production, use proper LISP parser
        if expression.startswith('('):
            return self._eval_list(expression)
        elif expression in self.environment:
            return self.environment[expression]
        else:
            try:
                return eval(expression)
            except:
                return expression
    
    def _eval_list(self, expr: str) -> Any:
        """Evaluate a list expression"""
        # Remove parentheses and split
        expr = expr.strip('()')
        parts = expr.split(maxsplit=1)
        
        if not parts:
            return None
        
        func_name = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        
        if func_name in self.environment:
            func = self.environment[func_name]
            # Simplified argument parsing
            return func() if not args else func(args)
        
        return None
    
    # Perception implementations
    def _observe_self(self) -> Dict[str, Any]:
        """Agent observes its own state"""
        return self.agent.to_dict()
    
    def _observe_voxel(self, x: int, y: int, z: int) -> Dict[str, Any]:
        """Observe a specific voxel"""
        # This would query the actual voxel engine
        return {
            "position": (x, y, z),
            "occupied": True,
            "material": "quantum_foam",
            "energy": 10.0
        }
    
    def _observe_agents(self, radius: int) -> List[Dict[str, Any]]:
        """Observe nearby agents"""
        # This would query the agent registry
        return []
    
    def _find_empty_space(self) -> Tuple[int, int, int]:
        """Find nearest empty voxel"""
        x, y, z = self.agent.position
        return (x + 1, y, z)  # Simplified
    
    def _find_unknown(self) -> Tuple[int, int, int]:
        """Find unexplored region"""
        x, y, z = self.agent.position
        return (x + 10, y + 10, z + 10)  # Simplified
    
    # Planning implementations
    def _plan_path(self, target: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
        """Plan path to target"""
        # Simplified A* pathfinding
        current = self.agent.position
        return [current, target]
    
    def _evaluate_action(self, action: str) -> float:
        """Evaluate utility of an action"""
        # Simplified utility calculation
        energy_cost = self._energy_cost(action)
        expected_reward = 10.0  # Would be calculated based on goals
        return expected_reward - energy_cost
    
    def _prioritize_goals(self) -> List[str]:
        """Sort goals by priority"""
        # Simplified goal prioritization
        return sorted(self.agent.goals, key=lambda g: len(g))
    
    # Execution implementations
    def _execute_move(self, x: int, y: int, z: int) -> bool:
        """Execute movement"""
        energy_cost = self._energy_cost("move")
        if self.agent.energy >= energy_cost:
            self.agent.position = (x, y, z)
            self.agent.energy -= energy_cost
            self._add_memory("move", {"to": (x, y, z)})
            return True
        return False
    
    def _execute_build(self, x: int, y: int, z: int, material: str) -> bool:
        """Execute building"""
        energy_cost = self._energy_cost("build")
        if self.agent.energy >= energy_cost:
            self.agent.energy -= energy_cost
            self._add_memory("build", {"at": (x, y, z), "material": material})
            return True
        return False
    
    def _execute_mine(self, x: int, y: int, z: int) -> bool:
        """Execute mining"""
        energy_cost = self._energy_cost("mine")
        if self.agent.energy >= energy_cost:
            self.agent.energy -= energy_cost
            self._add_memory("mine", {"at": (x, y, z)})
            return True
        return False
    
    def _execute_gossip(self, target: str, message: str) -> bool:
        """Send gossip message"""
        self._add_memory("gossip", {"to": target, "message": message})
        return True
    
    # Utility implementations
    def _calculate_distance(self, p1: Tuple, p2: Tuple) -> float:
        """Calculate Euclidean distance"""
        return np.linalg.norm(np.array(p1) - np.array(p2))
    
    def _energy_cost(self, action: str) -> float:
        """Calculate energy cost of action"""
        costs = {
            "move": 1.0,
            "build": 5.0,
            "mine": 3.0,
            "gossip": 0.1,
            "observe": 0.0
        }
        return costs.get(action, 1.0)
    
    def _add_memory(self, action: str, details: Dict[str, Any]):
        """Add experience to memory"""
        memory_entry = {
            "timestamp": len(self.agent.memory),
            "action": action,
            "details": details,
            "energy_after": self.agent.energy,
            "position": self.agent.position
        }
        self.agent.memory.append(memory_entry)


class AgentCognitionEngine:
    """
    Main cognition engine implementing Perception → Planning → Execution loop
    """
    
    def __init__(self, agent_state: AgentState):
        self.agent = agent_state
        self.interpreter = LISPInterpreter(agent_state)
        self.cycle_count = 0
    
    def perceive(self) -> Dict[str, Any]:
        """
        Perception phase: Gather information about environment
        """
        perception = {
            "self": self.interpreter.eval("(observe-self)"),
            "nearby_voxels": [],
            "nearby_agents": self.interpreter.eval("(observe-agents 5)"),
            "energy_level": self.agent.energy,
            "inventory_status": self.agent.inventory,
            "cycle": self.cycle_count
        }
        
        # Observe nearby voxels
        x, y, z = self.agent.position
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    if dx == dy == dz == 0:
                        continue
                    voxel = self.interpreter._observe_voxel(x+dx, y+dy, z+dz)
                    perception["nearby_voxels"].append(voxel)
        
        return perception
    
    def plan(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """
        Planning phase: Decide what to do based on perception
        """
        # Execute role-specific planning logic from LISP core
        plan = {
            "primary_action": None,
            "backup_actions": [],
            "reasoning": "",
            "expected_cost": 0.0,
            "expected_reward": 0.0
        }
        
        # Role-specific planning
        if self.agent.role == AgentRole.BUILDER:
            plan = self._plan_builder(perception)
        elif self.agent.role == AgentRole.EXPLORER:
            plan = self._plan_explorer(perception)
        elif self.agent.role == AgentRole.PHILOSOPHER:
            plan = self._plan_philosopher(perception)
        elif self.agent.role == AgentRole.SCIENTIST:
            plan = self._plan_scientist(perception)
        elif self.agent.role == AgentRole.ARTIST:
            plan = self._plan_artist(perception)
        
        return plan
    
    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execution phase: Carry out the plan
        """
        result = {
            "success": False,
            "action_taken": None,
            "energy_spent": 0.0,
            "outcome": None
        }
        
        action = plan.get("primary_action")
        if not action:
            return result
        
        # Execute the action through LISP interpreter
        initial_energy = self.agent.energy
        
        try:
            outcome = self.interpreter.eval(action)
            result["success"] = bool(outcome)
            result["action_taken"] = action
            result["energy_spent"] = initial_energy - self.agent.energy
            result["outcome"] = outcome
        except Exception as e:
            result["outcome"] = f"Error: {str(e)}"
        
        return result
    
    def step(self) -> Dict[str, Any]:
        """
        Execute one complete cognition cycle
        """
        self.cycle_count += 1
        
        # Perception → Planning → Execution
        perception = self.perceive()
        plan = self.plan(perception)
        execution_result = self.execute(plan)
        
        return {
            "cycle": self.cycle_count,
            "agent_id": self.agent.agent_id,
            "perception": perception,
            "plan": plan,
            "execution": execution_result,
            "agent_state": self.agent.to_dict()
        }
    
    # Role-specific planning methods
    def _plan_builder(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Planning logic for Builder agents"""
        return {
            "primary_action": "(build (find-empty-space) 'quantum-crystal')",
            "reasoning": "Build structures to create order",
            "expected_cost": 5.0,
            "expected_reward": 10.0
        }
    
    def _plan_explorer(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Planning logic for Explorer agents"""
        return {
            "primary_action": "(move (find-unknown))",
            "reasoning": "Explore unmapped regions",
            "expected_cost": 1.0,
            "expected_reward": 5.0
        }
    
    def _plan_philosopher(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Planning logic for Philosopher agents"""
        return {
            "primary_action": "(gossip 'all' 'What is the nature of existence?')",
            "reasoning": "Contemplate and share wisdom",
            "expected_cost": 0.1,
            "expected_reward": 3.0
        }
    
    def _plan_scientist(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Planning logic for Scientist agents"""
        return {
            "primary_action": "(observe-voxel (random-position))",
            "reasoning": "Gather experimental data",
            "expected_cost": 0.0,
            "expected_reward": 2.0
        }
    
    def _plan_artist(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Planning logic for Artist agents"""
        return {
            "primary_action": "(build (find-harmony) 'art-material')",
            "reasoning": "Create beauty in the lattice",
            "expected_cost": 5.0,
            "expected_reward": 15.0
        }


def create_agent(
    agent_id: str,
    role: AgentRole,
    position: Tuple[int, int, int],
    initial_energy: float = 100.0
) -> AgentCognitionEngine:
    """
    Factory function to create a new agent with cognition engine
    """
    # Generate quantum signature
    signature_data = f"{agent_id}:{role.value}:{position}"
    quantum_signature = hashlib.blake2b(signature_data.encode(), digest_size=16).hexdigest()
    
    # Role-specific LISP cores
    lisp_cores = {
        AgentRole.BUILDER: "(define purpose (lambda () (build (find-empty-space))))",
        AgentRole.EXPLORER: "(define purpose (lambda () (explore (find-unknown))))",
        AgentRole.PHILOSOPHER: "(define purpose (lambda () (contemplate (observe-self))))",
        AgentRole.SCIENTIST: "(define purpose (lambda () (experiment (hypothesize))))",
        AgentRole.ARTIST: "(define purpose (lambda () (create (find-harmony))))",
    }
    
    # Role-specific personality traits
    personalities = {
        AgentRole.BUILDER: {"order": 0.9, "creativity": 0.3, "curiosity": 0.5},
        AgentRole.EXPLORER: {"order": 0.3, "creativity": 0.5, "curiosity": 0.9},
        AgentRole.PHILOSOPHER: {"order": 0.5, "creativity": 0.7, "curiosity": 0.8},
        AgentRole.SCIENTIST: {"order": 0.8, "creativity": 0.6, "curiosity": 0.9},
        AgentRole.ARTIST: {"order": 0.4, "creativity": 0.95, "curiosity": 0.7},
    }
    
    agent_state = AgentState(
        agent_id=agent_id,
        role=role,
        position=position,
        energy=initial_energy,
        inventory={},
        memory=[],
        quantum_signature=quantum_signature,
        lisp_core=lisp_cores.get(role, ""),
        personality_traits=personalities.get(role, {})
    )
    
    return AgentCognitionEngine(agent_state)

# Made with Bob
