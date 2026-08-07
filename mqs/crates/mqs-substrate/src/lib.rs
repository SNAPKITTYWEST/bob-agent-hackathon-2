// crates/mqs-substrate/src/lib.rs
// MQS: Monadic Quantum Substrate
// NON-SEPARABLE — Qubit = Gate = Memory = Wire = Audit Log

pub mod hamiltonian;
pub mod er_bridge;

pub use hamiltonian::{
    GrowthHamiltonian, GrowthError, MachineState,
    AnyonModel, TopologicalCharge, BraidWord, BraidGenerator,
    LatticePos, LOG_D_FIBONACCI,
};
pub use er_bridge::{
    ERBridge, BridgeError, FusionChannel,
    ModularHamiltonian, BridgeManifest, TraversalResult,
};
