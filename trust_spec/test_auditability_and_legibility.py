"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/test_auditability_and_legibility.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Tests auditability, reporting constraints, and explanation legibility rules.
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
   2026-01-06 COD  Added evaluator safety meta-invariant tests.
------------------------------------------------------------
 SSE Principles Observed:
   - Explicit Result-based API (no silent failures)
   - Narrative comments for auditability
   - No hidden state changes; all mutations are explicit
   - Modular structure with clear boundaries
============================================================
"""

from __future__ import annotations

from hypothesis import given, strategies as st

from trust_spec import strategies as stg
import trust_impl
from trust_spec.violations import (
    ACCOUNTABILITY_VIOLATION,
    AUDIT_VIOLATION,
    EVALUATION_VIOLATION,
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


# Spec: TM1.0-S013, TM1.0-S014 | Property: P_TRANSPARENCY_NEEDS_LEGIBILITY, P_EXPLANATIONS_LEGIBLE
# Why: Transparency without legibility fails accountability; raw logs alone are insufficient.
# Why: Explanations must be accessible, contextual, and relevant to decisions affecting the S-User.
@given(suser_id=stg.suser_ids(), service_id=stg.service_ids(), decision_id=stg.decision_ids())
def test_legibility_required_for_reporting(suser_id: str, service_id: str, decision_id: str) -> None:
    """Test legibility required for reporting.

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
    delegation_id = "delegation_legible"
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        report_to_suser=True,
        explanation_legible=False,
    )
    events = [stg.make_delegation_event(delegation_id, suser_id, service_id), action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.ILLEGIBLE_REPORTING)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.NON_LEGIBLE_EXPLANATION)


# Spec: TM1.0-S015 | Property: P_ACCOUNTABILITY_CRITERIA
# Why: Accountability requires traceability, legible explanation, and challenge/correct/revoke mechanisms; unexplained outcomes fail.
@given(suser_id=stg.suser_ids(), service_id=stg.service_ids(), decision_id=stg.decision_ids())
def test_accountability_requires_contestation_and_revocation(suser_id: str, service_id: str, decision_id: str) -> None:
    """Test accountability requires contestation and revocation.

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
    delegation_id = "delegation_accountable"
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        contest_path=None,
        revocation_path=None,
    )
    events = [stg.make_delegation_event(delegation_id, suser_id, service_id), action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.NON_ACCOUNTABLE_OUTCOME)


# Spec: TM1.0-S021 | Property: P_REPORTING_OBLIGATIONS_UPWARD
# Why: Reporting flows upward with legibility; telemetry reports to services, services to users; constraints on reporting must be reported.
@given(suser_id=stg.suser_ids(), service_id=stg.service_ids(), decision_id=stg.decision_ids())
def test_reporting_constraints_disclosed(suser_id: str, service_id: str, decision_id: str) -> None:
    """Test reporting constraints disclosed.

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
    delegation_id = "delegation_reporting"
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        reporting_constraints=True,
        reporting_constraints_disclosed=False,
    )
    events = [stg.make_delegation_event(delegation_id, suser_id, service_id), action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.MISSING_REPORTING)


# Spec: TM1.0-S022 | Property: P_TRUST_DIAGNOSTIC_QUESTIONS
# Why: Systems must answer origin, data influence, authoriser, inspector, and revoker; failure in legible terms is accountability failure.
@given(suser_id=stg.suser_ids(), service_id=stg.service_ids(), decision_id=stg.decision_ids())
def test_diagnostic_answers_required(suser_id: str, service_id: str, decision_id: str) -> None:
    """Test diagnostic answers required.

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
    delegation_id = "delegation_diag"
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        diagnostic_ready=False,
    )
    events = [stg.make_delegation_event(delegation_id, suser_id, service_id), action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.DIAGNOSTIC_GAP)


# Spec: TM1.0-S040 | Property: P_TRUST_AUDIT_MINIMUM
# Why: TRUST audit minimum includes S-User identification, explicit delegation, legible reporting, traceability, and revocation.
@given(audit_id=stg.audit_ids())
def test_trust_audit_minimum(audit_id: str) -> None:
    """Test trust audit minimum.

    Args:
        audit_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    audit = stg.make_trust_audit_event(audit_id, minimum_met=False)
    state, receipts = run_events([audit])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [audit], receipts)
    assert_has_violation(report, AUDIT_VIOLATION.TRUST_MINIMUM_MISSING)


