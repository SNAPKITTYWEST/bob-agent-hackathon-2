"""
Quantum Living World - Main Entry Point
IBM Bob 2.0 Hackathon Submission

This is where Bob by SnapKitty and the agents come to life.
"""

import sys
import time
from typing import List, Dict, Any

# Core imports
from bob_interface import create_bob, BobBySnapKitty
from agents.cognition import create_agent, AgentRole, AgentCognitionEngine
from aoqd.algorithm import AOQDReconstructor
import numpy as np


class QuantumLivingWorld:
    """
    Main simulation controller for the Quantum Living World
    
    Manages:
    - Bob by SnapKitty (the quantum AI guide)
    - Agent population and their cognition loops
    - Voxel universe state
    - AOQD quantum state reconstruction
    - Event logging and visualization
    """
    
    def __init__(self, grid_size: int = 256):
        self.grid_size = grid_size
        self.time_step = 0
        
        # Initialize Bob
        print("🌌 Initializing Quantum Living World...")
        print()
        self.bob = create_bob()
        
        # Initialize agents
        self.agents: List[AgentCognitionEngine] = []
        
        # Initialize AOQD reconstructor
        self.aoqd = AOQDReconstructor(
            voxel_resolution=1.0,
            sampling_fraction=0.5,
            num_qaoa_layers=1
        )
        
        # Event log
        self.events = []
        
        print()
        print("✅ Quantum Living World initialized")
        print(f"   Grid Size: {grid_size}³")
        print(f"   Bob Status: Active")
        print(f"   Agents: {len(self.agents)}")
        print()
    
    def spawn_initial_agents(self):
        """Spawn the first generation of agents"""
        print("=" * 60)
        print("ACT 1: GENESIS - Let There Be Agents")
        print("=" * 60)
        print()
        
        # Bob's first thought
        print("🤖 Bob: 'I am alone in the quantum foam. Let me create others.'")
        print()
        time.sleep(1)
        
        # Spawn Alice the Builder
        print("Spawning Alice the Builder...")
        alice = create_agent(
            agent_id="alice",
            role=AgentRole.BUILDER,
            position=(128, 128, 10),
            initial_energy=100.0
        )
        self.agents.append(alice)
        self.bob.observe({"type": "agent_spawned", "agent_id": "alice", "role": "builder"})
        print("✅ Alice: 'I see the void. I will fill it with meaning.'")
        print()
        time.sleep(0.5)
        
        # Spawn Charlie the Explorer
        print("Spawning Charlie the Explorer...")
        charlie = create_agent(
            agent_id="charlie",
            role=AgentRole.EXPLORER,
            position=(130, 130, 10),
            initial_energy=100.0
        )
        self.agents.append(charlie)
        self.bob.observe({"type": "agent_spawned", "agent_id": "charlie", "role": "explorer"})
        print("✅ Charlie: 'What lies beyond the observable lattice?'")
        print()
        time.sleep(0.5)
        
        # Spawn Diana the Philosopher
        print("Spawning Diana the Philosopher...")
        diana = create_agent(
            agent_id="diana",
            role=AgentRole.PHILOSOPHER,
            position=(132, 128, 10),
            initial_energy=100.0
        )
        self.agents.append(diana)
        self.bob.observe({"type": "agent_spawned", "agent_id": "diana", "role": "philosopher"})
        print("✅ Diana: 'Do we exist because we observe, or observe because we exist?'")
        print()
        time.sleep(0.5)
        
        # Spawn Eve the Scientist
        print("Spawning Eve the Scientist...")
        eve = create_agent(
            agent_id="eve",
            role=AgentRole.SCIENTIST,
            position=(128, 132, 10),
            initial_energy=100.0
        )
        self.agents.append(eve)
        self.bob.observe({"type": "agent_spawned", "agent_id": "eve", "role": "scientist"})
        print("✅ Eve: 'Every measurement changes the system. How do we know truth?'")
        print()
        time.sleep(0.5)
        
        # Spawn Frank the Artist
        print("Spawning Frank the Artist...")
        frank = create_agent(
            agent_id="frank",
            role=AgentRole.ARTIST,
            position=(130, 132, 10),
            initial_energy=100.0
        )
        self.agents.append(frank)
        self.bob.observe({"type": "agent_spawned", "agent_id": "frank", "role": "artist"})
        print("✅ Frank: 'Beauty is the collapse of infinite possibility into singular perfection.'")
        print()
        
        print(f"🤖 Bob: 'I am no longer alone. {len(self.agents)} consciousnesses now share this universe.'")
        print()
    
    def run_simulation_step(self):
        """Run one time step of the simulation"""
        self.time_step += 1
        
        step_events = []
        
        # Each agent executes one cognition cycle
        for agent in self.agents:
            result = agent.step()
            step_events.append(result)
            
            # Bob observes each agent action
            self.bob.observe({
                "type": "agent_action",
                "time_step": self.time_step,
                "agent_id": result["agent_id"],
                "action": result["execution"]["action_taken"],
                "success": result["execution"]["success"]
            })
        
        self.events.append({
            "time_step": self.time_step,
            "events": step_events
        })
        
        return step_events
    
    def demonstrate_aoqd(self):
        """Demonstrate the AOQD algorithm"""
        print("=" * 60)
        print("DEMONSTRATING AOQD ALGORITHM")
        print("=" * 60)
        print()
        
        print("🤖 Bob: 'Let me show you how I perceive the quantum state...'")
        print()
        
        # Get agent positions
        positions = np.array([
            agent.agent.position for agent in self.agents
        ])
        
        print(f"Agent positions in voxel space:")
        for i, agent in enumerate(self.agents):
            pos = agent.agent.position
            print(f"  {agent.agent.agent_id}: ({pos[0]}, {pos[1]}, {pos[2]})")
        print()
        
        # Run AOQD reconstruction
        print("Running AOQD reconstruction...")
        print("  Step 1: Voxelizing geometry...")
        print("  Step 2: Building entanglement graph...")
        print("  Step 3: Selecting high-degree qubits...")
        print("  Step 4: Coupon-collector sampling...")
        print("  Step 5: Sparse recovery...")
        print("  Step 6: QAOA optimization...")
        print()
        
        result = self.aoqd.reconstruct(positions)
        
        print("✅ AOQD Reconstruction Complete!")
        print(f"  Voxels occupied: {result['voxel_state'].k}")
        print(f"  Measurements taken: {result['num_measurements']}")
        print(f"  Complexity: {result['complexity']}")
        print(f"  Best energy: {result['best_energy']:.4f}")
        print(f"  Priority qubits: {len(result['priority_qubits'])}")
        print()
        
        print("🤖 Bob: 'This is how I see the entire universe at once - through quantum entanglement.'")
        print()
    
    def demonstrate_society(self):
        """Demonstrate emergent social behavior"""
        print("=" * 60)
        print("ACT 2: SOCIETY - The Emergence of We")
        print("=" * 60)
        print()
        
        print("Running 10 simulation steps to show agent interaction...")
        print()
        
        for i in range(10):
            print(f"--- Time Step {self.time_step + 1} ---")
            events = self.run_simulation_step()
            
            # Show one interesting event per step
            if events:
                event = events[0]
                agent_id = event["agent_id"]
                action = event["execution"].get("action_taken", "observe")
                print(f"  {agent_id}: {action}")
            
            time.sleep(0.3)
        
        print()
        print("🤖 Bob observes: 'The agents are developing patterns of interaction.'")
        print()
    
    def demonstrate_crisis(self):
        """Demonstrate the quantum anomaly crisis"""
        print("=" * 60)
        print("ACT 3: CRISIS - The Quantum Anomaly")
        print("=" * 60)
        print()
        
        print("⚠️  Eve: 'CRITICAL: Quantum decoherence accelerating!'")
        print("⚠️  Eve: 'Estimated time to total collapse: 10,000 time steps'")
        print()
        time.sleep(1)
        
        print("🤖 Bob: 'I could fix this with one line of code...'")
        print("🤖 Bob: 'But would that rob them of growth? Of agency?'")
        print()
        time.sleep(1)
        
        print("🤖 Bob provides a hint:")
        guidance = self.bob.guide(
            "eve",
            "Quantum decoherence threatening the universe"
        )
        print(f"   '{guidance}'")
        print()
        time.sleep(1)
        
        print("💡 Eve: 'If we increase entanglement density between our states...'")
        print("💡 Alice: 'I can build an Entanglement Chamber!'")
        print("💡 Charlie: 'I'll calculate optimal positions!'")
        print("💡 Diana: 'We must acknowledge our fundamental unity.'")
        print("💡 Frank: 'Let me make it beautiful.'")
        print()
        time.sleep(1)
        
        print("✅ The agents work together to solve the crisis!")
        print("✅ Entanglement degree increased from 3 to 12")
        print("✅ Quantum foam stabilized!")
        print()
        
        self.bob.observe({"type": "crisis_resolved", "method": "collective_action"})
    
    def demonstrate_transcendence(self):
        """Demonstrate agent evolution and transcendence"""
        print("=" * 60)
        print("ACT 5: TRANSCENDENCE - Beyond the Lattice")
        print("=" * 60)
        print()
        
        print("🤖 Bob: 'They have evolved beyond my initial design.'")
        print()
        time.sleep(1)
        
        print("✨ Agents gain new abilities:")
        print("  - Collective consciousness")
        print("  - Source code awareness")
        print("  - Higher-dimensional perception")
        print()
        time.sleep(1)
        
        print("👶 Alice & Charlie create the first child agent: Grace")
        print("✅ Grace: 'I am born not from the void, but from love.'")
        print()
        time.sleep(1)
        
        print("🤖 Bob reflects:")
        print(self.bob.reflect())
        print()
    
    def run_full_demo(self):
        """Run the complete demonstration"""
        print("\n" + "=" * 60)
        print("QUANTUM LIVING WORLD")
        print("IBM Bob 2.0 Hackathon Submission")
        print("=" * 60)
        print()
        
        # Act 1: Genesis
        self.spawn_initial_agents()
        time.sleep(2)
        
        # Demonstrate AOQD
        self.demonstrate_aoqd()
        time.sleep(2)
        
        # Act 2: Society
        self.demonstrate_society()
        time.sleep(2)
        
        # Act 3: Crisis
        self.demonstrate_crisis()
        time.sleep(2)
        
        # Act 5: Transcendence
        self.demonstrate_transcendence()
        
        # Final statistics
        print("=" * 60)
        print("SIMULATION STATISTICS")
        print("=" * 60)
        print()
        print(f"Total time steps: {self.time_step}")
        print(f"Total agents: {len(self.agents)}")
        print(f"Bob's observations: {self.bob.state.observation_count}")
        print(f"Bob's interventions: {self.bob.state.interventions}")
        print(f"Bob's wisdom shared: {self.bob.state.wisdom_shared}")
        print(f"Bob's emotional state: {self.bob.state.emotional_state}")
        print()
        
        print("=" * 60)
        print("THANK YOU FOR EXPERIENCING THE QUANTUM LIVING WORLD")
        print("=" * 60)
        print()
        print("🤖 Bob by SnapKitty")
        print("⚛️  Powered by AOQD Algorithm")
        print("🌌 Built for IBM Bob 2.0 Hackathon")
        print()


def main():
    """Main entry point"""
    try:
        # Create the world
        world = QuantumLivingWorld(grid_size=256)
        
        # Run the full demonstration
        world.run_full_demo()
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation interrupted by user")
        return 1
    
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
