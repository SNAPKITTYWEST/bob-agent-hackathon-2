# Quickstart Guide

Get started with the Sovereign Voxel Civilization Engine in minutes.

## Prerequisites

- Rust 1.70 or later
- Cargo (comes with Rust)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd sovereign-voxel-civilization
```

2. Build the project:
```bash
cargo build --release
```

3. Run tests:
```bash
cargo test
```

## Running Your First Simulation

### Basic Simulation

Run a simulation with default parameters (1000 ticks):

```bash
cargo run --release --bin svc-simulator
```

### Custom Duration

Run for 5000 ticks:

```bash
cargo run --release --bin svc-simulator 5000
```

### Expected Output

```
=== Sovereign Voxel Civilization Simulator ===
DeepMind-inspired Neural-Symbolic Hybrid Framework

Configuration:
  World: 1024x256x1024
  Mines: 500
  Entropy Bound: 0.20
  Agents: 10 pioneers, 5 architects, 5 sentinels
  Simulation Ticks: 1000

Initializing simulation...
Simulation initialized with 20 agents

Starting simulation...
[INFO] Tick 0/1000 - Stats: ...
[INFO] Tick 1000/1000 - Stats: ...

=== Simulation Complete ===
Duration: 12.34s
Ticks per second: 81.03

Final Statistics:
  Total Agents: 20
  Total Voxels: 1523
  Active Mines: 487
  Ledger Blocks: 10
  Total Transitions: 15234
  ...
```

## Using as a Library

Add to your `Cargo.toml`:

```toml
[dependencies]
sovereign-voxel-civilization = { path = "../sovereign-voxel-civilization" }
```

### Example Code

```rust
use sovereign_voxel_civilization::{
    Simulation, SimulationConfig, AgentCounts
};

fn main() {
    // Create custom configuration
    let config = SimulationConfig {
        world_dimensions: (512, 128, 512),
        mine_count: 200,
        entropy_bound: 0.20,
        genesis_seed: [42u8; 32],
        agent_counts: AgentCounts {
            pioneers: 5,
            architects: 3,
            sentinels: 2,
        },
    };

    // Initialize simulation
    let mut simulation = Simulation::new(config);

    // Run for 1000 ticks
    match simulation.run(1000) {
        Ok(stats) => {
            println!("Simulation complete!");
            println!("Structures built: {}", stats.structures_built);
            println!("Voxels discovered: {}", stats.voxels_discovered);
        }
        Err(e) => eprintln!("Error: {}", e),
    }
}
```

## Key Concepts

### Agent Roles

- **Pioneer**: Explores the world, discovers new voxels, maps hazards
- **Architect**: Builds structures, manages resources, plans layouts
- **Sentinel**: Detects threats, protects other agents, enforces boundaries

### World Model

- 3D sparse voxel octree (1024×256×1024 default)
- Each voxel has: density, material, hazard potential, owner
- O(log N) access time for voxel operations

### Minefield Physics

- Mines have probabilistic triggers
- Adaptive density based on agent activity
- Multi-agent consensus required for detection
- Explosions cause structural collapse

### Cryptographic Ledger

- All state transitions are signed and recorded
- Deterministic replay from genesis seed
- Merkle tree verification for integrity
- WORM (Write-Once-Read-Many) storage

## Configuration Options

### World Dimensions

```rust
world_dimensions: (width, height, depth)
```

Larger worlds require more memory but allow more exploration.

### Mine Count

```rust
mine_count: usize
```

More mines increase difficulty and require better coordination.

### Entropy Bound

```rust
entropy_bound: f32  // 0.0 to 1.0
```

Maximum allowed system entropy (H ≤ 0.20 recommended).

### Agent Counts

```rust
agent_counts: AgentCounts {
    pioneers: usize,
    architects: usize,
    sentinels: usize,
}
```

Balance exploration, building, and defense.

## Performance Tips

1. **Release Mode**: Always use `--release` for production runs
2. **World Size**: Start small (256×128×256) for testing
3. **Agent Count**: 10-20 agents is optimal for most scenarios
4. **Tick Duration**: 1000-10000 ticks for meaningful results

## Troubleshooting

### Out of Memory

Reduce world dimensions or agent count:
```rust
world_dimensions: (512, 128, 512),
agent_counts: AgentCounts { pioneers: 5, architects: 2, sentinels: 2 }
```

### Slow Performance

- Use release mode: `cargo run --release`
- Reduce mine count
- Decrease agent count

### Ledger Integrity Errors

This indicates a bug in state transitions. Please report with:
- Genesis seed
- Configuration used
- Error message

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Explore [examples/](examples/) for advanced usage
- Check [tests/](tests/) for integration examples

## Getting Help

- GitHub Issues: Report bugs and request features
- Documentation: Run `cargo doc --open`
- Examples: See `examples/` directory

## License

MIT License - See LICENSE file for details