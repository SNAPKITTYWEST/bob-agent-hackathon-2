// Minefield Physics Engine
// Dynamic hazard distribution with adaptive density and probabilistic obscurity

use crate::world::octree::{Position, ProbabilityDistribution};
use crate::agents::agent::{Agent, HazardSignal};
use rand::{Rng, SeedableRng};
use rand_chacha::ChaCha20Rng;
use std::collections::HashMap;

/// Mine trigger mechanics
#[derive(Debug, Clone)]
pub struct Mine {
    pub position: Position,
    pub hazard_potential: ProbabilityDistribution,
    pub active: bool,
    pub trigger_threshold: f32,
    pub blast_radius: i32,
}

impl Mine {
    pub fn new(position: Position, rng: &mut ChaCha20Rng) -> Self {
        let mean = rng.gen_range(0.5..0.9);
        let variance = rng.gen_range(0.05..0.15);
        
        Self {
            position,
            hazard_potential: ProbabilityDistribution::new(mean, variance),
            active: true,
            trigger_threshold: 0.7,
            blast_radius: 3,
        }
    }

    /// Check if agent volume triggers mine
    pub fn check_trigger(&self, agent_position: &Position, rng: &mut ChaCha20Rng) -> bool {
        if !self.active {
            return false;
        }

        // Volume intersection test
        let distance_squared = self.position.distance_squared(agent_position);
        if distance_squared > 1 {
            return false;
        }

        // Entropy threshold test
        let entropy = self.hazard_potential.entropy();
        if entropy < 0.5 {
            return false;
        }

        // Probabilistic trigger
        let trigger_prob = self.hazard_potential.sample();
        trigger_prob > self.trigger_threshold && rng.gen::<f32>() < trigger_prob
    }

    /// Get obscured hazard signal (with noise)
    pub fn get_obscured_signal(&self, observer_position: &Position, rng: &mut ChaCha20Rng) -> HazardSignal {
        let distance = (self.position.distance_squared(observer_position) as f32).sqrt();
        
        // Distance attenuation
        let base_intensity = self.hazard_potential.mean / (1.0 + distance * 0.1);
        
        // Perlin-like noise overlay
        let noise = self.perlin_noise(observer_position, rng);
        let observed_intensity = base_intensity * (1.0 - noise) + noise * rng.gen::<f32>();
        
        // Confidence decreases with distance
        let confidence = (1.0 / (1.0 + distance * 0.05)).clamp(0.1, 0.9);
        
        HazardSignal {
            position: self.position,
            intensity: observed_intensity.clamp(0.0, 1.0),
            confidence,
        }
    }

    /// Simplified Perlin noise function
    fn perlin_noise(&self, pos: &Position, rng: &mut ChaCha20Rng) -> f32 {
        let x = pos.x as f32 * 0.1;
        let y = pos.y as f32 * 0.1;
        let z = pos.z as f32 * 0.1;
        
        // Simple multi-octave noise
        let mut noise = 0.0;
        let mut amplitude = 1.0;
        let mut frequency = 1.0;
        
        for _ in 0..4 {
            let sample_x = (x * frequency).sin();
            let sample_y = (y * frequency).sin();
            let sample_z = (z * frequency).sin();
            
            noise += (sample_x + sample_y + sample_z) * amplitude / 3.0;
            amplitude *= 0.5;
            frequency *= 2.0;
        }
        
        (noise + 1.0) / 2.0 // Normalize to [0, 1]
    }
}

/// Minefield manager with adaptive density
pub struct Minefield {
    mines: HashMap<Position, Mine>,
    activity_heatmap: HashMap<Position, f32>,
    rng: ChaCha20Rng,
    temperature: f32,
    initial_temperature: f32,
    cooling_rate: f32,
    entropy_bound: f32,
}

impl Minefield {
    pub fn new(seed: u64, entropy_bound: f32) -> Self {
        Self {
            mines: HashMap::new(),
            activity_heatmap: HashMap::new(),
            rng: ChaCha20Rng::seed_from_u64(seed),
            temperature: 1.0,
            initial_temperature: 1.0,
            cooling_rate: 0.001,
            entropy_bound,
        }
    }

    /// Initialize mines with random distribution
    pub fn initialize(&mut self, count: usize, bounds: (i32, i32, i32)) {
        for _ in 0..count {
            let x = self.rng.gen_range(0..bounds.0);
            let y = self.rng.gen_range(0..bounds.1);
            let z = self.rng.gen_range(0..bounds.2);
            
            let position = Position::new(x, y, z);
            let mine = Mine::new(position, &mut self.rng);
            
            self.mines.insert(position, mine);
        }
    }

