// Execution Pipeline
// Five-stage pipeline with safety constraints and trust-deed enforcement

use crate::world::octree::{SparseVoxelOctree, Position, Voxel};
use crate::agents::agent::{Agent, Action, ActionOutcome, Observation, Direction};
use crate::hazards::minefield::{Minefield, MineExplosion};
use crate::ledger::state_ledger::{SpatialLedger, StateTransition};
use ed25519_dalek::Keypair;
use std::collections::HashMap;

/// Trust deed constraint system
#[derive(Debug, Clone)]
pub struct TrustDeed {
    pub agent_id: uuid::Uuid,
    pub territory_bounds: Vec<(Position, Position)>,
    pub resource_limits: HashMap<u16, u32>,
    pub max_actions_per_tick: u32,
    pub hazard_risk_threshold: f32,
}

impl TrustDeed {
    pub fn new(agent_id: uuid::Uuid) -> Self {
        Self {
            agent_id,
            territory_bounds: Vec::new(),
            resource_limits: HashMap::new(),
            max_actions_per_tick: 10,
            hazard_risk_threshold: 0.7,
        }
    }

    /// Check if position is within allowed territory
    pub fn check_boundary(&self, position: &Position) -> bool {
        if self.territory_bounds.is_empty() {
            return true; // No restrictions
        }

        for (min, max) in &self.territory_bounds {
            if position.x >= min.x && position.x <= max.x &&
               position.y >= min.y && position.y <= max.y &&
               position.z >= min.z && position.z <= max.z {
                return true;
            }
        }

        false
    }

    /// Check if resource usage is within limits
    pub fn check_resources(&self, material_id: u16, amount: u32) -> bool {
        if let Some(&limit) = self.resource_limits.get(&material_id) {
            amount <= limit
        } else {
            true // No limit set
        }
    }

    /// Add territory bounds
    pub fn add_territory(&mut self, min: Position, max: Position) {
        self.territory_bounds.push((min, max));
    }

    /// Set resource limit
    pub fn set_resource_limit(&mut self, material_id: u16, limit: u32) {
        self.resource_limits.insert(material_id, limit);
    }
}

/// NAND-based safety kernel
pub struct SafetyKernel {
    trust_deeds: HashMap<uuid::Uuid, TrustDeed>,
}

impl SafetyKernel {
    pub fn new() -> Self {
        Self {
            trust_deeds: HashMap::new(),
        }
    }

    /// Register trust deed for agent
    pub fn register_trust_deed(&mut self, trust_deed: TrustDeed) {
        self.trust_deeds.insert(trust_deed.agent_id, trust_deed);
    }

    /// Filter actions through safety constraints (NAND logic)
    pub fn filter_actions(
        &self,
        agent_id: uuid::Uuid,
        actions: Vec<Action>,
        world: &SparseVoxelOctree,
        minefield: &Minefield,
    ) -> Vec<Action> {
        let trust_deed = match self.trust_deeds.get(&agent_id) {
            Some(td) => td,
            None => return actions, // No constraints
        };

        actions
            .into_iter()
            .filter(|action| {
                // Extract target position from action
                let target_position = match action {
                    Action::Move { direction } => {
                        // Would need agent position, simplified here
                        return true;
                    }
                    Action::Build { target, .. } => *target,
                    Action::Mine { target } => *target,
                    Action::Scan { target } => *target,
                    Action::Fortify { target } => *target,
                    Action::Communicate { .. } => return true,
                    Action::Idle => return true,
                };

                // NAND gate: action allowed if NOT (any constraint violated)
                let violates_boundary = !trust_deed.check_boundary(&target_position);
                let exceeds_resource_limit = match action {
                    Action::Build { material_id, .. } => {
                        !trust_deed.check_resources(*material_id, 1)
                    }
                    _ => false,
                };

                // Check hazard risk
                let high_hazard_risk = if let Some(voxel) = world.get(&target_position) {
                    voxel.hazard_potential.mean > trust_deed.hazard_risk_threshold
                } else {
                    false
                };

                // NAND: allow if NOT (any violation)
                !(violates_boundary || exceeds_resource_limit || high_hazard_risk)
            })
            .collect()
    }
}

impl Default for SafetyKernel {
    fn default() -> Self {
        Self::new()
    }
}

/// Five-stage execution pipeline
pub struct ExecutionPipeline {
    world: SparseVoxelOctree,
    minefield: Minefield,
    ledger: SpatialLedger,
    safety_kernel: SafetyKernel,
    agent_keypairs: HashMap<uuid::Uuid, Keypair>,
    current_time: u64,
}

