// Multi-Agent Reinforcement Learning Framework
// Role-based agent implementation with POMDP coordination

use uuid::Uuid;
use std::collections::HashMap;
use crate::world::octree::{Position, Voxel};

/// Agent role types
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AgentRole {
    Pioneer,   // Exploration and spatial mapping
    Architect, // Structure building and resource management
    Sentinel,  // Hazard detection and threat mitigation
}

/// Agent action types
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Action {
    Move { direction: Direction },
    Build { target: Position, material_id: u16 },
    Mine { target: Position },
    Scan { target: Position },
    Fortify { target: Position },
    Communicate { message_type: MessageType },
    Idle,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Direction {
    North,
    South,
    East,
    West,
    Up,
    Down,
}

impl Direction {
    pub fn to_offset(&self) -> (i32, i32, i32) {
        match self {
            Direction::North => (0, 0, -1),
            Direction::South => (0, 0, 1),
            Direction::East => (1, 0, 0),
            Direction::West => (-1, 0, 0),
            Direction::Up => (0, 1, 0),
            Direction::Down => (0, -1, 0),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum MessageType {
    Discovery,
    Warning,
    Coordination,
    ResourceClaim,
}

/// Agent observation from environment
#[derive(Debug, Clone)]
pub struct Observation {
    pub local_voxels: Vec<(Position, Voxel)>,
    pub agent_messages: Vec<Message>,
    pub hazard_signals: Vec<HazardSignal>,
    pub timestamp: u64,
}

#[derive(Debug, Clone)]
pub struct Message {
    pub sender_id: Uuid,
    pub message_type: MessageType,
    pub position: Position,
    pub data: Vec<u8>,
    pub timestamp: u64,
}

#[derive(Debug, Clone)]
pub struct HazardSignal {
    pub position: Position,
    pub intensity: f32,
    pub confidence: f32,
}

/// Agent belief state for POMDP
#[derive(Debug, Clone)]
pub struct BeliefState {
    pub position_belief: HashMap<Position, f32>,
    pub hazard_belief: HashMap<Position, f32>,
    pub resource_belief: HashMap<Position, f32>,
    pub agent_belief: HashMap<Uuid, Position>,
}

impl BeliefState {
    pub fn new() -> Self {
        Self {
            position_belief: HashMap::new(),
            hazard_belief: HashMap::new(),
            resource_belief: HashMap::new(),
            agent_belief: HashMap::new(),
        }
    }

    /// Update belief based on observation (Bayesian update)
    pub fn update(&mut self, observation: &Observation) {
        // Update hazard beliefs
        for signal in &observation.hazard_signals {
            let current = self.hazard_belief.get(&signal.position).unwrap_or(&0.5);
            // Bayesian update: P(H|O) ∝ P(O|H) * P(H)
            let likelihood = signal.confidence;
            let prior = *current;
            let posterior = (likelihood * prior) / (likelihood * prior + (1.0 - likelihood) * (1.0 - prior));
            self.hazard_belief.insert(signal.position, posterior);
        }

        // Update resource beliefs from voxel observations
        for (pos, voxel) in &observation.local_voxels {
            if voxel.material_id > 0 {
                self.resource_belief.insert(*pos, voxel.density);
            }
        }

        // Update agent beliefs from messages
        for message in &observation.agent_messages {
            self.agent_belief.insert(message.sender_id, message.position);
        }
    }

    /// Compute epistemic value (information gain) for a position
    pub fn epistemic_value(&self, pos: &Position) -> f32 {
        // Higher value for uncertain positions
        let hazard_uncertainty = 1.0 - self.hazard_belief.get(pos).unwrap_or(&0.5).abs();
        let resource_uncertainty = 1.0 - self.resource_belief.get(pos).unwrap_or(&0.5).abs();
        
        (hazard_uncertainty + resource_uncertainty) / 2.0
    }
}

impl Default for BeliefState {
    fn default() -> Self {
        Self::new()
    }
}

/// Agent inventory and resources
#[derive(Debug, Clone)]
pub struct Inventory {
    pub materials: HashMap<u16, u32>,
    pub energy: f32,
    pub max_capacity: u32,
}

impl Inventory {
    pub fn new(max_capacity: u32) -> Self {
        Self {
            materials: HashMap::new(),
            energy: 100.0,
            max_capacity,
        }
    }

    pub fn add_material(&mut self, material_id: u16, amount: u32) -> bool {
        let current_total: u32 = self.materials.values().sum();
        if current_total + amount <= self.max_capacity {
            *self.materials.entry(material_id).or_insert(0) += amount;
            true
        } else {
            false
        }
    }

    pub fn remove_material(&mut self, material_id: u16, amount: u32) -> bool {
        if let Some(current) = self.materials.get_mut(&material_id) {
            if *current >= amount {
                *current -= amount;
                return true;
            }
        }
        false
    }

    pub fn has_material(&self, material_id: u16, amount: u32) -> bool {
        self.materials.get(&material_id).unwrap_or(&0) >= &amount
    }
}

/// Latent embedding from perception
#[derive(Debug, Clone)]
pub struct LatentEmbedding {
    pub vector: Vec<f32>,
    pub dimension: usize,
}

impl LatentEmbedding {
    pub fn new(dimension: usize) -> Self {
        Self {
            vector: vec![0.0; dimension],
            dimension,
        }
    }

    pub fn from_observation(observation: &Observation) -> Self {
        // Simplified encoding - in practice would use neural network
        let mut embedding = Self::new(256);
        
        // Encode voxel density
        for (i, (_, voxel)) in observation.local_voxels.iter().enumerate().take(64) {
            embedding.vector[i] = voxel.density;
        }

        // Encode hazard signals
        for (i, signal) in observation.hazard_signals.iter().enumerate().take(64) {
            embedding.vector[64 + i] = signal.intensity;
        }

        // Encode message presence
        embedding.vector[128] = observation.agent_messages.len() as f32 / 10.0;

        embedding
    }
}

/// Main agent structure
pub struct Agent {
    pub id: Uuid,
    pub role: AgentRole,
    pub position: Position,
    pub orientation: Direction,
    pub belief_state: BeliefState,
    pub inventory: Inventory,
    pub hidden_state: Vec<f32>,
    pub experience_buffer: Vec<Experience>,
    pub reward_total: f32,
}

#[derive(Debug, Clone)]
pub struct Experience {
    pub observation: Observation,
    pub action: Action,
    pub reward: f32,
    pub next_observation: Observation,
}

impl Agent {
    pub fn new(role: AgentRole, position: Position) -> Self {
        Self {
            id: Uuid::new_v4(),
            role,
            position,
            orientation: Direction::North,
            belief_state: BeliefState::new(),
            inventory: Inventory::new(100),
            hidden_state: vec![0.0; 256],
            experience_buffer: Vec::new(),
            reward_total: 0.0,
        }
    }

    /// Perceive environment and update belief state
    pub fn perceive(&mut self, observation: Observation) {
        self.belief_state.update(&observation);
    }

    /// Select action based on role and current state
    pub fn select_action(&self, observation: &Observation) -> Action {
        match self.role {
            AgentRole::Pioneer => self.pioneer_policy(observation),
            AgentRole::Architect => self.architect_policy(observation),
            AgentRole::Sentinel => self.sentinel_policy(observation),
        }
    }

    /// Pioneer exploration policy
    fn pioneer_policy(&self, observation: &Observation) -> Action {
        // Find highest epistemic value position
        let mut best_value = 0.0;
        let mut best_direction = Direction::North;

        for direction in &[
            Direction::North,
            Direction::South,
            Direction::East,
            Direction::West,
            Direction::Up,
            Direction::Down,
        ] {
            let (dx, dy, dz) = direction.to_offset();
            let target = Position::new(
                self.position.x + dx,
                self.position.y + dy,
                self.position.z + dz,
            );

            let value = self.belief_state.epistemic_value(&target);
            let hazard_risk = self.belief_state.hazard_belief.get(&target).unwrap_or(&0.3);

            // Balance exploration value against hazard risk
            let adjusted_value = value * (1.0 - hazard_risk);

            if adjusted_value > best_value {
                best_value = adjusted_value;
                best_direction = *direction;
            }
        }

        if best_value > 0.3 {
            Action::Move {
                direction: best_direction,
            }
        } else {
            Action::Scan {
                target: self.position,
            }
        }
    }

    /// Architect building policy
    fn architect_policy(&self, observation: &Observation) -> Action {
        // Look for buildable positions with resources
        for (pos, voxel) in &observation.local_voxels {
            if voxel.density < 0.1 && self.inventory.has_material(1, 1) {
                // Empty space - consider building
                let hazard_risk = self.belief_state.hazard_belief.get(pos).unwrap_or(&0.3);
                
                if *hazard_risk < 0.4 {
                    return Action::Build {
                        target: *pos,
                        material_id: 1,
                    };
                }
            }
        }

        // Move towards resources
        Action::Move {
            direction: Direction::North,
        }
    }

    /// Sentinel patrol policy
    fn sentinel_policy(&self, observation: &Observation) -> Action {
        // Scan for hazards
        if !observation.hazard_signals.is_empty() {
            let highest_threat = observation
                .hazard_signals
                .iter()
                .max_by(|a, b| a.intensity.partial_cmp(&b.intensity).unwrap())
                .unwrap();

            if highest_threat.intensity > 0.7 {
                return Action::Communicate {
                    message_type: MessageType::Warning,
                };
            }

            return Action::Scan {
                target: highest_threat.position,
            };
        }

        // Patrol movement
        Action::Move {
            direction: Direction::East,
        }
    }

    /// Compute reward based on role
    pub fn compute_reward(&self, action: &Action, outcome: &ActionOutcome) -> f32 {
        match self.role {
            AgentRole::Pioneer => {
                let mut reward = 0.0;
                reward += outcome.new_voxels_discovered as f32 * 10.0;
                reward -= outcome.hazard_encounters as f32 * 50.0;
                reward += outcome.epistemic_gain * 5.0;
                reward
            }
            AgentRole::Architect => {
                let mut reward = 0.0;
                reward += outcome.structures_built as f32 * 20.0;
                reward += outcome.structure_stability * 10.0;
                reward -= outcome.resource_cost as f32 * 0.5;
                reward
            }
            AgentRole::Sentinel => {
                let mut reward = 0.0;
                reward += outcome.threats_detected as f32 * 15.0;
                reward += outcome.agents_protected as f32 * 25.0;
                reward -= outcome.false_positives as f32 * 5.0;
                reward
            }
        }
    }

    /// Update hidden state using Jordan-gated transition
    pub fn update_hidden_state(&mut self, observation: &Observation) {
        let embedding = LatentEmbedding::from_observation(observation);

        // Simplified Jordan-gated update
        // h_t = g_t ⊙ tanh(W_h · [s_t, h_{t-1}])
        for i in 0..self.hidden_state.len().min(embedding.dimension) {
            let gate = sigmoid(self.hidden_state[i] + embedding.vector[i]);
            let update = (self.hidden_state[i] + embedding.vector[i]).tanh();
            self.hidden_state[i] = gate * update;
        }
    }

    /// Store experience for learning
    pub fn store_experience(&mut self, experience: Experience) {
        self.experience_buffer.push(experience);
        
        // Keep buffer size manageable
        if self.experience_buffer.len() > 1000 {
            self.experience_buffer.remove(0);
        }
    }
}

/// Action outcome for reward computation
#[derive(Debug, Clone)]
pub struct ActionOutcome {
    pub success: bool,
    pub new_voxels_discovered: u32,
    pub hazard_encounters: u32,
    pub epistemic_gain: f32,
    pub structures_built: u32,
    pub structure_stability: f32,
    pub resource_cost: u32,
    pub threats_detected: u32,
    pub agents_protected: u32,
    pub false_positives: u32,
}

impl ActionOutcome {
    pub fn new() -> Self {
        Self {
            success: false,
            new_voxels_discovered: 0,
            hazard_encounters: 0,
            epistemic_gain: 0.0,
            structures_built: 0,
            structure_stability: 0.0,
            resource_cost: 0,
            threats_detected: 0,
            agents_protected: 0,
            false_positives: 0,
        }
    }
}

impl Default for ActionOutcome {
    fn default() -> Self {
        Self::new()
    }
}

fn sigmoid(x: f32) -> f32 {
    1.0 / (1.0 + (-x).exp())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_creation() {
        let agent = Agent::new(AgentRole::Pioneer, Position::new(0, 0, 0));
        assert_eq!(agent.role, AgentRole::Pioneer);
        assert_eq!(agent.position, Position::new(0, 0, 0));
    }

    #[test]
    fn test_belief_update() {
        let mut belief = BeliefState::new();
        let observation = Observation {
            local_voxels: vec![],
            agent_messages: vec![],
            hazard_signals: vec![HazardSignal {
                position: Position::new(1, 1, 1),
                intensity: 0.8,
                confidence: 0.9,
            }],
            timestamp: 0,
        };

        belief.update(&observation);
        assert!(belief.hazard_belief.contains_key(&Position::new(1, 1, 1)));
    }

    #[test]
    fn test_inventory() {
        let mut inventory = Inventory::new(100);
        assert!(inventory.add_material(1, 50));
        assert!(inventory.has_material(1, 50));
        assert!(inventory.remove_material(1, 25));
        assert!(inventory.has_material(1, 25));
    }
}

// Made with Bob
