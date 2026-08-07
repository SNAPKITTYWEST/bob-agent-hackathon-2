// Sparse Voxel Octree Implementation
// 3D spatial indexing structure for efficient voxel storage and retrieval

use std::collections::HashMap;
use uuid::Uuid;

/// 3D position in voxel space
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Position {
    pub x: i32,
    pub y: i32,
    pub z: i32,
}

impl Position {
    pub fn new(x: i32, y: i32, z: i32) -> Self {
        Self { x, y, z }
    }

    pub fn distance_squared(&self, other: &Position) -> i32 {
        let dx = self.x - other.x;
        let dy = self.y - other.y;
        let dz = self.z - other.z;
        dx * dx + dy * dy + dz * dz
    }
}

/// Probability distribution for hazard potential
#[derive(Debug, Clone)]
pub struct ProbabilityDistribution {
    pub mean: f32,
    pub variance: f32,
    pub samples: Vec<f32>,
}

impl ProbabilityDistribution {
    pub fn new(mean: f32, variance: f32) -> Self {
        Self {
            mean,
            variance,
            samples: Vec::new(),
        }
    }

    pub fn entropy(&self) -> f32 {
        // Shannon entropy calculation
        if self.samples.is_empty() {
            return 0.0;
        }

        let mut entropy = 0.0;
        let total: f32 = self.samples.iter().sum();
        
        for &sample in &self.samples {
            if sample > 0.0 {
                let p = sample / total;
                entropy -= p * p.log2();
            }
        }
        
        entropy
    }

    pub fn sample(&self) -> f32 {
        // Simple sampling from mean with variance
        use rand::Rng;
        let mut rng = rand::thread_rng();
        let noise: f32 = rng.gen_range(-1.0..1.0);
        (self.mean + noise * self.variance.sqrt()).clamp(0.0, 1.0)
    }
}

/// Individual voxel state
#[derive(Debug, Clone)]
pub struct Voxel {
    pub density: f32,
    pub material_id: u16,
    pub hazard_potential: ProbabilityDistribution,
    pub owner_agent_id: Option<Uuid>,
    pub timestamp: u64,
    pub state_hash: [u8; 32],
}

impl Voxel {
    pub fn new() -> Self {
        Self {
            density: 0.0,
            material_id: 0,
            hazard_potential: ProbabilityDistribution::new(0.0, 0.1),
            owner_agent_id: None,
            timestamp: 0,
            state_hash: [0u8; 32],
        }
    }

    pub fn compute_hash(&self) -> [u8; 32] {
        use sha3::{Sha3_256, Digest};
        let mut hasher = Sha3_256::new();
        
        hasher.update(self.density.to_le_bytes());
        hasher.update(self.material_id.to_le_bytes());
        hasher.update(self.hazard_potential.mean.to_le_bytes());
        hasher.update(self.timestamp.to_le_bytes());
        
        if let Some(id) = self.owner_agent_id {
            hasher.update(id.as_bytes());
        }
        
        hasher.finalize().into()
    }

    pub fn update_hash(&mut self) {
        self.state_hash = self.compute_hash();
    }
}

impl Default for Voxel {
    fn default() -> Self {
        Self::new()
    }
}

/// Octree node for spatial partitioning
#[derive(Debug)]
enum OctreeNode {
    Leaf {
        voxels: HashMap<Position, Voxel>,
    },
    Branch {
        children: Box<[Option<Box<OctreeNode>>; 8]>,
        bounds: Bounds,
    },
}

/// Axis-aligned bounding box
#[derive(Debug, Clone, Copy)]
pub struct Bounds {
    pub min: Position,
    pub max: Position,
}

impl Bounds {
    pub fn new(min: Position, max: Position) -> Self {
        Self { min, max }
    }

    pub fn contains(&self, pos: &Position) -> bool {
        pos.x >= self.min.x && pos.x <= self.max.x &&
        pos.y >= self.min.y && pos.y <= self.max.y &&
        pos.z >= self.min.z && pos.z <= self.max.z
    }