    /// Check if agent triggers any mines
    pub fn check_triggers(&mut self, agent: &Agent) -> Vec<MineExplosion> {
        let mut explosions = Vec::new();

        for mine in self.mines.values_mut() {
            if mine.check_trigger(&agent.position, &mut self.rng) {
                explosions.push(MineExplosion {
                    position: mine.position,
                    blast_radius: mine.blast_radius,
                    agent_id: agent.id,
                });
                mine.active = false;
            }
        }

        explosions
    }

    /// Get hazard signals visible to agent (with multi-agent consensus requirement)
    pub fn get_hazard_signals(
        &mut self,
        observer_position: &Position,
        scan_radius: i32,
        agent_observations: &[HazardSignal],
    ) -> Vec<HazardSignal> {
        let mut signals = Vec::new();
        let radius_squared = scan_radius * scan_radius;

        for mine in self.mines.values() {
            if !mine.active {
                continue;
            }

            let distance_squared = mine.position.distance_squared(observer_position);
            if distance_squared <= radius_squared {
                let signal = mine.get_obscured_signal(observer_position, &mut self.rng);
                
                // Check for multi-agent consensus
                if self.check_consensus(&signal, agent_observations) {
                    signals.push(signal);
                }
            }
        }

        signals
    }

    /// Check if multiple agents agree on hazard signal
    fn check_consensus(&self, signal: &HazardSignal, other_observations: &[HazardSignal]) -> bool {
        if other_observations.is_empty() {
            return signal.confidence > 0.6; // Single agent needs high confidence
        }

        let consensus_threshold = (other_observations.len() as f32 * 0.6).ceil() as usize;
        let mut similar_count = 0;

        for obs in other_observations {
            if obs.position == signal.position {
                let intensity_diff = (obs.intensity - signal.intensity).abs();
                if intensity_diff < 0.3 {
                    similar_count += 1;
                }
            }
        }

        similar_count >= consensus_threshold
    }

    /// Update activity heatmap based on agent movements
    pub fn update_activity_heatmap(&mut self, agent_positions: &[Position]) {
        // Decay existing activity
        for activity in self.activity_heatmap.values_mut() {
            *activity *= 0.95;
        }

        // Add new activity with Gaussian kernel
        for pos in agent_positions {
            for dx in -5..=5 {
                for dy in -5..=5 {
                    for dz in -5..=5 {
                        let target = Position::new(pos.x + dx, pos.y + dy, pos.z + dz);
                        let distance_squared = pos.distance_squared(&target);
                        
                        if distance_squared <= 25 {
                            let gaussian = (-distance_squared as f32 / 10.0).exp();
                            *self.activity_heatmap.entry(target).or_insert(0.0) += gaussian;
                        }
                    }
                }
            }
        }
    }

    /// Redistribute mines using simulated annealing
    pub fn redistribute_mines(&mut self, timestep: u64) {
        // Update temperature
        self.temperature = self.initial_temperature * (-self.cooling_rate * timestep as f32).exp();

        // Identify high-activity regions
        let mut high_activity_positions: Vec<Position> = self
            .activity_heatmap
            .iter()
            .filter(|(_, &activity)| activity > 0.5)
            .map(|(pos, _)| *pos)
            .collect();

        if high_activity_positions.is_empty() {
            return;
        }

        // Propose mine relocations
        let inactive_mines: Vec<Position> = self
            .mines
            .iter()
            .filter(|(_, mine)| !mine.active)
            .map(|(pos, _)| *pos)
            .collect();

        for old_pos in inactive_mines.iter().take(5) {
            if let Some(new_pos) = high_activity_positions.pop() {
                // Compute energy change
                let old_energy = self.compute_energy(old_pos);
                let new_energy = self.compute_energy(&new_pos);
                let delta_energy = new_energy - old_energy;

                // Metropolis-Hastings acceptance
                let acceptance_prob = if delta_energy < 0.0 {
                    1.0
                } else {
                    (-delta_energy / self.temperature).exp()
                };

                if self.rng.gen::<f32>() < acceptance_prob {
                    // Accept relocation
                    if let Some(mine) = self.mines.remove(old_pos) {
                        let mut new_mine = Mine::new(new_pos, &mut self.rng);
                        new_mine.active = true;
                        self.mines.insert(new_pos, new_mine);
                    }
                }
            }
        }
    }