impl ExecutionPipeline {
    pub fn new(
        world: SparseVoxelOctree,
        minefield: Minefield,
        ledger: SpatialLedger,
    ) -> Self {
        Self {
            world,
            minefield,
            ledger,
            safety_kernel: SafetyKernel::new(),
            agent_keypairs: HashMap::new(),
            current_time: 0,
        }
    }

    /// Register agent with keypair
    pub fn register_agent(&mut self, agent: &Agent, keypair: Keypair) {
        self.agent_keypairs.insert(agent.id, keypair);
        self.ledger.register_agent(agent.id, keypair.public);
    }

    /// Execute full pipeline for one agent
    pub fn execute_agent_tick(&mut self, agent: &mut Agent) -> Result<ActionOutcome, String> {
        // Stage 1: Perceive local spatial tensor and update latent world model
        let observation = self.stage1_perceive(agent)?;

        // Stage 2: Compute prediction error and evaluate epistemic value
        let epistemic_values = self.stage2_evaluate_epistemic(agent, &observation);

        // Stage 3: Filter actions through NAND-based safety and trust-deed constraints
        let candidate_actions = vec![agent.select_action(&observation)];
        let safe_actions = self.stage3_filter_safety(agent.id, candidate_actions);

        if safe_actions.is_empty() {
            return Ok(ActionOutcome::new());
        }

        let action = safe_actions[0];

        // Stage 4: Execute atomic voxel mutation
        let outcome = self.stage4_execute_action(agent, action)?;

        // Stage 5: Commit state transition and cryptographic proof
        self.stage5_commit_transition(agent, action, &outcome)?;

        Ok(outcome)
    }

    /// Stage 1: Perception
    fn stage1_perceive(&mut self, agent: &Agent) -> Result<Observation, String> {
        // Get local voxels (27x27x27 cube around agent)
        let local_voxels = self.world.get_in_radius(&agent.position, 13);

        // Get hazard signals
        let hazard_signals = self.minefield.get_hazard_signals(
            &agent.position,
            64,
            &[], // Simplified - would need other agents' observations
        );

        // Get agent messages (simplified - would use message passing system)
        let agent_messages = Vec::new();

        Ok(Observation {
            local_voxels,
            agent_messages,
            hazard_signals,
            timestamp: self.current_time,
        })
    }

    /// Stage 2: Prediction error and epistemic value
    fn stage2_evaluate_epistemic(
        &self,
        agent: &Agent,
        observation: &Observation,
    ) -> Vec<(Position, f32)> {
        let mut epistemic_values = Vec::new();

        // Evaluate unexplored positions
        for dx in -10..=10 {
            for dy in -5..=5 {
                for dz in -10..=10 {
                    let pos = Position::new(
                        agent.position.x + dx,
                        agent.position.y + dy,
                        agent.position.z + dz,
                    );

                    if self.world.get(&pos).is_none() {
                        let value = agent.belief_state.epistemic_value(&pos);
                        epistemic_values.push((pos, value));
                    }
                }
            }
        }

        epistemic_values.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        epistemic_values.truncate(10); // Top 10 positions

        epistemic_values
    }

    /// Stage 3: Safety filtering
    fn stage3_filter_safety(
        &self,
        agent_id: uuid::Uuid,
        actions: Vec<Action>,
    ) -> Vec<Action> {
        self.safety_kernel.filter_actions(
            agent_id,
            actions,
            &self.world,
            &self.minefield,
        )
    }

    /// Stage 4: Execute action
    fn stage4_execute_action(
        &mut self,
        agent: &mut Agent,
        action: Action,
    ) -> Result<ActionOutcome, String> {
        let mut outcome = ActionOutcome::new();

        match action {
            Action::Move { direction } => {
                let (dx, dy, dz) = direction.to_offset();
                let new_position = Position::new(
                    agent.position.x + dx,
                    agent.position.y + dy,
                    agent.position.z + dz,
                );

                // Check for mine triggers
                let explosions = self.minefield.check_triggers(agent);
                if !explosions.is_empty() {
                    outcome.hazard_encounters = explosions.len() as u32;
                    // Handle explosion consequences
                    self.handle_explosions(&explosions)?;
                    return Ok(outcome);
                }

                agent.position = new_position;
                outcome.success = true;
            }

            Action::Build { target, material_id } => {
                if agent.inventory.has_material(material_id, 1) {
                    let mut voxel = Voxel::new();
                    voxel.density = 1.0;
                    voxel.material_id = material_id;
                    voxel.owner_agent_id = Some(agent.id);
                    voxel.timestamp = self.current_time;

                    self.world.set(target, voxel)?;
                    agent.inventory.remove_material(material_id, 1);

                    outcome.success = true;
                    outcome.structures_built = 1;
                    outcome.resource_cost = 1;
                }
            }

            Action::Mine { target } => {
                if let Some(voxel) = self.world.remove(&target) {
                    if voxel.material_id > 0 {
                        agent.inventory.add_material(voxel.material_id, 1);
                        outcome.success = true;
                    }
                }
            }

            Action::Scan { target } => {
                if self.world.get(&target).is_none() {
                    outcome.new_voxels_discovered = 1;
                    outcome.epistemic_gain = 0.5;
                }
                outcome.success = true;
            }

            Action::Fortify { target } => {
                if let Some(voxel) = self.world.get(&target) {
                    let mut fortified = voxel.clone();
                    fortified.density = (fortified.density * 1.5).min(1.0);
                    self.world.set(target, fortified)?;
                    outcome.success = true;
                    outcome.structure_stability = 0.5;
                }
            }

            Action::Communicate { .. } => {
                // Message passing would be implemented here
                outcome.success = true;
            }

            Action::Idle => {
                outcome.success = true;
            }
        }

        Ok(outcome)
    }

