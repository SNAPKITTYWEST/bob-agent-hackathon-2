"""
test_guppy.py — pytest test suite for the Guppy Python simulation.

Run:
    pytest guppy/tests/test_guppy.py -v

Tests validate:
  - Linear type enforcement (no-cloning, no-discard)
  - Bell state QIR output shape and correctness
  - Measurement consumes qubit reference
  - Unsupported list is always present and non-empty
  - Resource counting accuracy
  - Grover circuit lowering
"""

from __future__ import annotations

import json
import math
import sys
import os
import pytest

# Ensure root of repo is importable when running from repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from guppy.guppy_types import (
    GuppyCircuit,
    QubitRef,
    ClassicalBit,
    LinearityViolation,
    Linearity,
)
from guppy.guppy_ops import (
    h, cx, t, t_dag, s, s_dag, x, y, z, rx, ry, rz,
    cz, swap, ccx, measure, init_qubit, barrier, reset_qubit,
)
from guppy.guppy_to_ir import circuit_to_ir, circuit_to_ir_json, validate_ir


# ===========================================================================
# Linearity / no-cloning tests
# ===========================================================================

class TestLinearityViolations:
    """Tests that the linear type system raises on violations."""

    def test_double_consume_raises(self):
        """Consuming the same QubitRef twice raises LinearityViolation."""
        q = QubitRef(id=0)
        q.consume()
        with pytest.raises(LinearityViolation, match="already been consumed"):
            q.consume()

    def test_double_gate_on_same_ref_raises(self):
        """Passing a qubit through two gates without capturing return raises."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        q = h(circ, q)        # consumes original, q is now the new ref
        h(circ, q)             # consumes new ref (this is fine)
        # But if we try to use the pre-h ref again:
        circ2 = GuppyCircuit(n_qubits=1)
        q2 = circ2.qubit(0)
        _q2_original = q2      # keep a reference to the original
        q2 = h(circ2, q2)      # q2_original is now consumed
        with pytest.raises(LinearityViolation):
            h(circ2, _q2_original)  # original ref is consumed — should raise

    def test_cx_same_qubit_as_ctrl_and_tgt_raises(self):
        """Passing the same QubitRef as both ctrl and tgt of CX raises."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        with pytest.raises(LinearityViolation):
            # This should raise because q.consume() is called for ctrl,
            # then q.consume() is called again for tgt.
            cx(circ, q, q)

    def test_unconsumed_qubit_raises_on_check(self):
        """A circuit with an unfinished qubit fails check_all_consumed()."""
        circ = GuppyCircuit(n_qubits=2)
        q0 = circ.qubit(0)
        _q1 = circ.qubit(1)  # allocated but never used
        q0 = h(circ, q0)
        measure(circ, q0)
        with pytest.raises(LinearityViolation, match="Linear resource leak"):
            circ.check_all_consumed()

    def test_all_consumed_passes(self):
        """A circuit where every qubit is measured passes check_all_consumed()."""
        circ = GuppyCircuit(n_qubits=2)
        q0, q1 = circ.qubit(0), circ.qubit(1)
        q0 = h(circ, q0)
        q0, q1 = cx(circ, q0, q1)
        measure(circ, q0)
        measure(circ, q1)
        circ.check_all_consumed()  # should not raise

    def test_measure_returns_classical_bit(self):
        """measure() returns a ClassicalBit — an unrestricted type."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        q = h(circ, q)
        result = measure(circ, q)
        assert isinstance(result, ClassicalBit)
        assert result.linearity == Linearity.UNRESTRICTED

    def test_measure_consumes_qubit(self):
        """After measure, the QubitRef is consumed — cannot be reused."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        # Keep the original ref to try reuse after measure
        original_ref = q
        q_new = h(circ, q)
        # q_new now owns it — measure consumes q_new
        measure(circ, q_new)
        # original_ref was already consumed by h(); trying to use it raises.
        with pytest.raises(LinearityViolation):
            measure(circ, original_ref)

    def test_qubit_ref_id_matches(self):
        """QubitRef ids match the circuit qubit indices."""
        circ = GuppyCircuit(n_qubits=3)
        for i in range(3):
            assert circ.qubit(i).id == i

    def test_init_qubit_allocates_fresh_ref(self):
        """init_qubit() returns a fresh QubitRef with a new id."""
        circ = GuppyCircuit(n_qubits=2)
        new_q = init_qubit(circ)
        assert new_q.id == 2  # next after 0, 1
        assert not new_q.consumed