    pub fn octant(&self, index: usize) -> Bounds {
        let mid_x = (self.min.x + self.max.x) / 2;
        let mid_y = (self.min.y + self.max.y) / 2;
        let mid_z = (self.min.z + self.max.z) / 2;

        let (x_offset, y_offset, z_offset) = (
            if index & 1 != 0 { 1 } else { 0 },
            if index & 2 != 0 { 1 } else { 0 },
            if index & 4 != 0 { 1 } else { 0 },
        );

        let min = Position::new(
            if x_offset == 0 { self.min.x } else { mid_x },
            if y_offset == 0 { self.min.y } else { mid_y },
            if z_offset == 0 { self.min.z } else { mid_z },
        );

        let max = Position::new(
            if x_offset == 0 { mid_x } else { self.max.x },
            if y_offset == 0 { mid_y } else { self.max.y },
            if z_offset == 0 { mid_z } else { self.max.z },
        );

        Bounds::new(min, max)
    }

    pub fn octant_index(&self, pos: &Position) -> usize {
        let mid_x = (self.min.x + self.max.x) / 2;
        let mid_y = (self.min.y + self.max.y) / 2;
        let mid_z = (self.min.z + self.max.z) / 2;

        let x_bit = if pos.x >= mid_x { 1 } else { 0 };
        let y_bit = if pos.y >= mid_y { 2 } else { 0 };
        let z_bit = if pos.z >= mid_z { 4 } else { 0 };

        x_bit | y_bit | z_bit
    }
}

/// Sparse Voxel Octree for efficient 3D world representation
pub struct SparseVoxelOctree {
    root: OctreeNode,
    bounds: Bounds,
    max_depth: usize,
    voxel_count: usize,
}

impl SparseVoxelOctree {
    /// Create new octree with specified dimensions
    pub fn new(width: i32, height: i32, depth: i32) -> Self {
        let bounds = Bounds::new(
            Position::new(0, 0, 0),
            Position::new(width - 1, height - 1, depth - 1),
        );

        Self {
            root: OctreeNode::Leaf {
                voxels: HashMap::new(),
            },
            bounds,
            max_depth: 10, // log2(1024) = 10 for 1024x1024x1024 grid
            voxel_count: 0,
        }
    }

    /// Get voxel at position (O(log N) complexity)
    pub fn get(&self, pos: &Position) -> Option<&Voxel> {
        if !self.bounds.contains(pos) {
            return None;
        }

        self.get_recursive(&self.root, pos, &self.bounds)
    }

    fn get_recursive(&self, node: &OctreeNode, pos: &Position, bounds: &Bounds) -> Option<&Voxel> {
        match node {
            OctreeNode::Leaf { voxels } => voxels.get(pos),
            OctreeNode::Branch { children, .. } => {
                let index = bounds.octant_index(pos);
                if let Some(child) = &children[index] {
                    let child_bounds = bounds.octant(index);
                    self.get_recursive(child, pos, &child_bounds)
                } else {
                    None
                }
            }
        }
    }

    /// Set voxel at position
    pub fn set(&mut self, pos: Position, mut voxel: Voxel) -> Result<(), String> {
        if !self.bounds.contains(&pos) {
            return Err(format!("Position {:?} out of bounds", pos));
        }

        voxel.update_hash();
        self.set_recursive(&mut self.root, pos, voxel, &self.bounds, 0)?;
        self.voxel_count += 1;
        Ok(())
    }

    fn set_recursive(
        &mut self,
        node: &mut OctreeNode,
        pos: Position,
        voxel: Voxel,
        bounds: &Bounds,
        depth: usize,
    ) -> Result<(), String> {
        match node {
            OctreeNode::Leaf { voxels } => {
                if depth < self.max_depth && voxels.len() >= 8 {
                    // Split leaf into branch
                    let old_voxels = std::mem::take(voxels);
                    let mut children: [Option<Box<OctreeNode>>; 8] = Default::default();
                    
                    *node = OctreeNode::Branch {
                        children: Box::new(children),
                        bounds: *bounds,
                    };

                    // Reinsert old voxels
                    for (old_pos, old_voxel) in old_voxels {
                        self.set_recursive(node, old_pos, old_voxel, bounds, depth)?;
                    }

                    // Insert new voxel
                    self.set_recursive(node, pos, voxel, bounds, depth)
                } else {
                    voxels.insert(pos, voxel);
                    Ok(())
                }
            }
            OctreeNode::Branch { children, .. } => {
                let index = bounds.octant_index(&pos);
                let child_bounds = bounds.octant(index);

                if children[index].is_none() {
                    children[index] = Some(Box::new(OctreeNode::Leaf {
                        voxels: HashMap::new(),
                    }));
                }

                if let Some(child) = &mut children[index] {
                    self.set_recursive(child, pos, voxel, &child_bounds, depth + 1)
                } else {
                    Err("Failed to create child node".to_string())
                }
            }
        }
    }

