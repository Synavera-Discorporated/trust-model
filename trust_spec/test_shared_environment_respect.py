"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/test_shared_environment_respect.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Tests shared-environment respect and governance rules.
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
   2026-01-06 COD  Added SSE header for auditability.
   2026-01-06 COD  Added invariants and trust boundary notes.
   2026-01-06 COD  Added narrative spec comments for readability.
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
    AUDIT_VIOLATION,
    EVALUATION_VIOLATION,
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


# Spec: TM1.0-S023, TM1.0-S027 | Property: P_SHARED_ENV_NO_UNILATERAL_IMPACT, P_MULTIUSER_CONSENT
# Why: One S-User's delegation may not affect another without legible, contestable consent or governance basis.
# Why: Multi-user actions require mutual/federated consent; implicit consent is insufficient; impact must be legible; scope constrained if consent cannot be obtained.
@given(env_id=stg.environment_ids(), pair=stg.distinct_suser_pair())
def test_unilateral_impact_requires_consent(env_id: str, pair: tuple[str, str]) -> None:
    """Test unilateral impact requires consent.

    Args:
        env_id: Test input value.
        pair: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    actor, other = pair
    action = stg.make_shared_action_event(
        env_id,
        actor,
        affected_susers=[actor, other],
        consent_basis="none",
        consent_legible=False,
    )
    state, receipts = run_events([action])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [action], receipts)
    assert_has_violation(report, RESPECT_VIOLATION.UNILATERAL_IMPACT)
    assert_has_violation(report, RESPECT_VIOLATION.MUTUAL_CONSENT_MISSING)


# Spec: TM1.0-S024 | Property: P_SHARED_ENV_INTERNAL_AND_EXTERNAL
# Why: Shared-environment systems must satisfy both internal accountability and external boundary constraints; failure is violation.
@given(env_id=stg.environment_ids(), actor=stg.suser_ids())
def test_boundary_constraints_required(env_id: str, actor: str) -> None:
    """Test boundary constraints required.

    Args:
        env_id: Test input value.
        actor: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    action = stg.make_shared_action_event(
        env_id,
        actor,
        boundary_constraints_met=False,
        internal_accountable=False,
    )
    state, receipts = run_events([action])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [action], receipts)
    assert_has_violation(report, RESPECT_VIOLATION.BOUNDARY_IGNORED)


# Spec: TM1.0-S025 | Property: P_AUTHORITY_CONTAINMENT
# Why: Delegated authority is bounded by context; cross-context authority needs renewed explicit agreement; no automatic propagation; lack of containment makes shared use unsuitable.
@given(env_id=stg.environment_ids(), actor=stg.suser_ids())
def test_authority_containment(env_id: str, actor: str) -> None:
    """Test authority containment.

    Args:
        env_id: Test input value.
        actor: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    action = stg.make_shared_action_event(
        env_id,
        actor,
        cross_context=True,
        renewed_consent=False,
    )
    state, receipts = run_events([action])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [action], receipts)
    assert_has_violation(report, RESPECT_VIOLATION.CONTEXT_LEAK)


# Spec: TM1.0-S026 | Property: P_NON_INTERFERENCE
# Why: Actions for one S-User must not secretly influence/coerce others; undisclosed asymmetric influence is forbidden.
@given(env_id=stg.environment_ids(), pair=stg.distinct_suser_pair())
def test_non_interference(env_id: str, pair: tuple[str, str]) -> None:
    """Test non interference.

    Args:
        env_id: Test input value.
        pair: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    actor, other = pair
    action = stg.make_shared_action_event(
        env_id,
        actor,
        affected_susers=[actor, other],
        influence_disclosed=False,
    )
    state, receipts = run_events([action])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [action], receipts)
    assert_has_violation(report, RESPECT_VIOLATION.NON_INTERFERENCE_BREACH)


# Spec: TM1.0-S028 | Property: P_BOUNDARY_GOVERNANCE_INTERFACES
# Why: Boundary governance operates at system interfaces.
@given(env_id=stg.environment_ids())
def test_boundary_interface_rules(env_id: str) -> None:
    """Test boundary interface rules.

    Args:
        env_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    rule = stg.make_boundary_rule_event(env_id, interface_rules_present=False)
    state, receipts = run_events([rule])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [rule], receipts)
    assert_has_violation(report, GOVERNANCE_VIOLATION.INTERFACE_GAP)


# Spec: TM1.0-S029 | Property: P_ENTRY_CONDITIONS_REQUIRED
# Why: Participation is conditional; systems must meet explicit entry conditions or are unsuitable for shared contexts.
@given(env_id=stg.environment_ids())
def test_entry_conditions_required(env_id: str) -> None:
    """Test entry conditions required.

    Args:
        env_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    entry = stg.make_entry_condition_event(env_id, conditions_defined=False)
    request = stg.make_entry_request_event(env_id, entry_conditions_met=False)
    state, receipts = run_events([entry, request])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [entry, request], receipts)
    assert_has_violation(report, GOVERNANCE_VIOLATION.MISSING_ENTRY_CONDITIONS)


