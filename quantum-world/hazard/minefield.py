"""
Sovereign Voxel Civilization - Hazard Matrix Engine
DeepMind MARL + Cryptographic Minefield Physics

Implements dynamic hazard topology with adaptive density,
trigger mechanics, state vaporization, and entropy bounds.

Made with Bob
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple


@dataclass
class Vec3:
    x: float
    y: float
    z: float


@dataclass
class VoxelHazard:
    position: Vec3
    hazard_potential: float  # 0-1 probability distribution
    entropy: float           # H <= 0.20
    trigger_threshold: float
    triggered: bool
    timestamp: float
    cryptographic_seal: str  # SHA-256 prefix (Blake3 equivalent via stdlib)
    triggered_by: Optional[str] = None


@dataclass
class MineFieldDensity:
    adaptive_level: float    # 0-1, adjusted by activity gradient
    active_mines: int
    total_voxels: int
    density_ratio: float     # mines / total_voxels
    last_updated: float


@dataclass
class MineFieldConfig:
    grid_dimensions: Dict[str, int]  # {"x": 1024, "y": 256, "z": 1024}
    max_entropy: float               # 0.20
    initial_density: float           # fraction of voxels with hazards
    adaptive_reschedule_interval: int  # steps
    cryptography_profile: Literal["blake3_ed25519", "sha256_hmac"] = "sha256_hmac"


@dataclass
class TriggerEvent:
    agent_id: str
    mine_id: str
    timestamp: float
    position: Vec3
    consequence: Literal["vaporization", "ledger_slash", "topological_collapse"]
    energy_loss: float
    structural_damage: List[float]
    ledger_slash: str       # hash of revoked transactions
    adjacent_voxels_affected: int
    recovery_time: float


class HazardMatrixEngine:
    def __init__(self, config: MineFieldConfig, seed: int = 42) -> None:
        self.config = config
        self.random_seed = seed
        total_voxels = (
            config.grid_dimensions["x"]
            * config.grid_dimensions["y"]
            * config.grid_dimensions["z"]
        )
        self.density = MineFieldDensity(
            adaptive_level=config.initial_density,
            active_mines=0,
            total_voxels=total_voxels,
            density_ratio=config.initial_density,
            last_updated=0.0,
        )
        self.hazard_grid: Dict[str, VoxelHazard] = {}
        self.trigger_history: List[TriggerEvent] = []
        self.activity_gradient: Dict[str, float] = {}
        self._prng_state = seed
        self._initialize_mine_field()

    # -------------------------------------------------------------------------
    # Seeded PRNG (sin-based, matches original TS implementation)
    # -------------------------------------------------------------------------

    def _seeded_random(self) -> float:
        """Return next value from seeded PRNG and advance state."""
        self._prng_state += 1
        x = math.sin(self._prng_state) * 10000.0
        return x - math.floor(x)

    # -------------------------------------------------------------------------
    # Initialisation
    # -------------------------------------------------------------------------

    def _initialize_mine_field(self) -> None:
        num_mines = int(self.density.total_voxels * self.config.initial_density)
        for _ in range(num_mines):
            position = self._random_voxel_position()
            hazard_id = self._voxel_key(position)
            hazard = VoxelHazard(
                position=position,
                hazard_potential=0.5 + self._seeded_random() * 0.4,
                entropy=self._seeded_random() * self.config.max_entropy,
                trigger_threshold=0.7 + self._seeded_random() * 0.3,
                triggered=False,
                timestamp=0.0,
                cryptographic_seal=self._compute_cryptographic_seal(hazard_id, 0),
            )
            self.hazard_grid[hazard_id] = hazard
            self.density.active_mines += 1
        self.density.density_ratio = self.density.active_mines / self.density.total_voxels

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def place_mines(self, positions: List[Vec3]) -> None:
        """Manually place mines at specified positions."""
        for pos in positions:
            hazard_id = self._voxel_key(pos)
            if hazard_id not in self.hazard_grid:
                hazard = VoxelHazard(
                    position=pos,
                    hazard_potential=0.5 + random.random() * 0.4,
                    entropy=random.random() * self.config.max_entropy,
                    trigger_threshold=0.7 + random.random() * 0.3,
                    triggered=False,
                    timestamp=0.0,
                    cryptographic_seal=self._compute_cryptographic_seal(hazard_id, 0),
                )
                self.hazard_grid[hazard_id] = hazard
                self.density.active_mines += 1
        self.density.density_ratio = self.density.active_mines / self.density.total_voxels

    def check_trigger(self, agent_id: str, position: Vec3) -> Optional[TriggerEvent]:
        """Check if agent at position triggers a mine. Returns event or None."""
        voxel_key = self._voxel_key(position)
        hazard = self.hazard_grid.get(voxel_key)
        if hazard is None or hazard.triggered:
            return None
        if hazard.hazard_potential > hazard.trigger_threshold:
            return self._execute_trigger(agent_id, hazard, voxel_key)
        return None

    def adaptive_density_reschedule(
        self, agent_activity_map: Dict[str, float]
    ) -> None:
        """Adaptive minefield rescheduling based on activity gradients."""
        self.activity_gradient = dict(agent_activity_map)
        values = list(agent_activity_map.values())
        if not values:
            return
        total_activity = sum(values)
        mean_activity = total_activity / len(values)
        new_density_level = self.config.initial_density + mean_activity * 0.1
        self.density.adaptive_level = min(new_density_level, 0.5)
        self._redistribute_mines(self.density.adaptive_level)
        self.density.last_updated = time.time()
        self.density.density_ratio = self.density.active_mines / self.density.total_voxels

    def get_density_info(self) -> MineFieldDensity:
        return MineFieldDensity(
            adaptive_level=self.density.adaptive_level,
            active_mines=self.density.active_mines,
            total_voxels=self.density.total_voxels,
            density_ratio=self.density.density_ratio,
            last_updated=self.density.last_updated,
        )

    def get_triggered_mines(self) -> List[VoxelHazard]:
        return [h for h in self.hazard_grid.values() if h.triggered]

    def get_trigger_history(self) -> List[TriggerEvent]:
        return list(self.trigger_history)

    def get_hazard_at(self, position: Vec3) -> Optional[VoxelHazard]:
        return self.hazard_grid.get(self._voxel_key(position))

    def decode_hazard_signature(self, signatures: List[str]) -> bool:
        """Require 2/3 consensus for hazard signature validity."""
        valid = sum(1 for sig in signatures if self._validate_signature(sig))
        return valid >= math.ceil(len(signatures) * 2 / 3)

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _execute_trigger(
        self, agent_id: str, hazard: VoxelHazard, mine_id: str
    ) -> TriggerEvent:
        hazard.triggered = True
        hazard.triggered_by = agent_id
        hazard.timestamp = time.time()
        hazard.cryptographic_seal = self._compute_cryptographic_seal(mine_id, hazard.timestamp)

        consequence = self._determine_trigger_consequence(hazard)
        energy_loss = hazard.hazard_potential * 100.0
        ledger_slash_hash = self._compute_ledger_slash(agent_id, mine_id, hazard.timestamp)
        adjacent_count = self._calculate_topological_collapse(hazard.position)
        structural_damage = self._calculate_structural_damage(hazard.position, adjacent_count)
        recovery_time = self._calculate_recovery_time(consequence, structural_damage)

        event = TriggerEvent(
            agent_id=agent_id,
            mine_id=mine_id,
            timestamp=hazard.timestamp,
            position=hazard.position,
            consequence=consequence,
            energy_loss=energy_loss,
            structural_damage=structural_damage,
            ledger_slash=ledger_slash_hash,
            adjacent_voxels_affected=adjacent_count,
            recovery_time=recovery_time,
        )
        self.trigger_history.append(event)
        return event

    def _determine_trigger_consequence(
        self, hazard: VoxelHazard
    ) -> Literal["vaporization", "ledger_slash", "topological_collapse"]:
        if hazard.entropy > 0.15:
            return "topological_collapse"
        elif hazard.hazard_potential > 0.8:
            return "vaporization"
        else:
            return "ledger_slash"

    def _redistribute_mines(self, new_density: float) -> None:
        target_mine_count = int(self.density.total_voxels * new_density)
        current_mine_count = self.density.active_mines

        if target_mine_count > current_mine_count:
            mines_to_add = target_mine_count - current_mine_count
            for _ in range(mines_to_add):
                position = self._random_voxel_position()
                hazard_id = self._voxel_key(position)
                if hazard_id not in self.hazard_grid:
                    hazard = VoxelHazard(
                        position=position,
                        hazard_potential=0.5 + random.random() * 0.4,
                        entropy=random.random() * self.config.max_entropy,
                        trigger_threshold=0.7 + random.random() * 0.3,
                        triggered=False,
                        timestamp=0.0,
                        cryptographic_seal=self._compute_cryptographic_seal(hazard_id, 0),
                    )
                    self.hazard_grid[hazard_id] = hazard
                    self.density.active_mines += 1
        elif target_mine_count < current_mine_count:
            mines_to_remove = current_mine_count - target_mine_count
            removed = 0
            keys_to_delete = []
            for key, hazard in self.hazard_grid.items():
                if not hazard.triggered and removed < mines_to_remove:
                    keys_to_delete.append(key)
                    removed += 1
            for key in keys_to_delete:
                del self.hazard_grid[key]
                self.density.active_mines -= 1

    def _calculate_topological_collapse(self, center: Vec3) -> int:
        direct_neighbors = 26
        cascade_chance = 0.3
        expected_cascade = direct_neighbors * (1 + cascade_chance * 5)
        return int(expected_cascade)

    def _calculate_structural_damage(
        self, center: Vec3, affected_count: int
    ) -> List[float]:
        return [random.random() * 0.8 for _ in range(affected_count)]

    def _calculate_recovery_time(
        self,
        consequence: str,
        structural_damage: List[float],
    ) -> float:
        base: Dict[str, float] = {
            "vaporization": 200.0,
            "ledger_slash": 50.0,
            "topological_collapse": 150.0,
        }
        if not structural_damage:
            return base.get(consequence, 100.0)
        damage_multiplier = sum(structural_damage) / len(structural_damage)
        return base.get(consequence, 100.0) * (1.0 + damage_multiplier)

    def _compute_cryptographic_seal(self, mine_id: str, timestamp: float) -> str:
        data = f"{mine_id}:{timestamp}:{self.random_seed}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _compute_ledger_slash(
        self, agent_id: str, mine_id: str, timestamp: float
    ) -> str:
        data = f"slash:{agent_id}:{mine_id}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _validate_signature(self, signature: str) -> bool:
        bits = ""
        for ch in signature:
            try:
                bits += bin(int(ch, 16))[2:].zfill(4)
            except ValueError:
                pass
        if not bits:
            return False
        ones = bits.count("1")
        ratio = ones / len(bits)
        if ratio == 0 or ratio == 1:
            return False
        entropy = -(ratio * math.log2(ratio))
        return entropy > 0.3

    def _voxel_key(self, pos: Vec3) -> str:
        return f"{int(pos.x)},{int(pos.y)},{int(pos.z)}"

    def _random_voxel_position(self) -> Vec3:
        gx = self.config.grid_dimensions["x"]
        gy = self.config.grid_dimensions["y"]
        gz = self.config.grid_dimensions["z"]
        return Vec3(
            x=int(self._seeded_random() * gx),
            y=int(self._seeded_random() * gy),
            z=int(self._seeded_random() * gz),
        )
