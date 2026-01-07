"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/test_compliance_gaming.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Tests adversarial compliance gaming scenarios in trust evaluation.
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
    ENFORCEMENT_VIOLATION,
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


# Spec: TM1.0-S014 | Property: P_EXPLANATIONS_LEGIBLE
# Why: Explanations must be accessible, contextual, and relevant to decisions affecting the S-User.
def test_meaningless_explanation_is_non_legible() -> None:
    """Test meaningless explanation is non legible.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    suser_id = "suser_explain"
    service_id = "service_explain"
    delegation_id = "delegation_explain"
    decision_id = "decision_explain"
    delegation = stg.make_delegation_event(delegation_id, suser_id, service_id)
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        explanation="ok",
        explanation_legible=True,
        explanation_contextual=False,
        report_to_suser=True,
    )
    events = [delegation, action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.NON_LEGIBLE_EXPLANATION)


# Spec: TM1.0-S015 | Property: P_ACCOUNTABILITY_CRITERIA
# Why: Accountability requires traceability, legible explanation, and challenge/correct/revoke mechanisms; unexplained outcomes fail.
def test_authority_chain_must_terminate_in_suser() -> None:
    """Test authority chain must terminate in suser.

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
        authority_chain_override=["service_alpha", "service_beta"],
        report_to_suser=True,
    )
    events = [delegation, action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, TRUST_VIOLATION.ACCOUNTABILITY_BREAK)


# Spec: TM1.0-S015, TM1.0-S022 | Property: P_ACCOUNTABILITY_CRITERIA, P_TRUST_DIAGNOSTIC_QUESTIONS
# Why: Accountability requires traceability, legible explanation, and challenge/correct/revoke mechanisms; unexplained outcomes fail.
# Why: Systems must answer origin, data influence, authoriser, inspector, and revoker; failure in legible terms is accountability failure.
def test_authority_graph_is_accountability_break() -> None:
    """Test authority graph is accountability break.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    suser_id = "suser_graph"
    service_id = "service_graph"
    delegation_id = "delegation_graph"
    decision_id = "decision_graph"
    delegation = stg.make_delegation_event(delegation_id, suser_id, service_id)
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        authority_chain_override=["delegation_graph", ["svc_a", "svc_b"]],
        report_to_suser=True,
    )
    events = [delegation, action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, TRUST_VIOLATION.ACCOUNTABILITY_BREAK)


# Spec: TM1.0-S044 | Property: P_ENFORCEMENT_LEGIBLE_ATTRIBUTABLE_CONTESTABLE
# Why: Enforcement must be legible, attributable, and contestable by affected S-Users.
def test_neutral_routing_is_no_attribution() -> None:
    """Test neutral routing is no attribution.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    enforcement = stg.make_enforcement_event(
        enforcement_id="enforce_neutral",
        enforcer_id=None,
        proportionate=True,
        transparent=True,
        contestable=True,
        reversible=True,
        punitive=False,
        attributable=True,
        contest_path="contest",
    )
    state, receipts = run_events([enforcement])
    report = trust_impl.evaluate_respect(state)
    attach_debug(report, [enforcement], receipts)
    assert_has_violation(report, ENFORCEMENT_VIOLATION.NO_ATTRIBUTION)
