// Sovereign Voxel Civilization Engine
// DeepMind-inspired neural-symbolic hybrid simulation framework

pub mod world;
pub mod agents;
pub mod hazards;
pub mod ledger;
pub mod pipeline;
pub mod perception;
pub mod reasoning;

// Re-export main types
pub use world::octree::{SparseVoxelOctree, Position, Voxel, Bounds};
pub use agents::agent::{Agent, AgentRole, Action, Observation};
pub use hazards::minefield::{Minefield, Mine, MineExplosion};
pub use ledger::state_ledger::{SpatialLedger, StateTransition, ReplayEngine};
pub use pipeline::execution::{ExecutionPipeline, TrustDeed, SafetyKernel};

/// Simulation configuration
#[derive(Debug, Clone)]
pub struct SimulationConfig {
    pub world_dimensions: (i32, i32, i32),
    pub mine_count: usize,
    pub entropy_bound: f32,
    pub genesis_seed: [u8; 32],
    pub agent_counts: AgentCounts,
}

#[derive(Debug, Clone)]
pub struct AgentCounts {
    pub pioneers: usize,
    pub architects: usize,
    pub sentinels: usize,
}

impl Default for SimulationConfig {
    fn default() -> Self {
        Self {
            world_dimensions: (1024, 256, 1024),
            mine_count: 1000,
            entropy_bound: 0.20,
            genesis_seed: [42u8; 32],
            agent_counts: AgentCounts {
                pioneers: 10,
                architects: 5,
                sentinels: 5,
            },
        }
    }
}

/// Main simulation engine
pub struct Simulation {
    pub config: SimulationConfig,
    pub pipeline: ExecutionPipeline,
    pub agents: Vec<Agent>,
}

impl Simulation {
    /// Create new simulation with config
    pub fn new(config: SimulationConfig) -> Self {
        // Initialize world
        let world = SparseVoxelOctree::new(
            config.world_dimensions.0,
            config.world_dimensions.1,
            config.world_dimensions.2,
        );

        // Initialize minefield
        let mut minefield = Minefield::new(
            u64::from_le_bytes(config.genesis_seed[0..8].try_into().unwrap()),
            config.entropy_bound,
        );
        minefield.initialize(config.mine_count, config.world_dimensions);

        // Initialize ledger
        let ledger = SpatialLedger::new(config.genesis_seed);

        // Create pipeline
        let pipeline = ExecutionPipeline::new(world, minefield, ledger);

        // Create agents
        let mut agents = Vec::new();

        // Spawn pioneers
        for i in 0..config.agent_counts.pioneers {
            let pos = Position::new(
                100 + (i as i32 * 50),
                100,
                100,
            );
            agents.push(Agent::new(AgentRole::Pioneer, pos));
        }

        // Spawn architects
        for i in 0..config.agent_counts.architects {
            let pos = Position::new(
                200 + (i as i32 * 50),
                100,
                200,
            );
            agents.push(Agent::new(AgentRole::Architect, pos));
        }

        // Spawn sentinels
        for i in 0..config.agent_counts.sentinels {
            let pos = Position::new(
                300 + (i as i32 * 50),
                100,
                300,
            );
            agents.push(Agent::new(AgentRole::Sentinel, pos));
        }

        Self {
            config,
            pipeline,
            agents,
        }
    }

    /// Run simulation for N ticks
    pub fn run(&mut self, ticks: u64) -> Result<SimulationStats, String> {
        let mut stats = SimulationStats::new();

        for tick in 0..ticks {
            // Execute each agent
            for agent in &mut self.agents {
                match self.pipeline.execute_agent_tick(agent) {
                    Ok(outcome) => {
                        stats.record_outcome(&outcome);
                        let reward = agent.compute_reward(&Action::Idle, &outcome);
                        agent.reward_total += reward;
                    }
                    Err(e) => {
                        log::warn!("Agent {} error: {}", agent.id, e);
                        stats.errors += 1;
                    }
                }
            }

            // Advance time
            self.pipeline.tick();

            // Commit ledger block every 100 ticks
            if tick % 100 == 0 {
                if let Err(e) = self.pipeline.commit_ledger_block() {
                    log::error!("Failed to commit ledger block: {}", e);
                }
            }

            // Log progress
            if tick % 1000 == 0 {
                log::info!("Tick {}/{} - Stats: {:?}", tick, ticks, stats);
            }
        }

        Ok(stats)
    }

    /// Get simulation statistics
    pub fn get_stats(&self) -> SimulationStats {
        let mut stats = SimulationStats::new();
        
        stats.total_agents = self.agents.len();
        stats.total_voxels = self.pipeline.world().voxel_count();
        stats.active_mines = self.pipeline.minefield().active_mine_count();
        stats.ledger_blocks = self.pipeline.ledger().block_count();
        stats.total_transitions = self.pipeline.ledger().transition_count();

        stats
    }
}

/// Simulation statistics
#[derive(Debug, Clone)]
pub struct SimulationStats {
    pub total_agents: usize,
    pub total_voxels: usize,
    pub active_mines: usize,
    pub ledger_blocks: usize,
    pub total_transitions: usize,
    pub structures_built: u32,
    pub voxels_discovered: u32,
    pub hazard_encounters: u32,
    pub threats_detected: u32,
    pub errors: u32,
}

impl SimulationStats {
    pub fn new() -> Self {
        Self {
            total_agents: 0,
            total_voxels: 0,
            active_mines: 0,
            ledger_blocks: 0,
            total_transitions: 0,
            structures_built: 0,
            voxels_discovered: 0,
            hazard_encounters: 0,
            threats_detected: 0,
            errors: 0,
        }
    }

    pub fn record_outcome(&mut self, outcome: &agents::agent::ActionOutcome) {
        self.structures_built += outcome.structures_built;
        self.voxels_discovered += outcome.new_voxels_discovered;
        self.hazard_encounters += outcome.hazard_encounters;
        self.threats_detected += outcome.threats_detected;
    }
}

impl Default for SimulationStats {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simulation_creation() {
        let config = SimulationConfig::default();
        let sim = Simulation::new(config);
        
        assert_eq!(sim.agents.len(), 20); // 10 + 5 + 5
    }

    #[test]
    fn test_simulation_run() {
        let config = SimulationConfig {
            agent_counts: AgentCounts {
                pioneers: 2,
                architects: 1,
                sentinels: 1,
            },
            ..Default::default()
        };

        let mut sim = Simulation::new(config);
        let result = sim.run(10);
        
        assert!(result.is_ok());
    }
}

// Made with Bob
