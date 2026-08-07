// Sovereign Voxel Civilization Simulator
// Command-line interface for running simulations

use sovereign_voxel_civilization::{Simulation, SimulationConfig, AgentCounts};
use std::time::Instant;

fn main() {
    // Initialize logger
    env_logger::Builder::from_default_env()
        .filter_level(log::LevelFilter::Info)
        .init();

    log::info!("=== Sovereign Voxel Civilization Simulator ===");
    log::info!("DeepMind-inspired Neural-Symbolic Hybrid Framework");
    log::info!("");

    // Parse command line arguments
    let args: Vec<String> = std::env::args().collect();
    let ticks = if args.len() > 1 {
        args[1].parse::<u64>().unwrap_or(1000)
    } else {
        1000
    };

    // Create simulation configuration
    let config = SimulationConfig {
        world_dimensions: (1024, 256, 1024),
        mine_count: 500,
        entropy_bound: 0.20,
        genesis_seed: generate_seed(),
        agent_counts: AgentCounts {
            pioneers: 10,
            architects: 5,
            sentinels: 5,
        },
    };

    log::info!("Configuration:");
    log::info!("  World: {}x{}x{}", 
        config.world_dimensions.0,
        config.world_dimensions.1,
        config.world_dimensions.2
    );
    log::info!("  Mines: {}", config.mine_count);
    log::info!("  Entropy Bound: {}", config.entropy_bound);
    log::info!("  Agents: {} pioneers, {} architects, {} sentinels",
        config.agent_counts.pioneers,
        config.agent_counts.architects,
        config.agent_counts.sentinels
    );
    log::info!("  Simulation Ticks: {}", ticks);
    log::info!("");

    // Create simulation
    log::info!("Initializing simulation...");
    let mut simulation = Simulation::new(config);
    log::info!("Simulation initialized with {} agents", simulation.agents.len());
    log::info!("");

    // Run simulation
    log::info!("Starting simulation...");
    let start_time = Instant::now();
    
    match simulation.run(ticks) {
        Ok(stats) => {
            let elapsed = start_time.elapsed();
            
            log::info!("");
            log::info!("=== Simulation Complete ===");
            log::info!("Duration: {:.2}s", elapsed.as_secs_f64());
            log::info!("Ticks per second: {:.2}", ticks as f64 / elapsed.as_secs_f64());
            log::info!("");
            log::info!("Final Statistics:");
            log::info!("  Total Agents: {}", stats.total_agents);
            log::info!("  Total Voxels: {}", stats.total_voxels);
            log::info!("  Active Mines: {}", stats.active_mines);
            log::info!("  Ledger Blocks: {}", stats.ledger_blocks);
            log::info!("  Total Transitions: {}", stats.total_transitions);
            log::info!("  Structures Built: {}", stats.structures_built);
            log::info!("  Voxels Discovered: {}", stats.voxels_discovered);
            log::info!("  Hazard Encounters: {}", stats.hazard_encounters);
            log::info!("  Threats Detected: {}", stats.threats_detected);
            log::info!("  Errors: {}", stats.errors);
            log::info!("");

            // Calculate performance metrics
            let transitions_per_second = stats.total_transitions as f64 / elapsed.as_secs_f64();
            log::info!("Performance Metrics:");
            log::info!("  Transitions/sec: {:.2}", transitions_per_second);
            log::info!("  Avg reward per agent: {:.2}", 
                simulation.agents.iter().map(|a| a.reward_total).sum::<f32>() / simulation.agents.len() as f32
            );
            log::info!("");

            // Verify ledger integrity
            log::info!("Verifying ledger integrity...");
            match simulation.pipeline.ledger().verify_integrity() {
                Ok(_) => log::info!("✓ Ledger integrity verified"),
                Err(e) => log::error!("✗ Ledger integrity check failed: {}", e),
            }
        }
        Err(e) => {
            log::error!("Simulation failed: {}", e);
            std::process::exit(1);
        }
    }

    log::info!("");
    log::info!("Simulation complete. Exiting.");
}

/// Generate random seed from system entropy
fn generate_seed() -> [u8; 32] {
    use rand::RngCore;
    let mut seed = [0u8; 32];
    rand::thread_rng().fill_bytes(&mut seed);
    seed
}

// Made with Bob
