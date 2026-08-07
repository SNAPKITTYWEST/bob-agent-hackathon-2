// 3D Raycasting for Agent Perception
// DDA (Digital Differential Analyzer) algorithm for voxel traversal

use crate::world::octree::{Position, SparseVoxelOctree, Voxel};

/// 3D ray for raycasting
#[derive(Debug, Clone)]
pub struct Ray {
    pub origin: (f32, f32, f32),
    pub direction: (f32, f32, f32),
}

impl Ray {
    pub fn new(origin: (f32, f32, f32), direction: (f32, f32, f32)) -> Self {
        // Normalize direction
        let len = (direction.0 * direction.0 + direction.1 * direction.1 + direction.2 * direction.2).sqrt();
        let normalized = (
            direction.0 / len,
            direction.1 / len,
            direction.2 / len,
        );

        Self {
            origin,
            direction: normalized,
        }
    }
}

/// Raycast result
#[derive(Debug, Clone)]
pub struct RaycastResult {
    pub hit: bool,
    pub position: Position,
    pub distance: f32,
    pub voxel: Option<Voxel>,
}

/// 3D frustum for field of view
pub struct Frustum {
    pub origin: Position,
    pub forward: (f32, f32, f32),
    pub horizontal_fov: f32, // degrees
    pub vertical_fov: f32,   // degrees
    pub ray_density: (usize, usize), // (horizontal, vertical)
}

impl Frustum {
    pub fn new(origin: Position, forward: (f32, f32, f32)) -> Self {
        Self {
            origin,
            forward,
            horizontal_fov: 90.0,
            vertical_fov: 60.0,
            ray_density: (32, 24),
        }
    }

    /// Generate rays for frustum
    pub fn generate_rays(&self) -> Vec<Ray> {
        let mut rays = Vec::new();

        let h_fov_rad = self.horizontal_fov.to_radians();
        let v_fov_rad = self.vertical_fov.to_radians();

        // Calculate right and up vectors
        let (right, up) = self.calculate_basis_vectors();

        for v in 0..self.ray_density.1 {
            for h in 0..self.ray_density.0 {
                // Calculate angles
                let h_angle = (h as f32 / self.ray_density.0 as f32 - 0.5) * h_fov_rad;
                let v_angle = (v as f32 / self.ray_density.1 as f32 - 0.5) * v_fov_rad;

                // Calculate direction
                let direction = (
                    self.forward.0 + right.0 * h_angle.sin() + up.0 * v_angle.sin(),
                    self.forward.1 + right.1 * h_angle.sin() + up.1 * v_angle.sin(),
                    self.forward.2 + right.2 * h_angle.sin() + up.2 * v_angle.sin(),
                );

                let origin = (
                    self.origin.x as f32,
                    self.origin.y as f32,
                    self.origin.z as f32,
                );

                rays.push(Ray::new(origin, direction));
            }
        }

        rays
    }

    fn calculate_basis_vectors(&self) -> ((f32, f32, f32), (f32, f32, f32)) {
        // Right vector (cross product with world up)
        let world_up = (0.0, 1.0, 0.0);
        let right = (
            self.forward.1 * world_up.2 - self.forward.2 * world_up.1,
            self.forward.2 * world_up.0 - self.forward.0 * world_up.2,
            self.forward.0 * world_up.1 - self.forward.1 * world_up.0,
        );

        // Up vector (cross product of right and forward)
        let up = (
            right.1 * self.forward.2 - right.2 * self.forward.1,
            right.2 * self.forward.0 - right.0 * self.forward.2,
            right.0 * self.forward.1 - right.1 * self.forward.0,
        );

        (right, up)
    }
}

/// Raycast engine
pub struct Raycast;

