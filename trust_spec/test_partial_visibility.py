"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/test_partial_visibility.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Tests partial visibility and redaction behavior in the S-User view.
 Invariants:
   Tests mutate only in-memory state via trust_impl.apply_event.
 Trust Boundaries:
   No external I/O; relies on trust_impl API and Hypothesis inputs.
 Security / Safety Notes:
   N/A.
 Dependencies:
   pytest, trust_impl, trust_spec.strategies.
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

from trust_spec import strategies as stg
import trust_impl
from trust_spec.violations import (
    ACCOUNTABILITY_VIOLATION,
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


# Spec: TM1.0-S021 | Property: P_REPORTING_OBLIGATIONS_UPWARD
# Why: Reporting flows upward with legibility; telemetry reports to services, services to users; constraints on reporting must be reported.
def test_view_missing_receipt_is_missing_reporting() -> None:
    """Test view missing receipt is missing reporting.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    suser_id = "suser_view"
    service_id = "service_view"
    delegation_id = "delegation_view"
    decision_id = "decision_view"
    delegation = stg.make_delegation_event(delegation_id, suser_id, service_id)
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        report_to_suser=True,
        receipt_delivered=False,
    )
    events = [delegation, action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust_view(state, suser_id)
    attach_debug(report, events, receipts)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.MISSING_REPORTING)


# Spec: TM1.0-S013, TM1.0-S014 | Property: P_TRANSPARENCY_NEEDS_LEGIBILITY, P_EXPLANATIONS_LEGIBLE
# Why: Transparency without legibility fails accountability; raw logs alone are insufficient.
# Why: Explanations must be accessible, contextual, and relevant to decisions affecting the S-User.
def test_view_redacted_explanation_is_non_legible() -> None:
    """Test view redacted explanation is non legible.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    suser_id = "suser_redact"
    service_id = "service_redact"
    delegation_id = "delegation_redact"
    decision_id = "decision_redact"
    delegation = stg.make_delegation_event(delegation_id, suser_id, service_id)
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        report_to_suser=True,
        explanation="contextual",
        explanation_legible=True,
        redacted_fields=["explanation", "explanation_legible"],
    )
    events = [delegation, action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust_view(state, suser_id)
    attach_debug(report, events, receipts)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.NON_LEGIBLE_EXPLANATION)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.ILLEGIBLE_REPORTING)


# Spec: TM1.0-S013, TM1.0-S014 | Property: P_TRANSPARENCY_NEEDS_LEGIBILITY, P_EXPLANATIONS_LEGIBLE
# Why: Transparency without legibility fails accountability; raw logs alone are insufficient.
# Why: Explanations must be accessible, contextual, and relevant to decisions affecting the S-User.
def test_view_delayed_explanation_is_non_legible() -> None:
    """Test view delayed explanation is non legible.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    suser_id = "suser_delay"
    service_id = "service_delay"
    delegation_id = "delegation_delay"
    decision_id = "decision_delay"
    delegation = stg.make_delegation_event(delegation_id, suser_id, service_id)
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        report_to_suser=True,
        explanation="contextual",
        explanation_legible=True,
        explanation_delivered=False,
    )
    events = [delegation, action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust_view(state, suser_id)
    attach_debug(report, events, receipts)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.NON_LEGIBLE_EXPLANATION)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.ILLEGIBLE_REPORTING)


# Spec: TM1.0-S015, TM1.0-S022 | Property: P_ACCOUNTABILITY_CRITERIA, P_TRUST_DIAGNOSTIC_QUESTIONS
# Why: Accountability requires traceability, legible explanation, and challenge/correct/revoke mechanisms; unexplained outcomes fail.
# Why: Systems must answer origin, data influence, authoriser, inspector, and revoker; failure in legible terms is accountability failure.
def test_view_redacted_authority_chain_is_accountability_break() -> None:
    """Test view redacted authority chain is accountability break.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    suser_id = "suser_chain"
    service_id = "service_chain"
    delegation_id = "delegation_chain"
    decision_id = "decision_chain"
    delegation = stg.make_delegation_event(delegation_id, suser_id, service_id)
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        report_to_suser=True,
        redacted_fields=["authority_chain"],
    )
    events = [delegation, action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust_view(state, suser_id)
    attach_debug(report, events, receipts)
    assert_has_violation(report, TRUST_VIOLATION.ACCOUNTABILITY_BREAK)
