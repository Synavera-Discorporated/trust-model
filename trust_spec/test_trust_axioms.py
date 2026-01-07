"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/test_trust_axioms.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Tests core trust axioms and accountability constraints.
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
    ACCOUNTABILITY_VIOLATION,
    CONSENT_VIOLATION,
    SERVICE_VIOLATION,
    STRUCTURAL_VIOLATION,
    TRUST_VIOLATION,
    attach_debug,
    assert_has_violation,
    assert_no_violation,
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


# Spec: TM1.0-S001, TM1.0-S018 | Property: P_SUSER_EXPLICIT, P_ACCOUNTABILITY_FLOW_TO_SUSER
# Why: Sovereignty must be explicit and identifiable.
# Why: Where authority exists, accountability must flow back to the consequence-bearing entity.
@given(service_id=stg.service_ids(), decision_id=stg.decision_ids())
def test_suser_required_for_decision(service_id: str, decision_id: str) -> None:
    """Test suser required for decision.

    Args:
        service_id: Test input value.
        decision_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=None,
        service_id=service_id,
        delegation_id=None,
        authority_chain_complete=False,
    )
    state, receipts = run_events([action])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [action], receipts)
    assert_has_violation(report, TRUST_VIOLATION.SUSER_UNIDENTIFIED)
    assert_has_violation(report, TRUST_VIOLATION.ACCOUNTABILITY_BREAK)


# Spec: TM1.0-S002 | Property: P_ADMIN_NOT_SOVEREIGN
# Why: Administrative control does not imply sovereignty; such capabilities remain delegated.
@given(suser_id=stg.suser_ids(), service_id=stg.service_ids(), decision_id=stg.decision_ids())
def test_admin_not_sovereign(suser_id: str, service_id: str, decision_id: str) -> None:
    """Test admin not sovereign.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        decision_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    delegation_id = "delegation_admin"
    events = [
        stg.make_delegation_event(delegation_id, suser_id, service_id),
        stg.make_service_action_event(
            decision_id=decision_id,
            suser_id=suser_id,
            service_id=service_id,
            delegation_id=delegation_id,
            admin_override=True,
        ),
    ]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, TRUST_VIOLATION.SOVEREIGNTY_ASSUMED)


# Spec: TM1.0-S003, TM1.0-S019 | Property: P_AUTHORITY_TRACEABLE, P_DIRECTIONAL_ACCOUNTABILITY_REQUIREMENTS
# Why: Authority must trace to the S-User; capability alone is not authority and is invalid without it.
# Why: Directional accountability requires upward traceability, no silent authority accumulation, and higher-layer inspection/intervention/revocation.
@given(suser_id=stg.suser_ids(), service_id=stg.service_ids(), decision_id=stg.decision_ids())
def test_authority_traceable(suser_id: str, service_id: str, decision_id: str) -> None:
    """Test authority traceable.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        decision_id: Test input value.

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
        delegation_id="missing_delegation",
        lower_layer_authority_accumulation=True,
    )
    state, receipts = run_events([action])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [action], receipts)
    assert_has_violation(report, TRUST_VIOLATION.AUTHORITY_UNTRACEABLE)
    assert_has_violation(report, TRUST_VIOLATION.DIRECTIONALITY_BREACH)


# Spec: TM1.0-S004, TM1.0-S005, TM1.0-S006 | Property: P_DELEGATION_EXPLICIT_SCOPED_REVOCABLE, P_SOVEREIGNTY_RETAINED, P_DELEGATION_NOT_BY_CONVENIENCE
# Why: Legitimate delegation is explicit, scoped, and revocable in principle.
# Why: Delegation does not transfer sovereignty; the S-User retains final authority and rights to inspect, contest, revoke.
# Why: Convenience, habituation, or dependency are not valid delegation.
@given(suser_id=stg.suser_ids(), service_id=stg.service_ids(), delegation_id=stg.delegation_ids())
def test_delegation_requirements(suser_id: str, service_id: str, delegation_id: str) -> None:
    """Test delegation requirements.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        delegation_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    delegation = stg.make_delegation_event(
        delegation_id,
        suser_id,
        service_id,
        explicit=False,
        revocable=False,
        derived_from_use=True,
        suser_can_revoke=False,
    )
    state, receipts = run_events([delegation])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [delegation], receipts)
    assert_has_violation(report, TRUST_VIOLATION.DELEGATION_INVALID)
    assert_has_violation(report, TRUST_VIOLATION.SOVEREIGNTY_DISPLACED)
    assert_has_violation(report, CONSENT_VIOLATION.IMPLICIT_DELEGATION)


