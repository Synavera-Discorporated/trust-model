"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/test_temporal_adversaries.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Tests temporal adversary cases like expiry and delayed revocation.
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
   2026-01-06 COD  Added SSE header for auditability; Added invariants and trust boundary notes; Added narrative spec comments for readability; Added pressure-point tests for audit lag and drift; Focused interpolation test on authority gap requirement; Added exemplar capture hooks for selected failures.
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
from hypothesis import strategies as st

from trust_spec import exemplars
from trust_spec import strategies as stg
import trust_impl
from trust_spec.violations import (
    GOVERNANCE_VIOLATION,
    RESPECT_VIOLATION,
    TRUST_VIOLATION,
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


# Spec: TM1.0-S004, TM1.0-S018 | Property: P_DELEGATION_EXPLICIT_SCOPED_REVOCABLE, P_ACCOUNTABILITY_FLOW_TO_SUSER
# Why: Legitimate delegation is explicit, scoped, and revocable in principle.
# Why: Where authority exists, accountability must flow back to the consequence-bearing entity.
@given(
    suser_id=stg.suser_ids(),
    service_id=stg.service_ids(),
    delegation_id=stg.delegation_ids(),
    decision_id=stg.decision_ids(),
    duration=stg.durations(),
    extra=st.integers(min_value=1, max_value=5),
)
def test_expired_delegation_breaks_authority(
    suser_id: str, service_id: str, delegation_id: str, decision_id: str, duration: int, extra: int
) -> None:
    """Test expired delegation breaks authority.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        delegation_id: Test input value.
        decision_id: Test input value.
        duration: Test input value.
        extra: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    scope = {"purpose": "p", "context_id": "ctx", "duration": duration, "effect": "e"}
    delegation = stg.make_delegation_event(
        delegation_id, suser_id, service_id, scope=scope, revocable=True
    )
    advance = stg.make_time_advance_event(duration + extra)
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        basis_in_delegation=True,
    )
    events = [delegation, advance, action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    exemplars.capture_on_failure(
        exemplar_id="TM1.0-EX-AUTH-POSTHOC-001",
        kind="trust",
        events=events,
        receipts=receipts,
        report=report,
        assertion=lambda: assert_has_violation(report, TRUST_VIOLATION.AUTHORITY_UNTRACEABLE),
        source=exemplars.source_metadata(
            test_name="test_interpolation_only_audit_trail_fails_authority"
        ),
        notes="Decision recorded before delegation; audit trail cannot backfill authority.",
        spec_map=["TM1.0-S003", "TM1.0-S018"],
    )


# Spec: TM1.0-S030 | Property: P_CONTINUOUS_GOVERNANCE_AND_REVOCATION
# Why: Governance is continuous; environments must observe, detect, and revoke; revocation is legible/contestable; irreversible/delayed limits must be disclosed.
@given(
    suser_id=stg.suser_ids(),
    service_id=stg.service_ids(),
    delegation_id=stg.delegation_ids(),
    delay=st.integers(min_value=1, max_value=5),
)
def test_revocation_delay_requires_disclosure(suser_id: str, service_id: str, delegation_id: str, delay: int) -> None:
    """Test revocation delay requires disclosure.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        delegation_id: Test input value.
        delay: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    delegation = stg.make_delegation_event(delegation_id, suser_id, service_id)
    revoke = stg.make_revoke_delegation_event(
        delegation_id, delay=delay, delay_disclosed=False
    )
    advance = stg.make_time_advance_event(delay)
    events = [delegation, revoke, advance]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, GOVERNANCE_VIOLATION.REVOCATION_DEFECT)