    /// Compute energy for simulated annealing
    fn compute_energy(&self, pos: &Position) -> f32 {
        let activity = self.activity_heatmap.get(pos).unwrap_or(&0.0);
        let spatial_uniformity = self.compute_spatial_uniformity(pos);
        
        // E(config) = w_activity * activity + λ * uniformity_penalty
        activity * 2.0 + spatial_uniformity * 0.5
    }

    /// Compute spatial uniformity penalty
    fn compute_spatial_uniformity(&self, pos: &Position) -> f32 {
        let mut nearby_mines = 0;
        
        for mine_pos in self.mines.keys() {
            if pos.distance_squared(mine_pos) <= 25 {
                nearby_mines += 1;
            }
        }

        // Penalty for clustering
        if nearby_mines > 3 {
            (nearby_mines - 3) as f32 * 0.5
        } else {
            0.0
        }
    }

    /// Get current system entropy
    pub fn compute_system_entropy(&self) -> f32 {
        if self.mines.is_empty() {
            return 0.0;
        }

        let mut total_entropy = 0.0;
        for mine in self.mines.values() {
            total_entropy += mine.hazard_potential.entropy();
        }

        total_entropy / self.mines.len() as f32
    }

    /// Check if entropy bound is satisfied
    pub fn check_entropy_bound(&self) -> bool {
        self.compute_system_entropy() <= self.entropy_bound
    }

    /// Get mine count
    pub fn mine_count(&self) -> usize {
        self.mines.len()
    }

    /// Get active mine count
    pub fn active_mine_count(&self) -> usize {
        self.mines.values().filter(|m| m.active).count()
    }
}

/// Mine explosion event
#[derive(Debug, Clone)]
pub struct MineExplosion {
    pub position: Position,
    pub blast_radius: i32,
    pub agent_id: uuid::Uuid,
}

impl MineExplosion {
    /// Get affected positions (6-connected neighbors)
    pub fn get_affected_positions(&self) -> Vec<Position> {
        let mut positions = vec![self.position];
        
        for dx in -self.blast_radius..=self.blast_radius {
            for dy in -self.blast_radius..=self.blast_radius {
                for dz in -self.blast_radius..=self.blast_radius {
                    if dx == 0 && dy == 0 && dz == 0 {
                        continue;
                    }

                    let distance_squared = dx * dx + dy * dy + dz * dz;
                    if distance_squared <= self.blast_radius * self.blast_radius {
                        positions.push(Position::new(
                            self.position.x + dx,
                            self.position.y + dy,
                            self.position.z + dz,
                        ));
                    }
                }
            }
        }

        positions
    }

    /// Compute damage at position
    pub fn compute_damage(&self, pos: &Position) -> f32 {
        let distance = (self.position.distance_squared(pos) as f32).sqrt();
        let max_distance = self.blast_radius as f32;
        
        if distance > max_distance {
            0.0
        } else {
            // Inverse square falloff
            1.0 - (distance / max_distance).powi(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_minefield_initialization() {
        let mut minefield = Minefield::new(12345, 0.20);
        minefield.initialize(100, (1024, 256, 1024));
        
        assert_eq!(minefield.mine_count(), 100);
        assert_eq!(minefield.active_mine_count(), 100);
    }

    #[test]
    fn test_entropy_bound() {
        let minefield = Minefield::new(12345, 0.20);
        assert!(minefield.check_entropy_bound());
    }

    #[test]
    fn test_mine_explosion() {
        let explosion = MineExplosion {
            position: Position::new(10, 10, 10),
            blast_radius: 3,
            agent_id: uuid::Uuid::new_v4(),
        };

        let affected = explosion.get_affected_positions();
        assert!(!affected.is_empty());

        let damage_center = explosion.compute_damage(&Position::new(10, 10, 10));
        let damage_edge = explosion.compute_damage(&Position::new(13, 10, 10));
        
        assert!(damage_center > damage_edge);
    }

    #[test]
    fn test_activity_heatmap() {
        let mut minefield = Minefield::new(12345, 0.20);
        let positions = vec![
            Position::new(100, 100, 100),
            Position::new(101, 100, 100),
        ];

        minefield.update_activity_heatmap(&positions);
        assert!(!minefield.activity_heatmap.is_empty());
    }
}

// Made with Bob
