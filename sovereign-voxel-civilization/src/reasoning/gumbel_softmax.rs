// Gumbel-Softmax for Discrete Action Selection
// Differentiable sampling from categorical distributions

use rand::Rng;

/// Gumbel-Softmax sampler for discrete action selection
pub struct GumbelSoftmax {
    temperature: f32,
    min_temperature: f32,
    annealing_rate: f32,
}

impl GumbelSoftmax {
    pub fn new(initial_temperature: f32, min_temperature: f32, annealing_rate: f32) -> Self {
        Self {
            temperature: initial_temperature,
            min_temperature,
            annealing_rate,
        }
    }

    /// Sample from categorical distribution using Gumbel-Softmax
    pub fn sample(&self, logits: &[f32]) -> usize {
        let mut rng = rand::thread_rng();
        
        // Add Gumbel noise
        let gumbel_logits: Vec<f32> = logits
            .iter()
            .map(|&logit| {
                let u: f32 = rng.gen();
                let gumbel = -(-(u.ln())).ln();
                (logit + gumbel) / self.temperature
            })
            .collect();

        // Apply softmax
        let max_logit = gumbel_logits.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let exp_logits: Vec<f32> = gumbel_logits
            .iter()
            .map(|&x| (x - max_logit).exp())
            .collect();
        
        let sum: f32 = exp_logits.iter().sum();
        let probabilities: Vec<f32> = exp_logits.iter().map(|&x| x / sum).collect();

        // Sample from categorical
        let sample: f32 = rng.gen();
        let mut cumulative = 0.0;
        
        for (i, &prob) in probabilities.iter().enumerate() {
            cumulative += prob;
            if sample <= cumulative {
                return i;
            }
        }

        probabilities.len() - 1
    }

    /// Get soft (continuous) sample for gradient computation
    pub fn soft_sample(&self, logits: &[f32]) -> Vec<f32> {
        let mut rng = rand::thread_rng();
        
        // Add Gumbel noise
        let gumbel_logits: Vec<f32> = logits
            .iter()
            .map(|&logit| {
                let u: f32 = rng.gen();
                let gumbel = -(-(u.ln())).ln();
                (logit + gumbel) / self.temperature
            })
            .collect();

        // Apply softmax
        let max_logit = gumbel_logits.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let exp_logits: Vec<f32> = gumbel_logits
            .iter()
            .map(|&x| (x - max_logit).exp())
            .collect();
        
        let sum: f32 = exp_logits.iter().sum();
        exp_logits.iter().map(|&x| x / sum).collect()
    }

    /// Anneal temperature over time
    pub fn anneal(&mut self, timestep: u64) {
        self.temperature = (self.temperature * (-self.annealing_rate * timestep as f32).exp())
            .max(self.min_temperature);
    }

    /// Get current temperature
    pub fn temperature(&self) -> f32 {
        self.temperature
    }

    /// Set temperature
    pub fn set_temperature(&mut self, temperature: f32) {
        self.temperature = temperature.max(self.min_temperature);
    }
}

impl Default for GumbelSoftmax {
    fn default() -> Self {
        Self::new(1.0, 0.5, 0.001)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gumbel_softmax_sampling() {
        let sampler = GumbelSoftmax::new(1.0, 0.5, 0.001);
        let logits = vec![1.0, 2.0, 0.5, 3.0];
        
        let sample = sampler.sample(&logits);
        assert!(sample < logits.len());
    }

    #[test]
    fn test_soft_sampling() {
        let sampler = GumbelSoftmax::new(1.0, 0.5, 0.001);
        let logits = vec![1.0, 2.0, 0.5];
        
        let soft_sample = sampler.soft_sample(&logits);
        assert_eq!(soft_sample.len(), logits.len());
        
        let sum: f32 = soft_sample.iter().sum();
        assert!((sum - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_temperature_annealing() {
        let mut sampler = GumbelSoftmax::new(1.0, 0.5, 0.001);
        let initial_temp = sampler.temperature();
        
        sampler.anneal(1000);
        let annealed_temp = sampler.temperature();
        
        assert!(annealed_temp < initial_temp);
        assert!(annealed_temp >= 0.5);
    }

    #[test]
    fn test_high_temperature_uniform() {
        let sampler = GumbelSoftmax::new(10.0, 0.5, 0.001);
        let logits = vec![1.0, 2.0, 3.0];
        
        // With high temperature, distribution should be more uniform
        let mut counts = vec![0; 3];
        for _ in 0..1000 {
            let sample = sampler.sample(&logits);
            counts[sample] += 1;
        }
        
        // Check that all actions are sampled
        assert!(counts.iter().all(|&c| c > 0));
    }

    #[test]
    fn test_low_temperature_greedy() {
        let sampler = GumbelSoftmax::new(0.1, 0.1, 0.001);
        let logits = vec![1.0, 5.0, 2.0]; // Index 1 has highest logit
        
        // With low temperature, should mostly select highest logit
        let mut counts = vec![0; 3];
        for _ in 0..100 {
            let sample = sampler.sample(&logits);
            counts[sample] += 1;
        }
        
        // Index 1 should be selected most often
        assert!(counts[1] > counts[0] && counts[1] > counts[2]);
    }
}

// Made with Bob
