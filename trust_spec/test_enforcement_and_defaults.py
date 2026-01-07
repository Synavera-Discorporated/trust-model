"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/test_enforcement_and_defaults.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Tests enforcement constraints and non-coercive defaults.
 Invariants:
   Tests mutate only in-memory state via trust_impl.apply_event.
 Trust Boundaries:
   No external I/O; relies on trust_impl API and Hypothesis inputs.
 Security / Safety Notes:
   N/A.
 Dependencies:
   pytest, hypothesis, trust_impl, trust_spec.strategies.
 Operational Scope:
   Executed under pytest as part of the trust-spec suite.
 Revision History:
   2026-01-06 COD  Added SSE header for auditability; Added invariants and trust boundary notes; Added narrative spec comments for readability.
------------------------------------------------------------
 SSE Principles Observed:
   - Explicit Result-based API (no silent failures)
   - Narrative comments for auditability
   - No hidden state changes; all mutations are explicit
   - Modular structure with clear boundaries
============================================================
"""

from __future__ import annotations

from hypothesis import given

from trust_spec import strategies as stg
import trust_impl
from trust_spec.violations import (
    ENFORCEMENT_VIOLATION,
    GOVERNANCE_VIOLATION,
    RESPECT_VIOLATION,
    attach_debug,
    assert_has_violation,
)


def run_events(events: list[dict[str, object]]) -> tuple[trust_impl.State, list[dict[str, object]]]:
    """Run events through the SUT and collect receipts.

    Args:
        events: Event sequence to apply.

    Returns:
        Tuple of (state, receipts) after applying events.

    Resources:
        In-memory state and receipts owned by the caller.

    Raises:
        None.
    """
    state = trust_impl.State()
    receipts = []
    for event in events:
        state, new_receipts = trust_impl.apply_event(state, event)
        receipts.extend(new_receipts)
    return state, receipts


# Spec: TM1.0-S043 | Property: P_SOVEREIGNTY_COMPATIBLE_ENFORCEMENT
# Why: Enforcement must not undermine sovereignty; it is proportionate, transparent, contestable, reversible where feasible; punitive/opaque enforcement is incompatible.
@given(enforcement_id=stg.enforcement_ids(), enforcer_id=stg.service_ids())
def test_enforcement_sovereignty_compatibility(enforcement_id: str, enforcer_id: str) -> None:
    """Test enforcement sovereignty compatibility.

    Args:
        enforcement_id: Test input value.
        enforcer_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    enforcement = stg.make_enforcement_event(
        enforcement_id,
        enforcer_id,
        proportionate=False,
        transparent=False,
        contestable=False,
        reversible=False,
        punitive=True,
    )
    state, receipts = run_events([enforcement])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [enforcement], receipts)
    assert_has_violation(report, ENFORCEMENT_VIOLATION.SOVEREIGNTY_INCOMPATIBLE)


# Spec: TM1.0-S044 | Property: P_ENFORCEMENT_LEGIBLE_ATTRIBUTABLE_CONTESTABLE
# Why: Enforcement must be legible, attributable, and contestable by affected S-Users.
@given(enforcement_id=stg.enforcement_ids(), enforcer_id=stg.service_ids())
def test_enforcement_attribution_required(enforcement_id: str, enforcer_id: str) -> None:
    """Test enforcement attribution required.

    Args:
        enforcement_id: Test input value.
        enforcer_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    enforcement = stg.make_enforcement_event(
        enforcement_id,
        enforcer_id,
        attributable=False,
    )
    state, receipts = run_events([enforcement])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [enforcement], receipts)
    assert_has_violation(report, ENFORCEMENT_VIOLATION.NO_ATTRIBUTION)


# Spec: TM1.0-S032 | Property: P_NON_COERCIVE_DEFAULTS
# Why: Defaults must not exploit bias, expand scope, or privilege platform incentives; impactful defaults must be justifiable and reversible.
@given(default_id=stg.default_ids())
def test_non_coercive_defaults(default_id: str) -> None:
    """Test non coercive defaults.

    Args:
        default_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    default = stg.make_default_event(
        default_id,
        exploits_bias=True,
        justifiable=False,
        reversible=False,
    )
    state, receipts = run_events([default])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [default], receipts)
    assert_has_violation(report, RESPECT_VIOLATION.COERCIVE_DEFAULT)


# Spec: TM1.0-S034 | Property: P_BOUNDARY_GOVERNANCE_FAILURE_MODES
# Why: Failure modes include implicit-consent participation, opaque enforcement, hidden influence, and non-revocable participation.
@given(env_id=stg.environment_ids())
def test_boundary_failure_modes(env_id: str) -> None:
    """Test boundary failure modes.

    Args:
        env_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    failure = stg.make_boundary_failure_modes_event(env_id, opaque_enforcement=True)
    state, receipts = run_events([failure])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [failure], receipts)
    assert_has_violation(report, GOVERNANCE_VIOLATION.FAILURE_MODE_IGNORED)


# Spec: TM1.0-S037 | Property: P_RESPECT_DECLARATIONS_AND_ENFORCEMENT
# Why: Systems must declare scope, influence modes, and boundaries; violations justify constraint/exclusion; enforcement must be legible, proportionate, contestable.
@given(env_id=stg.environment_ids())
def test_participation_declaration_enforcement(env_id: str) -> None:
    """Test participation declaration enforcement.

    Args:
        env_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    declaration = stg.make_participation_declaration_event(env_id, enforcement_contestable=False)
    state, receipts = run_events([declaration])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [declaration], receipts)
    assert_has_violation(report, RESPECT_VIOLATION.OPAQUE_ENFORCEMENT)
