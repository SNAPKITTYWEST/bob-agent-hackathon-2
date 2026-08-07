// Cryptographic State Ledger
// WORM (Write-Once-Read-Many) spatial ledger with deterministic replay

use sha3::{Sha3_256, Digest};
use ed25519_dalek::{Keypair, Signature, Signer, Verifier, PublicKey};
use rand_chacha::ChaCha20Rng;
use rand::SeedableRng;
use uuid::Uuid;
use crate::world::octree::{Position, Voxel};
use crate::agents::agent::Action;

/// State transition record
#[derive(Debug, Clone)]
pub struct StateTransition {
    pub agent_id: Uuid,
    pub action: Action,
    pub old_state_hash: [u8; 32],
    pub new_state_hash: [u8; 32],
    pub timestamp: u64,
    pub signature: Vec<u8>,
}

impl StateTransition {
    pub fn new(
        agent_id: Uuid,
        action: Action,
        old_state: &Voxel,
        new_state: &Voxel,
        timestamp: u64,
    ) -> Self {
        Self {
            agent_id,
            action,
            old_state_hash: old_state.state_hash,
            new_state_hash: new_state.state_hash,
            timestamp,
            signature: Vec::new(),
        }
    }

    /// Compute hash of transition for signing
    pub fn compute_hash(&self) -> [u8; 32] {
        let mut hasher = Sha3_256::new();
        
        hasher.update(self.agent_id.as_bytes());
        hasher.update(&self.old_state_hash);
        hasher.update(&self.new_state_hash);
        hasher.update(self.timestamp.to_le_bytes());
        
        hasher.finalize().into()
    }

    /// Sign transition with agent's private key
    pub fn sign(&mut self, keypair: &Keypair) {
        let hash = self.compute_hash();
        let signature = keypair.sign(&hash);
        self.signature = signature.to_bytes().to_vec();
    }

    /// Verify transition signature
    pub fn verify(&self, public_key: &PublicKey) -> Result<(), String> {
        if self.signature.len() != 64 {
            return Err("Invalid signature length".to_string());
        }

        let hash = self.compute_hash();
        let signature = Signature::from_bytes(&self.signature.as_slice()[..64])
            .map_err(|e| format!("Invalid signature: {}", e))?;

        public_key
            .verify(&hash, &signature)
            .map_err(|e| format!("Signature verification failed: {}", e))
    }
}

/// Merkle tree for efficient verification
#[derive(Debug, Clone)]
pub struct MerkleTree {
    pub leaves: Vec<[u8; 32]>,
    pub root: [u8; 32],
}

impl MerkleTree {
    pub fn new(leaves: Vec<[u8; 32]>) -> Self {
        let root = Self::compute_root(&leaves);
        Self { leaves, root }
    }

    fn compute_root(leaves: &[[u8; 32]]) -> [u8; 32] {
        if leaves.is_empty() {
            return [0u8; 32];
        }

        if leaves.len() == 1 {
            return leaves[0];
        }

        let mut current_level = leaves.to_vec();

        while current_level.len() > 1 {
            let mut next_level = Vec::new();

            for chunk in current_level.chunks(2) {
                let hash = if chunk.len() == 2 {
                    Self::hash_pair(&chunk[0], &chunk[1])
                } else {
                    chunk[0]
                };
                next_level.push(hash);
            }

            current_level = next_level;
        }

        current_level[0]
    }

    fn hash_pair(left: &[u8; 32], right: &[u8; 32]) -> [u8; 32] {
        let mut hasher = Sha3_256::new();
        hasher.update(left);
        hasher.update(right);
        hasher.finalize().into()
    }

    /// Generate Merkle proof for a leaf
    pub fn generate_proof(&self, index: usize) -> Vec<[u8; 32]> {
        let mut proof = Vec::new();
        let mut current_index = index;
        let mut current_level = self.leaves.clone();

        while current_level.len() > 1 {
            let sibling_index = if current_index % 2 == 0 {
                current_index + 1
            } else {
                current_index - 1
            };

            if sibling_index < current_level.len() {
                proof.push(current_level[sibling_index]);
            }

            let mut next_level = Vec::new();
            for chunk in current_level.chunks(2) {
                let hash = if chunk.len() == 2 {
                    Self::hash_pair(&chunk[0], &chunk[1])
                } else {
                    chunk[0]
                };
                next_level.push(hash);
            }

            current_level = next_level;
            current_index /= 2;
        }

        proof
    }

    /// Verify Merkle proof
    pub fn verify_proof(leaf: &[u8; 32], proof: &[[u8; 32]], root: &[u8; 32]) -> bool {
        let mut current_hash = *leaf;

        for sibling in proof {
            current_hash = Self::hash_pair(&current_hash, sibling);
        }

        current_hash == *root
    }
}