# ===========================================================================
# Bell state QIR output
# ===========================================================================

class TestBellStateQIR:
    """Verify the Bell state circuit produces correct QIR."""

    def _build_bell(self) -> GuppyCircuit:
        circ = GuppyCircuit(n_qubits=2)
        q0, q1 = circ.qubit(0), circ.qubit(1)
        q0 = h(circ, q0)
        q0, q1 = cx(circ, q0, q1)
        measure(circ, q0)
        measure(circ, q1)
        circ.check_all_consumed()
        return circ

    def test_source_lang_is_guppy(self):
        """QIR source_lang must be 'guppy'."""
        qir = circuit_to_ir(self._build_bell())
        assert qir["source_lang"] == "guppy"

    def test_qubits_count(self):
        """Bell state uses exactly 2 qubits."""
        qir = circuit_to_ir(self._build_bell())
        assert qir["qubits"] == 2

    def test_cbits_count(self):
        """Bell state produces exactly 2 classical bits."""
        qir = circuit_to_ir(self._build_bell())
        assert qir["cbits"] == 2

    def test_ops_list_has_four_entries(self):
        """Bell state has 4 ops: H, CX, measure(q0), measure(q1)."""
        qir = circuit_to_ir(self._build_bell())
        assert len(qir["ops"]) == 4

    def test_first_op_is_h_gate(self):
        """First op in Bell state is a Hadamard on qubit 0."""
        qir = circuit_to_ir(self._build_bell())
        op = qir["ops"][0]
        assert op["type"] == "gate"
        assert op["name"] == "H"
        assert op["qubits"] == [0]

    def test_second_op_is_cx(self):
        """Second op is CX with ctrl=0, tgt=1."""
        qir = circuit_to_ir(self._build_bell())
        op = qir["ops"][1]
        assert op["type"] == "gate"
        assert op["name"] == "CX"
        assert op["qubits"] == [0, 1]

    def test_measure_ops_consume_qubits(self):
        """Both measure ops reference the correct qubit and cbit indices."""
        qir = circuit_to_ir(self._build_bell())
        meas_ops = [op for op in qir["ops"] if op["type"] == "measure"]
        assert len(meas_ops) == 2
        qubit_ids = {op["qubit"] for op in meas_ops}
        assert qubit_ids == {0, 1}
        cbit_ids = {op["cbit"] for op in meas_ops}
        assert cbit_ids == {0, 1}

    def test_gate_count_equals_non_measure_gates(self):
        """gate_count resource metric equals number of gate-type ops."""
        qir = circuit_to_ir(self._build_bell())
        gate_ops = [op for op in qir["ops"] if op["type"] == "gate"]
        assert qir["resources"]["gate_count"] == len(gate_ops)

    def test_bell_gate_count_is_2(self):
        """Bell state has exactly 2 gates (H and CX)."""
        qir = circuit_to_ir(self._build_bell())
        assert qir["resources"]["gate_count"] == 2

    def test_t_count_is_zero(self):
        """Bell state has no T gates."""
        qir = circuit_to_ir(self._build_bell())
        assert qir["resources"]["t_count"] == 0

    def test_width_is_2(self):
        """Circuit width equals number of qubits."""
        qir = circuit_to_ir(self._build_bell())
        assert qir["resources"]["width"] == 2

    def test_qir_json_is_parseable(self):
        """circuit_to_ir_json() produces valid JSON."""
        circ = self._build_bell()
        json_str = circuit_to_ir_json(circ)
        parsed = json.loads(json_str)
        assert parsed["source_lang"] == "guppy"

    def test_validate_ir_passes(self):
        """validate_ir() returns no errors for Bell state QIR."""
        qir = circuit_to_ir(self._build_bell())
        errors = validate_ir(qir)
        assert errors == [], f"Unexpected validation errors: {errors}"


# ===========================================================================
# Unsupported semantics list
# ===========================================================================