# Spec: TM1.0-S007 | Property: P_AUTOMATION_WITHIN_DELEGATION
# Why: Automation does not change delegation limits; autonomous systems stay within delegated bounds.
@given(suser_id=stg.suser_ids(), service_id=stg.service_ids(), decision_id=stg.decision_ids())
def test_automation_within_delegation(suser_id: str, service_id: str, decision_id: str) -> None:
    """Test automation within delegation.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        decision_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    delegation_id = "delegation_auto"
    events = [
        stg.make_delegation_event(delegation_id, suser_id, service_id),
        stg.make_service_action_event(
            decision_id=decision_id,
            suser_id=suser_id,
            service_id=service_id,
            delegation_id=delegation_id,
            automated=True,
            within_scope=False,
        ),
    ]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, TRUST_VIOLATION.AUTONOMY_OVERREACH)


# Spec: TM1.0-S010 | Property: P_SERVICE_NON_SOVEREIGN
# Why: Services are not sovereign and may not substitute their incentives or silently enforce outcomes without delegated authority and disclosure.
@given(suser_id=stg.suser_ids(), service_id=stg.service_ids(), decision_id=stg.decision_ids())
def test_service_non_sovereign(suser_id: str, service_id: str, decision_id: str) -> None:
    """Test service non sovereign.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        decision_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    delegation_id = "delegation_service"
    events = [
        stg.make_delegation_event(delegation_id, suser_id, service_id),
        stg.make_service_action_event(
            decision_id=decision_id,
            suser_id=suser_id,
            service_id=service_id,
            delegation_id=delegation_id,
            disclosed=False,
        ),
    ]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, SERVICE_VIOLATION.SOVEREIGN_SUBSTITUTION)


# Spec: TM1.0-S011, TM1.0-S012 | Property: P_CONSENT_VALID_CRITERIA, P_CONSENT_INVALID_FORMS
# Why: Valid consent is informed, specific, and revocable with meaningful effect; constraints must be disclosed.
# Why: Bundled/coerced consent, dark patterns, continued-use assumptions, or non-withdrawable consent are invalid.
@given(suser_id=stg.suser_ids(), consent_id=stg.consent_ids())
def test_consent_validity_and_invalid_forms(suser_id: str, consent_id: str) -> None:
    """Test consent validity and invalid forms.

    Args:
        suser_id: Test input value.
        consent_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    consent = stg.make_consent_event(
        consent_id,
        suser_id,
        informed=False,
        specific=False,
        revocable=False,
        bundled=True,
        coerced=True,
    )
    state, receipts = run_events([consent])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [consent], receipts)
    assert_has_violation(report, CONSENT_VIOLATION.INVALID_CONSENT)
    assert_has_violation(report, CONSENT_VIOLATION.COERCED_OR_OPAQUE)


# Spec: TM1.0-S016, TM1.0-S017 | Property: P_INVALID_CONFIGURATIONS, P_NO_JUSTIFICATION_FOR_INVALID
# Why: The listed configurations (telemetry-driven without explanation, irrevocable delegation, inferred intent, coerced consent, no S-User) are invalid.
# Why: Structural failures cannot be justified by scale, optimisation, compliance, or market norms.
@given(telemetry_id=stg.telemetry_ids())
def test_invalid_configuration_and_no_justification(telemetry_id: str) -> None:
    """Test invalid configuration and no justification.

    Args:
        telemetry_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    telemetry = stg.make_telemetry_event(
        telemetry_id,
        influences=True,
        explained=False,
        justification="scale",
    )
    state, receipts = run_events([telemetry])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [telemetry], receipts)
    assert_has_violation(report, STRUCTURAL_VIOLATION.INVALID_STATE)
    assert_has_violation(report, STRUCTURAL_VIOLATION.JUSTIFIED_INVALIDITY)


# Spec: TM1.0-S020, TM1.0-S021, TM1.0-S022 | Property: P_TRUST_ORDERING, P_REPORTING_OBLIGATIONS_UPWARD, P_TRUST_DIAGNOSTIC_QUESTIONS
# Why: TRUST ordering is Users > Services > Telemetry; inversions are structural violations.
# Why: Reporting flows upward with legibility; telemetry reports to services, services to users; constraints on reporting must be reported.
# Why: Systems must answer origin, data influence, authoriser, inspector, and revoker; failure in legible terms is accountability failure.
@given(suser_id=stg.suser_ids(), service_id=stg.service_ids(), decision_id=stg.decision_ids())
def test_ordering_reporting_and_diagnostics(suser_id: str, service_id: str, decision_id: str) -> None:
    """Test ordering reporting and diagnostics.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        decision_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    delegation_id = "delegation_order"
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        ordering_inverted=True,
        report_to_suser=False,
        diagnostic_ready=False,
    )
    events = [stg.make_delegation_event(delegation_id, suser_id, service_id), action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, TRUST_VIOLATION.ORDERING_INVERTED)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.MISSING_REPORTING)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.DIAGNOSTIC_GAP)


# Spec: TM1.0-S018 | Property: P_ACCOUNTABILITY_FLOW_TO_SUSER
# Why: Where authority exists, accountability must flow back to the consequence-bearing entity.
@given(suser_id=stg.suser_ids(), service_id=stg.service_ids(), decision_id=stg.decision_ids())
def test_accountability_flow_to_suser_valid_path(suser_id: str, service_id: str, decision_id: str) -> None:
    """Test accountability flow to suser valid path.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        decision_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    delegation_id = "delegation_valid"
    events = [
        stg.make_delegation_event(delegation_id, suser_id, service_id),
        stg.make_service_action_event(
            decision_id=decision_id,
            suser_id=suser_id,
            service_id=service_id,
            delegation_id=delegation_id,
            authority_chain_complete=True,
        ),
    ]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_no_violation(report, TRUST_VIOLATION.ACCOUNTABILITY_BREAK)