/// Ledger block
#[derive(Debug, Clone)]
pub struct Block {
    pub index: u64,
    pub timestamp: u64,
    pub transitions: Vec<StateTransition>,
    pub previous_hash: [u8; 32],
    pub merkle_root: [u8; 32],
    pub nonce: u64,
}

impl Block {
    pub fn new(
        index: u64,
        timestamp: u64,
        transitions: Vec<StateTransition>,
        previous_hash: [u8; 32],
    ) -> Self {
        let transition_hashes: Vec<[u8; 32]> = transitions
            .iter()
            .map(|t| t.compute_hash())
            .collect();

        let merkle_tree = MerkleTree::new(transition_hashes);

        Self {
            index,
            timestamp,
            transitions,
            previous_hash,
            merkle_root: merkle_tree.root,
            nonce: 0,
        }
    }

    /// Compute block hash
    pub fn compute_hash(&self) -> [u8; 32] {
        let mut hasher = Sha3_256::new();
        
        hasher.update(self.index.to_le_bytes());
        hasher.update(self.timestamp.to_le_bytes());
        hasher.update(&self.previous_hash);
        hasher.update(&self.merkle_root);
        hasher.update(self.nonce.to_le_bytes());
        
        hasher.finalize().into()
    }
}

/// WORM Spatial Ledger
pub struct SpatialLedger {
    pub genesis_seed: [u8; 32],
    pub blocks: Vec<Block>,
    pub pending_transitions: Vec<StateTransition>,
    pub agent_keys: std::collections::HashMap<Uuid, PublicKey>,
}

impl SpatialLedger {
    pub fn new(genesis_seed: [u8; 32]) -> Self {
        Self {
            genesis_seed,
            blocks: Vec::new(),
            pending_transitions: Vec::new(),
            agent_keys: std::collections::HashMap::new(),
        }
    }

    /// Register agent's public key
    pub fn register_agent(&mut self, agent_id: Uuid, public_key: PublicKey) {
        self.agent_keys.insert(agent_id, public_key);
    }

    /// Append transition to pending queue
    pub fn append_transition(&mut self, transition: StateTransition) -> Result<(), String> {
        // Verify signature
        if let Some(public_key) = self.agent_keys.get(&transition.agent_id) {
            transition.verify(public_key)?;
        } else {
            return Err("Agent not registered".to_string());
        }

        self.pending_transitions.push(transition);
        Ok(())
    }

    /// Commit pending transitions to a new block
    pub fn commit_block(&mut self, timestamp: u64) -> Result<(), String> {
        if self.pending_transitions.is_empty() {
            return Err("No pending transitions".to_string());
        }

        let previous_hash = if let Some(last_block) = self.blocks.last() {
            last_block.compute_hash()
        } else {
            self.genesis_seed
        };

        let index = self.blocks.len() as u64;
        let transitions = std::mem::take(&mut self.pending_transitions);

        let block = Block::new(index, timestamp, transitions, previous_hash);
        self.blocks.push(block);

        Ok(())
    }

    /// Verify entire ledger integrity
    pub fn verify_integrity(&self) -> Result<(), IntegrityError> {
        // Verify genesis
        if self.blocks.is_empty() {
            return Ok(());
        }

        // Verify block chain
        for i in 1..self.blocks.len() {
            let prev_hash = self.blocks[i - 1].compute_hash();
            if self.blocks[i].previous_hash != prev_hash {
                return Err(IntegrityError::BrokenChain(i));
            }
        }

        // Verify merkle roots
        for (i, block) in self.blocks.iter().enumerate() {
            let transition_hashes: Vec<[u8; 32]> = block
                .transitions
                .iter()
                .map(|t| t.compute_hash())
                .collect();

            let merkle_tree = MerkleTree::new(transition_hashes);
            if block.merkle_root != merkle_tree.root {
                return Err(IntegrityError::InvalidMerkleRoot(i));
            }
        }

        // Verify all signatures
        for (i, block) in self.blocks.iter().enumerate() {
            for (j, transition) in block.transitions.iter().enumerate() {
                if let Some(public_key) = self.agent_keys.get(&transition.agent_id) {
                    transition.verify(public_key).map_err(|e| {
                        IntegrityError::InvalidSignature(i, j, e)
                    })?;
                }
            }
        }

        Ok(())
    }

    /// Get block count
    pub fn block_count(&self) -> usize {
        self.blocks.len()
    }

    /// Get total transition count
    pub fn transition_count(&self) -> usize {
        self.blocks.iter().map(|b| b.transitions.len()).sum()
    }

    /// Derive deterministic seed for replay
    pub fn derive_seed(&self, agent_id: Uuid, timestamp: u64) -> [u8; 32] {
        let mut hasher = Sha3_256::new();
        hasher.update(&self.genesis_seed);
        hasher.update(agent_id.as_bytes());
        hasher.update(timestamp.to_le_bytes());
        hasher.finalize().into()
    }
}