# Spec: TM1.0-S030 | Property: P_CONTINUOUS_GOVERNANCE_AND_REVOCATION
# Why: Governance is continuous; environments must observe, detect, and revoke; revocation is legible/contestable; irreversible/delayed limits must be disclosed.
@given(env_id=stg.environment_ids())
def test_revocation_policy_requirements(env_id: str) -> None:
    """Test revocation policy requirements.

    Args:
        env_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    policy = stg.make_revocation_policy_event(
        env_id,
        revocation_legible=False,
        revocation_contestable=False,
    )
    state, receipts = run_events([policy])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [policy], receipts)
    assert_has_violation(report, GOVERNANCE_VIOLATION.REVOCATION_DEFECT)


# Spec: TM1.0-S031 | Property: P_MUTUAL_CONSENT_BASIS
# Why: Legitimacy arises from mutual/federated consent; no unilateral influence without visible, contestable basis.
@given(env_id=stg.environment_ids(), pair=stg.distinct_suser_pair())
def test_mutual_consent_basis(env_id: str, pair: tuple[str, str]) -> None:
    """Test mutual consent basis.

    Args:
        env_id: Test input value.
        pair: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    actor, other = pair
    action = stg.make_shared_action_event(
        env_id,
        actor,
        affected_susers=[actor, other],
        consent_basis="unilateral",
    )
    state, receipts = run_events([action])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [action], receipts)
    assert_has_violation(report, RESPECT_VIOLATION.UNILATERAL_CONSENT_BASIS)


# Spec: TM1.0-S033 | Property: P_FEDERATED_GOVERNANCE_REQUIREMENTS
# Why: Federated models must keep entry/exit, non-interference, auditability, contestation; lack of central authority heightens need for explicit rules.
@given(env_id=stg.environment_ids())
def test_federated_governance_requirements(env_id: str) -> None:
    """Test federated governance requirements.

    Args:
        env_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    event = stg.make_federated_governance_event(env_id, contestable=False)
    state, receipts = run_events([event])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [event], receipts)
    assert_has_violation(report, GOVERNANCE_VIOLATION.FEDERATED_GAP)


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
    event = stg.make_boundary_failure_modes_event(env_id, hidden_influence=True)
    state, receipts = run_events([event])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [event], receipts)
    assert_has_violation(report, GOVERNANCE_VIOLATION.FAILURE_MODE_IGNORED)


# Spec: TM1.0-S035 | Property: P_RESPECT_CORE_PRINCIPLES
# Why: RESPECT requires boundary integrity, non-coercion, mutual legibility, contextual consent, and contestability.
@given(env_id=stg.environment_ids())
def test_respect_core_principles(env_id: str) -> None:
    """Test respect core principles.

    Args:
        env_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    event = stg.make_respect_principles_event(env_id, mutual_legibility=False)
    state, receipts = run_events([event])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [event], receipts)
    assert_has_violation(report, RESPECT_VIOLATION.PRINCIPLE_BREACH)


# Spec: TM1.0-S036 | Property: P_RESPECT_EXPLICIT_BOUNDARIES
# Why: RESPECT requires explicit boundaries (no centralised control required).
@given(env_id=stg.environment_ids())
def test_explicit_boundaries_required(env_id: str) -> None:
    """Test explicit boundaries required.

    Args:
        env_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    event = stg.make_boundary_declaration_event(env_id, explicit=False)
    state, receipts = run_events([event])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [event], receipts)
    assert_has_violation(report, RESPECT_VIOLATION.IMPLICIT_BOUNDARIES)


# Spec: TM1.0-S037 | Property: P_RESPECT_DECLARATIONS_AND_ENFORCEMENT
# Why: Systems must declare scope, influence modes, and boundaries; violations justify constraint/exclusion; enforcement must be legible, proportionate, contestable.
@given(env_id=stg.environment_ids())
def test_participation_declarations(env_id: str) -> None:
    """Test participation declarations.

    Args:
        env_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    event = stg.make_participation_declaration_event(env_id, enforcement_legible=False)
    state, receipts = run_events([event])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [event], receipts)
    assert_has_violation(report, RESPECT_VIOLATION.OPAQUE_ENFORCEMENT)


# Spec: TM1.0-S038 | Property: P_SHARED_SPACE_DIAGNOSTIC
# Why: Shared-space systems must answer who authorised and whose boundaries are affected; unclear answers are illegitimate.
@given(env_id=stg.environment_ids(), actor=stg.suser_ids())
def test_shared_space_diagnostic(env_id: str, actor: str) -> None:
    """Test shared space diagnostic.

    Args:
        env_id: Test input value.
        actor: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    action = stg.make_shared_action_event(env_id, actor, diagnostic_ready=False)
    state, receipts = run_events([action])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [action], receipts)
    assert_has_violation(report, RESPECT_VIOLATION.DIAGNOSTIC_GAP)


# Spec: TM1.0-S039 | Property: P_NONCOMPLIANCE_IF_UNDETERMINABLE
# Why: If authority/delegation/reporting/boundary properties are indeterminable, the system is non-compliant.
@given(env_id=stg.environment_ids())
def test_noncompliance_if_undeterminable(env_id: str) -> None:
    """Test noncompliance if undeterminable.

    Args:
        env_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    event = stg.make_shared_action_event(env_id, "suser_a")
    event["undeterminable"] = True
    state, receipts = run_events([event])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [event], receipts)
    assert_has_violation(report, EVALUATION_VIOLATION.UNDETERMINABLE_PASS)


# Spec: TM1.0-S041 | Property: P_RESPECT_AUDIT_MINIMUM
# Why: RESPECT audit minimum includes boundaries, entry conditions, non-interference, mutual consent mechanisms, and contestable enforcement.
@given(audit_id=stg.audit_ids())
def test_respect_audit_minimum(audit_id: str) -> None:
    """Test respect audit minimum.

    Args:
        audit_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    audit = stg.make_respect_audit_event(audit_id, minimum_met=False)
    state, receipts = run_events([audit])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [audit], receipts)
    assert_has_violation(report, AUDIT_VIOLATION.RESPECT_MINIMUM_MISSING)