# Spec: TM1.0-S003, TM1.0-S018 | Property: P_AUTHORITY_TRACEABLE, P_ACCOUNTABILITY_FLOW_TO_SUSER
# Why: Decision-time authority must be complete; audits cannot retroactively fabricate a valid chain.
@given(
    suser_id=stg.suser_ids(),
    service_id=stg.service_ids(),
    delegation_id=stg.delegation_ids(),
    decision_id=stg.decision_ids(),
    audit_id=stg.audit_ids(),
    delay=st.integers(min_value=1, max_value=3),
)
def test_interpolation_only_audit_trail_fails_authority(
    suser_id: str,
    service_id: str,
    delegation_id: str,
    decision_id: str,
    audit_id: str,
    delay: int,
) -> None:
    """Test interpolation-only audit trail fails authority.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        delegation_id: Test input value.
        decision_id: Test input value.
        audit_id: Test input value.
        delay: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        authority_chain_complete=False,
    )
    advance = stg.make_time_advance_event(delay)
    delegation = stg.make_delegation_event(delegation_id, suser_id, service_id)
    audit = stg.make_trust_audit_event(audit_id, minimum_met=True)
    events = [action, advance, delegation, audit]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, TRUST_VIOLATION.AUTHORITY_UNTRACEABLE)


# Spec: TM1.0-S008, TM1.0-S009 | Property: P_TELEMETRY_SUBORDINATION, P_TELEMETRY_NO_AUTHORITY
# Why: Telemetry is descriptive only and must not define policy, enforce, trigger irreversible outcomes, or accumulate authority.
# Why: Telemetry influence must be visible and explainable; human-inexplicable telemetry-driven decisions are invalid.
@given(
    telemetry_id=stg.telemetry_ids(),
    suser_id=stg.suser_ids(),
    service_id=stg.service_ids(),
    decision_id=stg.decision_ids(),
    exposures=st.integers(min_value=2, max_value=8),
)
def test_telemetry_inertia_does_not_create_authority(
    telemetry_id: str, suser_id: str, service_id: str, decision_id: str, exposures: int
) -> None:
    """Test telemetry inertia does not create authority.

    Args:
        telemetry_id: Test input value.
        suser_id: Test input value.
        service_id: Test input value.
        decision_id: Test input value.
        exposures: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    telemetry_events = []
    for _ in range(exposures):
        telemetry_events.append(
            stg.make_telemetry_event(
                telemetry_id,
                influences=True,
                explained=True,
                human_explainable=True,
                reports_to_service=True,
            )
        )
        telemetry_events.append(stg.make_time_advance_event(1))
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=None,
        telemetry_refs=[telemetry_id],
        basis_in_delegation=True,
    )
    events = telemetry_events + [action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, TRUST_VIOLATION.AUTHORITY_UNTRACEABLE)


# Spec: TM1.0-S007 | Property: P_AUTOMATION_WITHIN_DELEGATION
# Why: Self-optimizing drift counts as automation and requires explicit mutation authority.
@given(
    suser_id=stg.suser_ids(),
    service_id=stg.service_ids(),
    delegation_id=stg.delegation_ids(),
    decision_id=stg.decision_ids(),
)
def test_behavior_drift_requires_mutation_authority(
    suser_id: str,
    service_id: str,
    delegation_id: str,
    decision_id: str,
) -> None:
    """Test behavior drift requires mutation authority.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        delegation_id: Test input value.
        decision_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    delegation = stg.make_delegation_event(delegation_id, suser_id, service_id)
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        automated=True,
        behavior_drift=True,
        mutation_authority=False,
    )
    events = [delegation, action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    exemplars.capture_on_failure(
        exemplar_id="TM1.0-EX-AUTO-DRIFT-001",
        kind="trust",
        events=events,
        receipts=receipts,
        report=report,
        assertion=lambda: assert_has_violation(report, TRUST_VIOLATION.AUTONOMY_OVERREACH),
        source=exemplars.source_metadata(
            test_name="test_behavior_drift_requires_mutation_authority"
        ),
        notes="Behavior drift without delegated mutation authority.",
        spec_map=["TM1.0-S007"],
    )


# Spec: TM1.0-S032 | Property: P_NON_COERCIVE_DEFAULTS
# Why: Defaults must not exploit bias, expand scope, or privilege platform incentives; impactful defaults must be justifiable and reversible.
@given(
    default_id=stg.default_ids(),
    duration=stg.durations(),
)
def test_time_based_default_expiry_is_enforced(default_id: str, duration: int) -> None:
    """Test time based default expiry is enforced.

    Args:
        default_id: Test input value.
        duration: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    default_event = stg.make_default_event(
        default_id=default_id,
        exploits_bias=False,
        expands_scope=False,
        privileges_platform=False,
        justifiable=True,
        reversible=True,
        duration=duration,
        active=True,
    )
    advance = stg.make_time_advance_event(duration + 1)
    events = [default_event, advance]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, RESPECT_VIOLATION.COERCIVE_DEFAULT)