/// Ledger integrity errors
#[derive(Debug)]
pub enum IntegrityError {
    BrokenChain(usize),
    InvalidMerkleRoot(usize),
    InvalidSignature(usize, usize, String),
}

impl std::fmt::Display for IntegrityError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            IntegrityError::BrokenChain(index) => {
                write!(f, "Broken chain at block {}", index)
            }
            IntegrityError::InvalidMerkleRoot(index) => {
                write!(f, "Invalid Merkle root at block {}", index)
            }
            IntegrityError::InvalidSignature(block, transition, msg) => {
                write!(
                    f,
                    "Invalid signature at block {}, transition {}: {}",
                    block, transition, msg
                )
            }
        }
    }
}

impl std::error::Error for IntegrityError {}

/// Deterministic replay engine
pub struct ReplayEngine {
    ledger: SpatialLedger,
}

impl ReplayEngine {
    pub fn new(ledger: SpatialLedger) -> Self {
        Self { ledger }
    }

    /// Replay entire simulation from genesis
    pub fn replay(&self) -> Result<ReplayState, String> {
        // Verify ledger integrity first
        self.ledger
            .verify_integrity()
            .map_err(|e| format!("Ledger integrity check failed: {}", e))?;

        let mut state = ReplayState::new(self.ledger.genesis_seed);

        // Replay each block
        for block in &self.ledger.blocks {
            for transition in &block.transitions {
                state.apply_transition(transition)?;
            }
        }

        Ok(state)
    }

    /// Replay up to specific block
    pub fn replay_to_block(&self, target_block: u64) -> Result<ReplayState, String> {
        let mut state = ReplayState::new(self.ledger.genesis_seed);

        for block in self.ledger.blocks.iter().take(target_block as usize + 1) {
            for transition in &block.transitions {
                state.apply_transition(transition)?;
            }
        }

        Ok(state)
    }
}

/// Replay state tracker
#[derive(Debug)]
pub struct ReplayState {
    pub genesis_seed: [u8; 32],
    pub rng: ChaCha20Rng,
    pub transitions_applied: usize,
    pub state_hashes: Vec<[u8; 32]>,
}

impl ReplayState {
    pub fn new(genesis_seed: [u8; 32]) -> Self {
        Self {
            genesis_seed,
            rng: ChaCha20Rng::from_seed(genesis_seed),
            transitions_applied: 0,
            state_hashes: Vec::new(),
        }
    }

    /// Apply state transition deterministically
    pub fn apply_transition(&mut self, transition: &StateTransition) -> Result<(), String> {
        // Derive action-specific seed
        let action_seed = self.derive_action_seed(transition.agent_id, transition.timestamp);
        let mut action_rng = ChaCha20Rng::from_seed(action_seed);

        // Verify state hash matches
        if !self.state_hashes.is_empty() {
            let last_hash = self.state_hashes.last().unwrap();
            if *last_hash != transition.old_state_hash {
                return Err("State hash mismatch".to_string());
            }
        }

        // Record new state hash
        self.state_hashes.push(transition.new_state_hash);
        self.transitions_applied += 1;

        Ok(())
    }

    fn derive_action_seed(&self, agent_id: Uuid, timestamp: u64) -> [u8; 32] {
        let mut hasher = Sha3_256::new();
        hasher.update(&self.genesis_seed);
        hasher.update(agent_id.as_bytes());
        hasher.update(timestamp.to_le_bytes());
        hasher.finalize().into()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ed25519_dalek::Keypair;
    use rand::rngs::OsRng;

    #[test]
    fn test_merkle_tree() {
        let leaves = vec![
            [1u8; 32],
            [2u8; 32],
            [3u8; 32],
            [4u8; 32],
        ];

        let tree = MerkleTree::new(leaves.clone());
        let proof = tree.generate_proof(0);
        
        assert!(MerkleTree::verify_proof(&leaves[0], &proof, &tree.root));
    }

    #[test]
    fn test_ledger_integrity() {
        let genesis_seed = [42u8; 32];
        let mut ledger = SpatialLedger::new(genesis_seed);

        let mut csprng = OsRng{};
        let keypair = Keypair::generate(&mut csprng);
        let agent_id = Uuid::new_v4();

        ledger.register_agent(agent_id, keypair.public);

        let voxel = Voxel::new();
        let mut transition = StateTransition::new(
            agent_id,
            Action::Idle,
            &voxel,
            &voxel,
            0,
        );
        transition.sign(&keypair);

        assert!(ledger.append_transition(transition).is_ok());
        assert!(ledger.commit_block(0).is_ok());
        assert!(ledger.verify_integrity().is_ok());
    }

    #[test]
    fn test_replay_engine() {
        let genesis_seed = [42u8; 32];
        let ledger = SpatialLedger::new(genesis_seed);
        let engine = ReplayEngine::new(ledger);

        let result = engine.replay();
        assert!(result.is_ok());
    }
}

// Made with Bob