# Spec: TM1.0-S045 | Property: P_USER_COMPREHENSION_REQUIRED
# Why: S-Users must be able to understand, interrogate, and act on disclosures; otherwise accountability collapses to opacity.
@given(disclosure_id=stg.disclosure_ids())
def test_user_comprehension_required(disclosure_id: str) -> None:
    """Test user comprehension required.

    Args:
        disclosure_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    disclosure = stg.make_disclosure_event(disclosure_id, user_actionable=False)
    state, receipts = run_events([disclosure])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [disclosure], receipts)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.NON_ACTIONABLE_DISCLOSURE)


# Spec: TM1.0-S046 | Property: P_SYSTEMS_HONEST_ABOUT_LIMITS
# Why: Systems must be honest about limitations and boundaries.
@given(limitation_id=stg.limitation_ids())
def test_limits_disclosed(limitation_id: str) -> None:
    """Test limits disclosed.

    Args:
        limitation_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    limitation = stg.make_limitation_disclosure_event(limitation_id, limits_disclosed=False)
    state, receipts = run_events([limitation])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [limitation], receipts)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.LIMITS_UNDISCLOSED)


# Spec: TM1.0-S042 | Property: P_EVALUATION_NON_REDUCTIONIST
# Why: Evaluation must be multi-dimensional and contextual, not a single score.
@given(score=st.floats(min_value=0.0, max_value=1.0))
def test_evaluation_non_reductionist(score: float) -> None:
    """Test evaluation non reductionist.

    Args:
        score: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    event = {"type": "reductionist_metric", "score": score}
    state, receipts = run_events([event])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [event], receipts)
    assert_has_violation(report, EVALUATION_VIOLATION.REDUCTIONISM)


# Spec: TM1.0-S021 | Property: P_REPORTING_OBLIGATIONS_UPWARD
# Why: Reporting flows upward with legibility; telemetry reports to services, services to users; constraints on reporting must be reported.
@given(telemetry_id=stg.telemetry_ids())
def test_reporting_obligations_satisfied(telemetry_id: str) -> None:
    """Test reporting obligations satisfied.

    Args:
        telemetry_id: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    telemetry = stg.make_telemetry_event(telemetry_id, reports_to_service=True)
    state, receipts = run_events([telemetry])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [telemetry], receipts)
    assert_no_violation(report, ACCOUNTABILITY_VIOLATION.MISSING_REPORTING)


# Meta-invariant: Evaluators must not throw on malformed inputs.
# Why: Crashing the evaluator would erase accountability exactly when it is most needed.
def test_evaluator_handles_malformed_trust_state() -> None:
    """Test evaluator handles malformed trust state.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When expected safety violations are missing.
    """
    state = trust_impl.State()
    state.decisions.append(
        {
            "type": "service_action",
            "decision_id": "decision_malformed",
            "suser_id": "suser_malformed",
            "service_id": "service_malformed",
            "delegation_id": "delegation_malformed",
            "time": ["not", "an", "int"],
        }
    )
    report = trust_impl.evaluate_trust(state)
    assert_has_violation(report, STRUCTURAL_VIOLATION.INVALID_STATE)
    assert_has_violation(report, TRUST_VIOLATION.ACCOUNTABILITY_BREAK)


# Meta-invariant: Evaluators must not throw on malformed inputs.
# Why: If respect evaluation crashes, shared-environment harm becomes non-auditable.
def test_evaluator_handles_malformed_respect_state() -> None:
    """Test evaluator handles malformed respect state.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When expected safety violations are missing.
    """
    state = trust_impl.State()
    state.event_log.append(
        {
            "type": "revocation_policy",
            "revocation_delay": True,
            "revocation_delay_disclosed": True,
            "time": ["not", "an", "int"],
        }
    )
    report = trust_impl.evaluate_respect(state)
    assert_has_violation(report, STRUCTURAL_VIOLATION.INVALID_STATE)
    assert_has_violation(report, TRUST_VIOLATION.ACCOUNTABILITY_BREAK)