    /// Remove voxel at position
    pub fn remove(&mut self, pos: &Position) -> Option<Voxel> {
        if !self.bounds.contains(pos) {
            return None;
        }

        let result = self.remove_recursive(&mut self.root, pos, &self.bounds);
        if result.is_some() {
            self.voxel_count = self.voxel_count.saturating_sub(1);
        }
        result
    }

    fn remove_recursive(&mut self, node: &mut OctreeNode, pos: &Position, bounds: &Bounds) -> Option<Voxel> {
        match node {
            OctreeNode::Leaf { voxels } => voxels.remove(pos),
            OctreeNode::Branch { children, .. } => {
                let index = bounds.octant_index(pos);
                if let Some(child) = &mut children[index] {
                    let child_bounds = bounds.octant(index);
                    self.remove_recursive(child, pos, &child_bounds)
                } else {
                    None
                }
            }
        }
    }

    /// Get all voxels within a radius
    pub fn get_in_radius(&self, center: &Position, radius: i32) -> Vec<(Position, &Voxel)> {
        let mut results = Vec::new();
        let radius_squared = radius * radius;

        self.collect_in_radius(&self.root, center, radius_squared, &self.bounds, &mut results);
        results
    }

    fn collect_in_radius(
        &self,
        node: &OctreeNode,
        center: &Position,
        radius_squared: i32,
        bounds: &Bounds,
        results: &mut Vec<(Position, &Voxel)>,
    ) {
        match node {
            OctreeNode::Leaf { voxels } => {
                for (pos, voxel) in voxels {
                    if pos.distance_squared(center) <= radius_squared {
                        results.push((*pos, voxel));
                    }
                }
            }
            OctreeNode::Branch { children, .. } => {
                for (i, child_opt) in children.iter().enumerate() {
                    if let Some(child) = child_opt {
                        let child_bounds = bounds.octant(i);
                        // Check if octant intersects sphere
                        if self.bounds_intersects_sphere(&child_bounds, center, radius_squared) {
                            self.collect_in_radius(child, center, radius_squared, &child_bounds, results);
                        }
                    }
                }
            }
        }
    }

    fn bounds_intersects_sphere(&self, bounds: &Bounds, center: &Position, radius_squared: i32) -> bool {
        let closest_x = center.x.clamp(bounds.min.x, bounds.max.x);
        let closest_y = center.y.clamp(bounds.min.y, bounds.max.y);
        let closest_z = center.z.clamp(bounds.min.z, bounds.max.z);

        let closest = Position::new(closest_x, closest_y, closest_z);
        closest.distance_squared(center) <= radius_squared
    }

    /// Get total number of voxels
    pub fn voxel_count(&self) -> usize {
        self.voxel_count
    }

    /// Get world bounds
    pub fn bounds(&self) -> &Bounds {
        &self.bounds
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_octree_basic_operations() {
        let mut octree = SparseVoxelOctree::new(1024, 256, 1024);
        
        let pos = Position::new(100, 50, 100);
        let voxel = Voxel::new();
        
        assert!(octree.set(pos, voxel.clone()).is_ok());
        assert!(octree.get(&pos).is_some());
        assert_eq!(octree.voxel_count(), 1);
        
        assert!(octree.remove(&pos).is_some());
        assert!(octree.get(&pos).is_none());
        assert_eq!(octree.voxel_count(), 0);
    }

    #[test]
    fn test_octree_radius_query() {
        let mut octree = SparseVoxelOctree::new(1024, 256, 1024);
        
        let center = Position::new(100, 100, 100);
        
        // Add voxels in a pattern
        for i in 0..5 {
            let pos = Position::new(100 + i, 100, 100);
            octree.set(pos, Voxel::new()).unwrap();
        }
        
        let results = octree.get_in_radius(&center, 3);
        assert!(results.len() >= 3);
    }

    #[test]
    fn test_voxel_hash() {
        let mut voxel = Voxel::new();
        voxel.density = 0.5;
        voxel.material_id = 42;
        
        let hash1 = voxel.compute_hash();
        voxel.update_hash();
        
        assert_eq!(hash1, voxel.state_hash);
        
        voxel.density = 0.6;
        let hash2 = voxel.compute_hash();
        
        assert_ne!(hash1, hash2);
    }
}

// Made with Bob
