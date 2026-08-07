// Basic Simulation Example
// Demonstrates how to create and run a simple simulation

use sovereign_voxel_civilization::{
    Simulation, SimulationConfig, AgentCounts,
};

fn main() {
    // Initialize logger
    env_logger::Builder::from_default_env()
        .filter_level(log::LevelFilter::Info)
        .init();

    println!("=== Basic Simulation Example ===\n");

    // Create a small-scale simulation for demonstration
    let config = SimulationConfig {
        world_dimensions: (256, 128, 256),
        mine_count: 50,
        entropy_bound: 0.20,
        genesis_seed: [42u8; 32], // Fixed seed for reproducibility
        agent_counts: AgentCounts {
            pioneers: 3,
            architects: 2,
            sentinels: 1,
        },
    };

    println!("Configuration:");
    println!("  World: {}x{}x{}", 
        config.world_dimensions.0,
        config.world_dimensions.1,
        config.world_dimensions.2
    );
    println!("  Agents: {} total", 
        config.agent_counts.pioneers + 
        config.agent_counts.architects + 
        config.agent_counts.sentinels
    );
    println!("  Mines: {}", config.mine_count);
    println!();

    // Create simulation
    println!("Initializing simulation...");
    let mut simulation = Simulation::new(config);
    println!("✓ Simulation initialized with {} agents\n", simulation.agents.len());

    // Run simulation
    println!("Running simulation for 100 ticks...");
    match simulation.run(100) {
        Ok(stats) => {
            println!("✓ Simulation complete!\n");
            
            println!("Results:");
            println!("  Structures built: {}", stats.structures_built);
            println!("  Voxels discovered: {}", stats.voxels_discovered);
            println!("  Hazard encounters: {}", stats.hazard_encounters);
            println!("  Threats detected: {}", stats.threats_detected);
            println!("  Total transitions: {}", stats.total_transitions);
            println!();

            // Show agent rewards
            println!("Agent Performance:");
            for (i, agent) in simulation.agents.iter().enumerate() {
                println!("  Agent {} ({:?}): reward = {:.2}", 
                    i, agent.role, agent.reward_total);
            }
        }
        Err(e) => {
            eprintln!("✗ Simulation failed: {}", e);
            std::process::exit(1);
        }
    }

    println!("\nExample complete!");
}

// Made with Bob