class TestUnsupportedList:
    """The unsupported list must always be present and non-empty."""

    def test_unsupported_present_in_metadata(self):
        """metadata.unsupported key exists in every QIR output."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        q = h(circ, q)
        measure(circ, q)
        qir = circuit_to_ir(circ)
        assert "unsupported" in qir["metadata"]

    def test_unsupported_is_list(self):
        """metadata.unsupported is a list type."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        q = h(circ, q)
        measure(circ, q)
        qir = circuit_to_ir(circ)
        assert isinstance(qir["metadata"]["unsupported"], list)

    def test_unsupported_never_empty(self):
        """metadata.unsupported always has at least one entry (HUGR note)."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        measure(circ, q)
        qir = circuit_to_ir(circ)
        assert len(qir["metadata"]["unsupported"]) >= 1

    def test_hugr_note_in_unsupported(self):
        """The HUGR flattening note is always present."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        measure(circ, q)
        qir = circuit_to_ir(circ)
        unsupported_text = " ".join(qir["metadata"]["unsupported"])
        assert "HUGR" in unsupported_text

    def test_extra_unsupported_propagated(self):
        """Extra unsupported strings passed to circuit_to_ir() appear in output."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        measure(circ, q)
        qir = circuit_to_ir(circ, extra_unsupported=["test: extra semantics"])
        assert any("extra semantics" in s for s in qir["metadata"]["unsupported"])


# ===========================================================================
# Resource counting
# ===========================================================================

class TestResourceCounting:
    """Tests for gate_count, depth, t_count, width."""

    def test_gate_count_excludes_measures(self):
        """gate_count does not include measure ops."""
        circ = GuppyCircuit(n_qubits=2)
        q0, q1 = circ.qubit(0), circ.qubit(1)
        q0 = h(circ, q0)
        q0, q1 = cx(circ, q0, q1)
        measure(circ, q0)
        measure(circ, q1)
        qir = circuit_to_ir(circ)
        # 2 gates (H, CX), 2 measures — gate_count should be 2
        assert qir["resources"]["gate_count"] == 2

    def test_t_count_single_t_gate(self):
        """A single T gate increments t_count by 1."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        q = t(circ, q)
        measure(circ, q)
        qir = circuit_to_ir(circ)
        assert qir["resources"]["t_count"] == 1

    def test_t_count_multiple_t_gates(self):
        """Multiple T gates accumulate in t_count."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        q = t(circ, q)
        q = t(circ, q)
        q = t(circ, q)
        measure(circ, q)
        qir = circuit_to_ir(circ)
        assert qir["resources"]["t_count"] == 3

    def test_t_dag_counts_as_t(self):
        """T-dagger counts as 1 T gate in the T-count metric."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        q = t_dag(circ, q)
        measure(circ, q)
        qir = circuit_to_ir(circ)
        assert qir["resources"]["t_count"] == 1

    def test_ccx_contributes_7_to_t_count(self):
        """CCX gate adds 7 to t_count (Selinger T-gate decomposition)."""
        circ = GuppyCircuit(n_qubits=3)
        q0, q1, q2 = circ.qubit(0), circ.qubit(1), circ.qubit(2)
        q0, q1, q2 = ccx(circ, q0, q1, q2)
        measure(circ, q0)
        measure(circ, q1)
        measure(circ, q2)
        qir = circuit_to_ir(circ)
        assert qir["resources"]["t_count"] == 7

    def test_width_equals_qubit_count(self):
        """width resource equals total allocated qubits."""
        circ = GuppyCircuit(n_qubits=4)
        for i in range(4):
            q = circ.qubit(i)
            measure(circ, q)
        qir = circuit_to_ir(circ)
        assert qir["resources"]["width"] == 4

    def test_depth_serial_circuit(self):
        """A chain of single-qubit gates has depth equal to gate count."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        q = h(circ, q)   # depth 1
        q = t(circ, q)   # depth 2
        q = h(circ, q)   # depth 3
        measure(circ, q) # depth 4
        qir = circuit_to_ir(circ)
        assert qir["resources"]["depth"] == 4  # including measure in depth

    def test_depth_parallel_circuits(self):
        """Two independent single-qubit chains have depth of the longer chain."""
        circ = GuppyCircuit(n_qubits=2)
        q0, q1 = circ.qubit(0), circ.qubit(1)
        # q0: H, T, H → depth 3 on qubit 0
        q0 = h(circ, q0)
        q0 = t(circ, q0)
        q0 = h(circ, q0)
        # q1: H → depth 1 on qubit 1
        q1 = h(circ, q1)
        measure(circ, q0)
        measure(circ, q1)
        qir = circuit_to_ir(circ)
        # depth = max(4 [q0: H+T+H+measure], 2 [q1: H+measure]) = 4
        assert qir["resources"]["depth"] == 4


# ===========================================================================
# Rotation gates
# ===========================================================================

class TestRotationGates:
    """Tests for parametric rotation gates."""

    def test_rx_params_preserved(self):
        """Rx gate stores its theta parameter in QIR."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        q = rx(circ, math.pi / 4, q)
        measure(circ, q)
        qir = circuit_to_ir(circ)
        gate_ops = [op for op in qir["ops"] if op.get("name") == "Rx"]
        assert len(gate_ops) == 1
        assert abs(gate_ops[0]["params"][0] - math.pi / 4) < 1e-9

    def test_rz_params_preserved(self):
        """Rz gate stores its phi parameter in QIR."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        q = rz(circ, math.pi / 3, q)
        measure(circ, q)
        qir = circuit_to_ir(circ)
        gate_ops = [op for op in qir["ops"] if op.get("name") == "Rz"]
        assert len(gate_ops) == 1
        assert abs(gate_ops[0]["params"][0] - math.pi / 3) < 1e-9


# ===========================================================================
# Two-qubit gate tests
# ===========================================================================

class TestTwoQubitGates:
    """Tests for CX, CZ, SWAP."""

    def test_cx_records_correct_qubit_order(self):
        """CX gate records [ctrl, tgt] in that order."""
        circ = GuppyCircuit(n_qubits=2)
        q0, q1 = circ.qubit(0), circ.qubit(1)
        q0, q1 = cx(circ, q0, q1)
        measure(circ, q0)
        measure(circ, q1)
        qir = circuit_to_ir(circ)
        cx_ops = [op for op in qir["ops"] if op.get("name") == "CX"]
        assert cx_ops[0]["qubits"] == [0, 1]

    def test_cz_gate_name(self):
        """CZ gate is recorded with name 'CZ'."""
        circ = GuppyCircuit(n_qubits=2)
        q0, q1 = circ.qubit(0), circ.qubit(1)
        q0, q1 = cz(circ, q0, q1)
        measure(circ, q0)
        measure(circ, q1)
        qir = circuit_to_ir(circ)
        names = [op.get("name") for op in qir["ops"] if op["type"] == "gate"]
        assert "CZ" in names

    def test_swap_gate_name(self):
        """SWAP gate is recorded with name 'SWAP'."""
        circ = GuppyCircuit(n_qubits=2)
        q0, q1 = circ.qubit(0), circ.qubit(1)
        q0, q1 = swap(circ, q0, q1)
        measure(circ, q0)
        measure(circ, q1)
        qir = circuit_to_ir(circ)
        names = [op.get("name") for op in qir["ops"] if op["type"] == "gate"]
        assert "SWAP" in names


# ===========================================================================
# Grover circuit
# ===========================================================================

class TestGroverCircuit:
    """Tests for the 2-qubit Grover example."""

    def _build_grover(self) -> GuppyCircuit:
        from guppy.examples.grover_2qubit import build_grover_2qubit
        return build_grover_2qubit()

    def test_grover_source_lang(self):
        qir = circuit_to_ir(self._build_grover())
        assert qir["source_lang"] == "guppy"

    def test_grover_qubits(self):
        qir = circuit_to_ir(self._build_grover())
        assert qir["qubits"] == 2

    def test_grover_unsupported_non_empty(self):
        qir = circuit_to_ir(self._build_grover())
        assert len(qir["metadata"]["unsupported"]) >= 1

    def test_grover_gate_count_matches_gate_ops(self):
        qir = circuit_to_ir(self._build_grover())
        gate_ops = [op for op in qir["ops"] if op["type"] == "gate"]
        assert qir["resources"]["gate_count"] == len(gate_ops)

    def test_grover_validate_passes(self):
        qir = circuit_to_ir(self._build_grover())
        errors = validate_ir(qir)
        assert errors == []


# ===========================================================================
# Schema version
# ===========================================================================

class TestSchemaVersion:
    """Version and structure compliance tests."""

    def test_version_string(self):
        """QIR version is '0.1.0'."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        measure(circ, q)
        qir = circuit_to_ir(circ)
        assert qir["version"] == "0.1.0"

    def test_required_top_level_keys_present(self):
        """All required QIR top-level keys are present."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        measure(circ, q)
        qir = circuit_to_ir(circ)
        required = {"version", "source_lang", "qubits", "cbits", "ops", "metadata", "resources"}
        assert required.issubset(set(qir.keys()))

    def test_resources_keys_present(self):
        """All required resources keys are present."""
        circ = GuppyCircuit(n_qubits=1)
        q = circ.qubit(0)
        measure(circ, q)
        qir = circuit_to_ir(circ)
        required = {"gate_count", "depth", "t_count", "width"}
        assert required.issubset(set(qir["resources"].keys()))