impl Raycast {
    /// Cast ray through voxel grid using DDA algorithm
    pub fn cast(
        ray: &Ray,
        world: &SparseVoxelOctree,
        max_distance: f32,
    ) -> RaycastResult {
        let mut current_pos = (
            ray.origin.0.floor() as i32,
            ray.origin.1.floor() as i32,
            ray.origin.2.floor() as i32,
        );

        // Step direction
        let step = (
            if ray.direction.0 > 0.0 { 1 } else { -1 },
            if ray.direction.1 > 0.0 { 1 } else { -1 },
            if ray.direction.2 > 0.0 { 1 } else { -1 },
        );

        // Calculate t_delta (distance to next voxel boundary)
        let t_delta = (
            if ray.direction.0 != 0.0 { (1.0 / ray.direction.0).abs() } else { f32::MAX },
            if ray.direction.1 != 0.0 { (1.0 / ray.direction.1).abs() } else { f32::MAX },
            if ray.direction.2 != 0.0 { (1.0 / ray.direction.2).abs() } else { f32::MAX },
        );

        // Calculate initial t_max (distance to first voxel boundary)
        let mut t_max = (
            if ray.direction.0 > 0.0 {
                (current_pos.0 as f32 + 1.0 - ray.origin.0) / ray.direction.0
            } else {
                (ray.origin.0 - current_pos.0 as f32) / -ray.direction.0
            },
            if ray.direction.1 > 0.0 {
                (current_pos.1 as f32 + 1.0 - ray.origin.1) / ray.direction.1
            } else {
                (ray.origin.1 - current_pos.1 as f32) / -ray.direction.1
            },
            if ray.direction.2 > 0.0 {
                (current_pos.2 as f32 + 1.0 - ray.origin.2) / ray.direction.2
            } else {
                (ray.origin.2 - current_pos.2 as f32) / -ray.direction.2
            },
        );

        let mut distance = 0.0;

        // DDA traversal
        while distance < max_distance {
            // Check current voxel
            let pos = Position::new(current_pos.0, current_pos.1, current_pos.2);
            if let Some(voxel) = world.get(&pos) {
                if voxel.density > 0.1 {
                    return RaycastResult {
                        hit: true,
                        position: pos,
                        distance,
                        voxel: Some(voxel.clone()),
                    };
                }
            }

            // Step to next voxel
            if t_max.0 < t_max.1 {
                if t_max.0 < t_max.2 {
                    current_pos.0 += step.0;
                    distance = t_max.0;
                    t_max.0 += t_delta.0;
                } else {
                    current_pos.2 += step.2;
                    distance = t_max.2;
                    t_max.2 += t_delta.2;
                }
            } else if t_max.1 < t_max.2 {
                current_pos.1 += step.1;
                distance = t_max.1;
                t_max.1 += t_delta.1;
            } else {
                current_pos.2 += step.2;
                distance = t_max.2;
                t_max.2 += t_delta.2;
            }
        }

        RaycastResult {
            hit: false,
            position: Position::new(current_pos.0, current_pos.1, current_pos.2),
            distance,
            voxel: None,
        }
    }

    /// Cast multiple rays (frustum)
    pub fn cast_frustum(
        frustum: &Frustum,
        world: &SparseVoxelOctree,
        max_distance: f32,
    ) -> Vec<RaycastResult> {
        let rays = frustum.generate_rays();
        rays.iter()
            .map(|ray| Self::cast(ray, world, max_distance))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ray_creation() {
        let ray = Ray::new((0.0, 0.0, 0.0), (1.0, 0.0, 0.0));
        assert!((ray.direction.0 - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_frustum_rays() {
        let frustum = Frustum::new(
            Position::new(0, 0, 0),
            (1.0, 0.0, 0.0),
        );
        let rays = frustum.generate_rays();
        assert_eq!(rays.len(), 32 * 24);
    }

    #[test]
    fn test_raycast() {
        let mut world = SparseVoxelOctree::new(100, 100, 100);
        
        // Place a voxel
        let mut voxel = Voxel::new();
        voxel.density = 1.0;
        world.set(Position::new(10, 10, 10), voxel).unwrap();

        let ray = Ray::new((0.0, 10.0, 10.0), (1.0, 0.0, 0.0));
        let result = Raycast::cast(&ray, &world, 20.0);

        assert!(result.hit);
        assert_eq!(result.position, Position::new(10, 10, 10));
    }
}

// Made with Bob
