"""
POMDP Multi-Agent Coordination with Jordan-Gated Transitions
DeepMind MARL architecture for Sovereign Voxel Civilization

Partially Observable Markov Decision Processes with:
- Decentralized agent reasoning
- Gumbel-Softmax discrete action selection
- Shared mmap message passing
- Trust-deed constraint kernels
- NAND-based safety filters

Made with Bob
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple

AgentRole = Literal["Pioneer", "Architect", "Sentinel"]


@dataclass
class AgentPerception:
    local_frustum: int  # 3D frustum voxel count
    visible_hazards: int
    hazard_signatures: List[str]  # Non-linear noise masked
    visible_agents: List[str]  # Nearby agent IDs
    resource_density: float
    structural_integrity: float  # 0-1
    energy_level: float
    timestamp: int


@dataclass
class AgentBeliefState:
    agent_id: str
    role: AgentRole
    position: Tuple[float, float, float]
    energy: float
    inventory: Dict[str, float]

    # Latent beliefs (partially observable)
    estimated_hazard_map: Dict[str, float]  # hazard_id -> confidence
    estimated_agent_positions: Dict[str, Tuple[float, float, float]]
    mission_progress: float  # 0-1
    trust_score: float  # 0-1, for alliance formation
    last_observation: AgentPerception

    # History (for planning)
    recent_actions: List[Dict]  # {action, outcome, timestamp}


@dataclass
class JordanGateTransition:
    input_dimension: int
    gate_weights: List[float]  # Learned weights
    activation_function: Literal["relu", "tanh", "sigmoid"]
    gate_values: List[float]
    selected_action: Optional[str] = None


@dataclass
class PODMPAction:
    action: Literal["explore", "build", "defend", "communicate", "retreat"]
    target: Optional[Tuple[float, float, float]]
    target_agent: Optional[str]
    probability: float  # Gumbel-Softmax temperature-scaled
    energy_cost: float
    expected_reward: float
    trust_deed_violation: bool


@dataclass
class SafetyConstraint:
    type: Literal["nand_kernel", "trust_deed", "entropy_bound"]
    enabled: bool
    violation_count: int
    last_violation: Optional[float] = None


def _empty_perception() -> AgentPerception:
    return AgentPerception(
        local_frustum=0,
        visible_hazards=0,
        hazard_signatures=[],
        visible_agents=[],
        resource_density=0.0,
        structural_integrity=1.0,
        energy_level=100.0,
        timestamp=0,
    )


def _initialize_weights(dimension: int) -> List[float]:
    return [(random.random() - 0.5) * 2.0 for _ in range(dimension)]


def _apply_activation(x: float, fn: str) -> float:
    if fn == "relu":
        return max(0.0, x)
    elif fn == "tanh":
        return math.tanh(x)
    elif fn == "sigmoid":
        return 1.0 / (1.0 + math.exp(-x))
    return x


def _compute_entropy(observation: str) -> float:
    if not observation:
        return 0.0
    freq: Dict[str, int] = {}
    for ch in observation:
        freq[ch] = freq.get(ch, 0) + 1
    entropy = 0.0
    n = len(observation)
    for count in freq.values():
        p = count / n
        entropy -= p * math.log2(p)
    return entropy


class PODMPAgent:
    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        position: Tuple[float, float, float],
    ) -> None:
        self.belief = AgentBeliefState(
            agent_id=agent_id,
            role=role,
            position=position,
            energy=100.0,
            inventory={},
            estimated_hazard_map={},
            estimated_agent_positions={},
            mission_progress=0.0,
            trust_score=1.0,
            last_observation=_empty_perception(),
            recent_actions=[],
        )

        self.jordan_gate = JordanGateTransition(
            input_dimension=16,
            gate_weights=_initialize_weights(16),
            activation_function="tanh",
            gate_values=[],
        )

        self.safety_constraints: Dict[str, SafetyConstraint] = {
            "nand_kernel": SafetyConstraint(type="nand_kernel", enabled=True, violation_count=0),
            "trust_deed": SafetyConstraint(type="trust_deed", enabled=True, violation_count=0),
            "entropy_bound": SafetyConstraint(type="entropy_bound", enabled=True, violation_count=0),
        }

        self.message_buffer: List[Dict] = []
        self.epistemic_value: Dict[str, float] = {}

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def perceive(self, observation: AgentPerception) -> None:
        """Perception phase: update belief state from local observation."""
        self.belief.last_observation = observation

        for idx, sig in enumerate(observation.hazard_signatures):
            hazard_id = f"hazard_{idx}"
            current_confidence = self.belief.estimated_hazard_map.get(hazard_id, 0.5)
            new_confidence = self._bayesian_update(current_confidence, sig)
            self.belief.estimated_hazard_map[hazard_id] = new_confidence

        self._compute_epistemic_value(observation)

    def compute_action_distribution(self, mission_goal: str) -> List[PODMPAction]:
        """Reasoning phase: compute action probabilities via Jordan-gated transition."""
        features = self._encode_perception_features()
        self._apply_jordan_gate_transition(features)
        action_logits = self._compute_action_logits(mission_goal)
        probabilities = self._gumbel_softmax(action_logits, temperature=0.5)
        safe_actions = self._filter_through_nand_kernel(probabilities, mission_goal)
        trustee_actions = self._filter_through_trust_deed(safe_actions)
        return self._enrich_actions_with_estimates(trustee_actions)

    def select_action_gumbel(self, actions: List[PODMPAction]) -> PODMPAction:
        """Weighted random selection using Gumbel-Softmax probabilities."""
        r = random.random()
        for action in actions:
            r -= action.probability
            if r <= 0:
                return action
        return actions[-1]

    def get_belief(self) -> AgentBeliefState:
        """Return a shallow copy of the belief state."""
        return AgentBeliefState(
            agent_id=self.belief.agent_id,
            role=self.belief.role,
            position=self.belief.position,
            energy=self.belief.energy,
            inventory=dict(self.belief.inventory),
            estimated_hazard_map=dict(self.belief.estimated_hazard_map),
            estimated_agent_positions=dict(self.belief.estimated_agent_positions),
            mission_progress=self.belief.mission_progress,
            trust_score=self.belief.trust_score,
            last_observation=self.belief.last_observation,
            recent_actions=list(self.belief.recent_actions),
        )

    def process_messages(self) -> None:
        """Message passing phase: coordinate with other agents via mmap."""
        import json as _json
        while self.message_buffer:
            msg = self.message_buffer.pop(0)
            if msg.get("priority", 0) > 0.8:
                try:
                    hazard_data = _json.loads(msg["message"])
                    self.belief.estimated_hazard_map[hazard_data["id"]] = hazard_data["confidence"]
                except Exception:
                    pass
            if "alliance" in msg.get("message", ""):
                self.belief.trust_score = min(1.0, self.belief.trust_score + 0.1)

    def send_message(self, to: str, message: str, priority: float = 0.5) -> None:
        """Send message to other agents (async mmap queue)."""
        print(f"[MMAP] {self.belief.agent_id} -> {to}: {message}")

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _sample_gumbel(self) -> float:
        u = random.random()
        return -math.log(-math.log(u + 1e-20) + 1e-20)

    def _gumbel_softmax(self, logits: List[float], temperature: float = 1.0) -> List[float]:
        gumbel_logits = [l + self._sample_gumbel() for l in logits]
        scaled = [g / temperature for g in gumbel_logits]
        max_val = max(scaled)
        exps = [math.exp(s - max_val) for s in scaled]
        total = sum(exps)
        return [e / total for e in exps]

    def _apply_jordan_gate_transition(self, features: List[float]) -> None:
        if len(features) != self.jordan_gate.input_dimension:
            raise ValueError(
                f"Feature dimension mismatch: expected {self.jordan_gate.input_dimension}, "
                f"got {len(features)}"
            )
        preactivations = [
            features[i] * self.jordan_gate.gate_weights[i]
            for i in range(len(features))
        ]
        self.jordan_gate.gate_values = [
            _apply_activation(p, self.jordan_gate.activation_function)
            for p in preactivations
        ]

    def _filter_through_nand_kernel(
        self, probabilities: List[float], goal: str
    ) -> List[PODMPAction]:
        actions: List[PODMPAction] = [
            PODMPAction(action="explore",     target=None, target_agent=None, probability=probabilities[0], energy_cost=1.0,   expected_reward=5.0,  trust_deed_violation=False),
            PODMPAction(action="build",       target=None, target_agent=None, probability=probabilities[1], energy_cost=5.0,   expected_reward=10.0, trust_deed_violation=False),
            PODMPAction(action="defend",      target=None, target_agent=None, probability=probabilities[2], energy_cost=3.0,   expected_reward=8.0,  trust_deed_violation=False),
            PODMPAction(action="communicate", target=None, target_agent=None, probability=probabilities[3], energy_cost=0.5,   expected_reward=2.0,  trust_deed_violation=False),
            PODMPAction(action="retreat",     target=None, target_agent=None, probability=probabilities[4], energy_cost=2.0,   expected_reward=3.0,  trust_deed_violation=False),
        ]

        result = []
        for a in actions:
            if a.action == "build" and "defend" in goal:
                self.safety_constraints["nand_kernel"].violation_count += 1
                continue
            result.append(a)
        return result

    def _filter_through_trust_deed(self, actions: List[PODMPAction]) -> List[PODMPAction]:
        for a in actions:
            if self._check_trust_deed_violation(a):
                self.safety_constraints["trust_deed"].violation_count += 1
                a.trust_deed_violation = True
                a.probability *= 0.1
        return actions

    def _check_trust_deed_violation(self, action: PODMPAction) -> bool:
        if action.action == "communicate" and action.target_agent:
            target_trust = 0.5
            return target_trust < self.belief.trust_score * 0.7
        return False

    def _encode_perception_features(self) -> List[float]:
        obs = self.belief.last_observation
        nk = self.safety_constraints["nand_kernel"].violation_count
        td = self.safety_constraints["trust_deed"].violation_count
        eb = self.safety_constraints["entropy_bound"].violation_count
        return [
            obs.local_frustum / 1000.0,
            obs.visible_hazards / 10.0,
            len(obs.hazard_signatures) / 5.0,
            len(obs.visible_agents) / 5.0,
            obs.resource_density,
            obs.structural_integrity,
            obs.energy_level / 100.0,
            math.tanh(self.belief.mission_progress),
            self.belief.trust_score,
            len(self.belief.recent_actions) / 10.0,
            len(self.belief.estimated_hazard_map) / 100.0,
            math.log1p(len(self.belief.estimated_agent_positions)),
            nk / 10.0,
            td / 10.0,
            eb / 10.0,
            self.belief.energy / 100.0,
        ]

    def _compute_action_logits(self, goal: str) -> List[float]:
        actions = ["explore", "build", "defend", "communicate", "retreat"]
        logits = []
        for action in actions:
            logit = random.random()
            if "explore" in goal and action == "explore":
                logit += 2.0
            if "build" in goal and action == "build":
                logit += 2.0
            if "defend" in goal and action == "defend":
                logit += 2.0
            if "communicate" in goal and action == "communicate":
                logit += 1.5
            if self.belief.energy < 20:
                logit += 1.0 if action == "retreat" else -0.5
            logits.append(logit)
        return logits

    def _enrich_actions_with_estimates(self, actions: List[PODMPAction]) -> List[PODMPAction]:
        eb_violations = self.safety_constraints["entropy_bound"].violation_count
        for a in actions:
            a.expected_reward *= (1.0 + self.belief.mission_progress) * math.exp(-eb_violations)
            if self.belief.energy < 30:
                a.energy_cost *= 1.5
        return actions

    def _bayesian_update(self, prior: float, observation: str) -> float:
        likelihood = self._compute_likelihood(observation)
        posterior = (likelihood * prior) / (
            likelihood * prior + (1 - likelihood) * (1 - prior)
        )
        return posterior

    def _compute_likelihood(self, observation: str) -> float:
        entropy = _compute_entropy(observation)
        return 0.5 + 0.5 * math.tanh(entropy - 0.5)

    def _compute_epistemic_value(self, observation: AgentPerception) -> None:
        for i in range(10):
            voxel_id = f"voxel_{i}"
            self.epistemic_value[voxel_id] = random.random() * 0.5


# =============================================================================
# PIONEER AGENT - EXPLORATION & ACTIVE INFERENCE
# =============================================================================

class PioneerAgent(PODMPAgent):
    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        position: Tuple[float, float, float],
    ) -> None:
        super().__init__(agent_id, role, position)
        self.exploration_map: Dict[str, int] = {}
        self.frontier_voxels: set = set()
        self.active_inference_queue: List[str] = []

    def compute_exploration_objective(
        self, unexplored_regions: List[str]
    ) -> List[PODMPAction]:
        actions = self.compute_action_distribution("explore")
        for a in actions:
            if a.action == "explore":
                a.probability *= 1.5
                break
        for voxel_id in unexplored_regions:
            self.frontier_voxels.add(voxel_id)
            self.active_inference_queue.append(voxel_id)
        return actions

    def perform_active_inference(self) -> Dict:
        probed_voxels = []
        total_information_gain = 0.0
        for _ in range(5):
            if not self.active_inference_queue:
                break
            voxel_id = self.active_inference_queue.pop(0)
            probed_voxels.append(voxel_id)
            visit_count = self.exploration_map.get(voxel_id, 0)
            information_gain = 1.0 / (1.0 + visit_count)
            total_information_gain += information_gain
            self.exploration_map[voxel_id] = visit_count + 1
            if visit_count >= 3:
                self.frontier_voxels.discard(voxel_id)
        return {"probed_voxels": probed_voxels, "information_gain": total_information_gain}

    def generate_spatial_map(self) -> Dict:
        explored = len(self.exploration_map)
        frontier = len(self.frontier_voxels)
        coverage = explored / (explored + frontier + 1)
        return {
            "explored_voxels": explored,
            "frontier_size": frontier,
            "coverage": coverage,
        }

    def compute_local_frustum(
        self,
        position: Tuple[float, float, float],
        direction: Tuple[float, float, float],
    ) -> AgentPerception:
        num_sigs = random.randint(0, 2)
        perception = AgentPerception(
            local_frustum=27,
            visible_hazards=random.randint(0, 2),
            hazard_signatures=[
                hex(random.getrandbits(32))[2:] for _ in range(num_sigs)
            ],
            visible_agents=[],
            resource_density=random.random() * 0.5,
            structural_integrity=1.0,
            energy_level=80.0,
            timestamp=int(time.time() * 1000),
        )
        self.perceive(perception)
        return perception


# =============================================================================
# ARCHITECT AGENT - STRUCTURE COMPILATION & MACRO-PLANNING
# =============================================================================

@dataclass
class StructureBlueprint:
    type: Literal["wall", "tower", "farm", "factory", "antenna", "resonator"]
    position: Tuple[float, float, float]
    durability: float
    material_cost: Dict[str, float]
    estimated_build_time: float
    energy_production: float = 0.0


@dataclass
class StructureInstance:
    id: str
    type: str
    position: Tuple[float, float, float]
    durability: float
    completion_time: float
    energy_production: float


@dataclass
class MacroLayout:
    zone_map: Dict[str, List[str]]
    critical_paths: List[Tuple[str, str]]
    resource_distribution: Dict[str, float]
    optimization_objective: str


@dataclass
class ResourceNode:
    type: str
    position: Tuple[float, float, float]
    amount: float


class ArchitectAgent(PODMPAgent):
    def __init__(
        self,
        agent_id: str,
        position: Tuple[float, float, float],
    ) -> None:
        super().__init__(agent_id, "Architect", position)
        self.structure_blueprints: Dict[str, StructureBlueprint] = {}
        self.resource_inventory: Dict[str, float] = {}
        self.construction_queue: List[str] = []
        self.macro_layout = MacroLayout(
            zone_map={},
            critical_paths=[],
            resource_distribution={},
            optimization_objective="minimize_distance",
        )

    def compute_building_objective(
        self, target_structures: List[str]
    ) -> List[PODMPAction]:
        actions = self.compute_action_distribution("build")
        for a in actions:
            if a.action == "build":
                a.probability *= 1.5
                break
        for struct_id in target_structures:
            self.construction_queue.append(struct_id)
        return actions

    def compile_structures(
        self, available_resources: Dict[str, float]
    ) -> Dict:
        compiled: List[StructureInstance] = []
        used: Dict[str, float] = {}
        while self.construction_queue:
            struct_id = self.construction_queue.pop(0)
            blueprint = self.structure_blueprints.get(struct_id)
            if blueprint is None or not self._can_build(blueprint, available_resources, used):
                break
            instance = StructureInstance(
                id=struct_id,
                type=blueprint.type,
                position=blueprint.position,
                durability=blueprint.durability,
                completion_time=blueprint.estimated_build_time,
                energy_production=blueprint.energy_production,
            )
            compiled.append(instance)
            for resource, amount in blueprint.material_cost.items():
                used[resource] = used.get(resource, 0.0) + amount
        return {"compiled_structures": compiled, "resources_used": used}

    def plan_macro_layout(
        self, structures: List[StructureInstance]
    ) -> MacroLayout:
        zones = self._partition_into_zones(structures)
        critical_paths = self._compute_critical_paths(zones)
        resource_dist = self._distribute_resources(zones)
        self.macro_layout = MacroLayout(
            zone_map=zones,
            critical_paths=critical_paths,
            resource_distribution=resource_dist,
            optimization_objective="minimize_distance",
        )
        return self.macro_layout

    def consolidate_resources(self, scattered_resources: List[ResourceNode]) -> None:
        centers = self._identify_consolidation_centers(scattered_resources)
        if not centers:
            return
        for resource in scattered_resources:
            nearest = min(centers, key=lambda c: self._distance(resource.position, c))
            self.resource_inventory[resource.type] = (
                self.resource_inventory.get(resource.type, 0.0) + resource.amount
            )

    def get_macro_layout(self) -> MacroLayout:
        return self.macro_layout

    def _can_build(
        self,
        blueprint: StructureBlueprint,
        available: Dict[str, float],
        used: Dict[str, float],
    ) -> bool:
        for resource, cost in blueprint.material_cost.items():
            total_used = used.get(resource, 0.0) + cost
            if available.get(resource, 0.0) - total_used < 0:
                return False
        return True

    def _partition_into_zones(
        self, structures: List[StructureInstance]
    ) -> Dict[str, List[str]]:
        zones: Dict[str, List[str]] = {}
        for s in structures:
            zone = f"zone_{int(s.position[0] / 10)}"
            zones.setdefault(zone, []).append(s.id)
        return zones

    def _compute_critical_paths(
        self, zones: Dict[str, List[str]]
    ) -> List[Tuple[str, str]]:
        zone_ids = list(zones.keys())
        return [(zone_ids[i], zone_ids[i + 1]) for i in range(len(zone_ids) - 1)]

    def _distribute_resources(
        self, zones: Dict[str, List[str]]
    ) -> Dict[str, float]:
        total = len(zones)
        if total == 0:
            return {}
        return {zone_id: 1.0 / total for zone_id in zones}

    def _identify_consolidation_centers(
        self, resources: List[ResourceNode]
    ) -> List[Tuple[float, float, float]]:
        if not resources:
            return []
        sx = sum(r.position[0] for r in resources)
        sy = sum(r.position[1] for r in resources)
        sz = sum(r.position[2] for r in resources)
        n = len(resources)
        return [(sx / n, sy / n, sz / n)]

    def _distance(
        self,
        pos1: Tuple[float, float, float],
        pos2: Tuple[float, float, float],
    ) -> float:
        dx, dy, dz = pos1[0] - pos2[0], pos1[1] - pos2[1], pos1[2] - pos2[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)


# =============================================================================
# SENTINEL AGENT - THREAT DETECTION & DEFENSE
# =============================================================================

@dataclass
class VoxelHazardRef:
    position: Tuple[float, float, float]  # (x, y, z)
    hazard_potential: float
    entropy: float


@dataclass
class HazardThreat:
    hazard_id: str
    severity: float  # 0-1
    position: Tuple[float, float, float]


@dataclass
class Alliance:
    id: str
    members: List[str]
    terms: str


@dataclass
class TrustDeed:
    id: str
    signatories: List[str]
    terms: str
    signature: str
    verified: bool
    timestamp: float


class SentinelAgent(PODMPAgent):
    def __init__(
        self,
        agent_id: str,
        position: Tuple[float, float, float],
    ) -> None:
        super().__init__(agent_id, "Sentinel", position)
        self.hazard_gradient_map: Dict[str, float] = {}
        self.threat_level: float = 0.0
        self.defensive_structures: set = set()
        self.trust_deed_registry: Dict[str, TrustDeed] = {}

    def compute_defense_objective(
        self, detected_threats: List[HazardThreat]
    ) -> List[PODMPAction]:
        actions = self.compute_action_distribution("defend")
        for a in actions:
            if a.action == "defend":
                a.probability *= 1.8
                break
        self.threat_level = max((t.severity for t in detected_threats), default=0.0)
        return actions

    def detect_minefield_gradient(
        self, local_hazards: List[VoxelHazardRef]
    ) -> Dict:
        max_gradient = 0.0
        danger_zones: List[str] = []
        for hazard in local_hazards:
            voxel_id = f"{hazard.position[0]},{hazard.position[1]},{hazard.position[2]}"
            gradient = hazard.hazard_potential * (1.0 - hazard.entropy)
            self.hazard_gradient_map[voxel_id] = gradient
            max_gradient = max(max_gradient, gradient)
            if gradient > 0.7:
                danger_zones.append(voxel_id)
        return {
            "gradient_map": dict(self.hazard_gradient_map),
            "max_gradient": max_gradient,
            "danger_zones": danger_zones,
        }

    def mitigate_threats(
        self, threats: List[HazardThreat]
    ) -> Dict:
        defensive_actions: List[str] = []
        for threat in threats:
            if threat.severity > 0.8:
                defend_struct_id = f"defend_{threat.hazard_id}"
                self.defensive_structures.add(defend_struct_id)
                defensive_actions.append(f"BUILD_DEFENSE_{threat.hazard_id}")
        evasion_routes = self._compute_evasion_routes(
            list(self.hazard_gradient_map.keys())
        )
        return {
            "defensive_actions": defensive_actions,
            "evasion_routes": evasion_routes,
        }

    def enforce_trust_deeds(self, alliances: List[Alliance]) -> Dict:
        verified: List[str] = []
        violated: List[str] = []
        for alliance in alliances:
            deed = self.trust_deed_registry.get(alliance.id)
            if deed is None:
                new_deed = TrustDeed(
                    id=alliance.id,
                    signatories=alliance.members,
                    terms=alliance.terms,
                    signature=self._compute_deed_signature(alliance),
                    verified=True,
                    timestamp=time.time(),
                )
                self.trust_deed_registry[alliance.id] = new_deed
                verified.append(alliance.id)
            elif self._verify_deed_signature(deed):
                verified.append(alliance.id)
            else:
                violated.append(alliance.id)
        return {"verified_alliances": verified, "violated_deeds": violated}

    def get_threat_level(self) -> float:
        return self.threat_level

    def _compute_evasion_routes(
        self, danger_voxels: List[str]
    ) -> List[Tuple[float, float, float]]:
        if not danger_voxels:
            return []
        centroid = self._compute_centroid(danger_voxels)
        escape = self._compute_escape_vector(centroid)
        route: List[Tuple[float, float, float]] = []
        for i in range(5):
            route.append((
                centroid[0] + escape[0] * i * 2,
                centroid[1] + escape[1] * i * 2,
                centroid[2] + escape[2] * i * 2,
            ))
        return route

    def _compute_centroid(
        self, voxel_ids: List[str]
    ) -> Tuple[float, float, float]:
        sx, sy, sz = 0.0, 0.0, 0.0
        for vid in voxel_ids:
            parts = vid.split(",")
            sx += float(parts[0])
            sy += float(parts[1])
            sz += float(parts[2])
        n = len(voxel_ids)
        return (sx / n, sy / n, sz / n)

    def _compute_escape_vector(
        self, danger: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        angle = random.random() * 2.0 * math.pi
        x = math.cos(angle)
        y = math.sin(angle)
        z = random.random() - 0.5
        norm = math.sqrt(x * x + y * y + z * z)
        return (x / norm, y / norm, z / norm)

    def _compute_deed_signature(self, alliance: Alliance) -> str:
        import hashlib
        data = ":".join(alliance.members)
        return hashlib.sha256(data.encode()).hexdigest()

    def _verify_deed_signature(self, deed: TrustDeed) -> bool:
        recomputed = self._compute_deed_signature(
            Alliance(id=deed.id, members=deed.signatories, terms=deed.terms)
        )
        return recomputed == deed.signature