    /// Stage 5: Commit to ledger
    fn stage5_commit_transition(
        &mut self,
        agent: &Agent,
        action: Action,
        outcome: &ActionOutcome,
    ) -> Result<(), String> {
        let old_voxel = Voxel::new();
        let new_voxel = Voxel::new();

        let mut transition = StateTransition::new(
            agent.id,
            action,
            &old_voxel,
            &new_voxel,
            self.current_time,
        );

        // Sign transition
        if let Some(keypair) = self.agent_keypairs.get(&agent.id) {
            transition.sign(keypair);
        } else {
            return Err("Agent keypair not found".to_string());
        }

        // Append to ledger
        self.ledger.append_transition(transition)?;

        Ok(())
    }

    /// Handle mine explosions
    fn handle_explosions(&mut self, explosions: &[MineExplosion]) -> Result<(), String> {
        for explosion in explosions {
            let affected_positions = explosion.get_affected_positions();

            for pos in affected_positions {
                if let Some(voxel) = self.world.get(&pos) {
                    let damage = explosion.compute_damage(&pos);
                    
                    if damage > 0.5 {
                        // Vaporize voxel
                        self.world.remove(&pos);
                    } else {
                        // Reduce density
                        let mut damaged = voxel.clone();
                        damaged.density *= 1.0 - damage;
                        self.world.set(pos, damaged)?;
                    }
                }
            }
        }

        Ok(())
    }

    /// Advance simulation time
    pub fn tick(&mut self) {
        self.current_time += 1;
    }

    /// Commit pending ledger block
    pub fn commit_ledger_block(&mut self) -> Result<(), String> {
        self.ledger.commit_block(self.current_time)
    }

    /// Get current time
    pub fn current_time(&self) -> u64 {
        self.current_time
    }

    /// Get world reference
    pub fn world(&self) -> &SparseVoxelOctree {
        &self.world
    }

    /// Get minefield reference
    pub fn minefield(&self) -> &Minefield {
        &self.minefield
    }

    /// Get ledger reference
    pub fn ledger(&self) -> &SpatialLedger {
        &self.ledger
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::agents::agent::AgentRole;
    use ed25519_dalek::Keypair;
    use rand::rngs::OsRng;

    #[test]
    fn test_trust_deed() {
        let agent_id = uuid::Uuid::new_v4();
        let mut trust_deed = TrustDeed::new(agent_id);

        trust_deed.add_territory(
            Position::new(0, 0, 0),
            Position::new(100, 100, 100),
        );

        assert!(trust_deed.check_boundary(&Position::new(50, 50, 50)));
        assert!(!trust_deed.check_boundary(&Position::new(150, 50, 50)));
    }

    #[test]
    fn test_safety_kernel() {
        let kernel = SafetyKernel::new();
        let world = SparseVoxelOctree::new(1024, 256, 1024);
        let minefield = Minefield::new(12345, 0.20);

        let actions = vec![Action::Idle];
        let filtered = kernel.filter_actions(
            uuid::Uuid::new_v4(),
            actions,
            &world,
            &minefield,
        );

        assert_eq!(filtered.len(), 1);
    }

    #[test]
    fn test_execution_pipeline() {
        let world = SparseVoxelOctree::new(1024, 256, 1024);
        let minefield = Minefield::new(12345, 0.20);
        let ledger = SpatialLedger::new([42u8; 32]);

        let mut pipeline = ExecutionPipeline::new(world, minefield, ledger);
        let mut agent = Agent::new(AgentRole::Pioneer, Position::new(100, 100, 100));

        let mut csprng = OsRng{};
        let keypair = Keypair::generate(&mut csprng);
        pipeline.register_agent(&agent, keypair);

        let result = pipeline.execute_agent_tick(&mut agent);
        assert!(result.is_ok());
    }
}

// Made with Bob
