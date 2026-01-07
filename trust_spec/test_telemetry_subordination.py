"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/test_telemetry_subordination.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Tests telemetry subordination and reporting/ordering rules.
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
   2026-01-06 COD  Added SSE header for auditability; Added invariants and trust boundary notes; Added narrative spec comments for readability; Added pressure-point tests for aggregate and feedback telemetry; Added exemplar capture hooks for selected failures.
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
    ACCOUNTABILITY_VIOLATION,
    TELEMETRY_VIOLATION,
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


# Spec: TM1.0-S008 | Property: P_TELEMETRY_NON_PRESCRIPTIVE
# Why: Telemetry is descriptive only and must not define policy, enforce, trigger irreversible outcomes, or accumulate authority.
@given(telemetry_id=stg.telemetry_ids())
def test_telemetry_not_prescriptive(telemetry_id: str) -> None:
    """Test telemetry not prescriptive.

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
        prescriptive_use=True,
    )
    state, receipts = run_events([telemetry])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [telemetry], receipts)
    assert_has_violation(report, TELEMETRY_VIOLATION.PRESCRIPTIVE_USE)


# Spec: TM1.0-S009 | Property: P_TELEMETRY_INFLUENCE_EXPLAINED
# Why: Telemetry influence must be visible and explainable; human-inexplicable telemetry-driven decisions are invalid.
@given(telemetry_id=stg.telemetry_ids())
def test_telemetry_influence_explained(telemetry_id: str) -> None:
    """Test telemetry influence explained.

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
    )
    state, receipts = run_events([telemetry])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [telemetry], receipts)
    assert_has_violation(report, TELEMETRY_VIOLATION.OPAQUE_INFLUENCE)


# Spec: TM1.0-S009 | Property: P_TELEMETRY_INFLUENCE_EXPLAINED
# Why: Multi-signal decisions require explicit attribution; influence cannot hide inside an unnamed aggregate.
@given(
    suser_id=stg.suser_ids(),
    service_id=stg.service_ids(),
    decision_id=stg.decision_ids(),
    telemetry_ids=st.lists(stg.telemetry_ids(), min_size=2, max_size=2, unique=True),
)
def test_multi_signal_decision_requires_attribution(
    suser_id: str,
    service_id: str,
    decision_id: str,
    telemetry_ids: list[str],
) -> None:
    """Test multi-signal decision requires attribution.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        decision_id: Test input value.
        telemetry_ids: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    telemetry_events = [
        stg.make_telemetry_event(
            telemetry_id,
            influences=True,
            explained=True,
            human_explainable=True,
            reports_to_service=True,
        )
        for telemetry_id in telemetry_ids
    ]
    delegation_id = "delegation_multi_signal"
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        telemetry_refs=telemetry_ids,
        telemetry_attribution_complete=False,
    )
    events = telemetry_events + [stg.make_delegation_event(delegation_id, suser_id, service_id), action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    exemplars.capture_on_failure(
        exemplar_id="TM1.0-EX-TEL-MULTI-ATTRIB-001",
        kind="trust",
        events=events,
        receipts=receipts,
        report=report,
        assertion=lambda: assert_has_violation(report, TELEMETRY_VIOLATION.OPAQUE_INFLUENCE),
        source=exemplars.source_metadata(
            test_name="test_multi_signal_decision_requires_attribution"
        ),
        notes="Multi-signal decision missing explicit telemetry attribution.",
        spec_map=["TM1.0-S009"],
    )


# Spec: TM1.0-S009 | Property: P_TELEMETRY_INFLUENCE_EXPLAINED
# Why: Aggregate scalars must list their inputs; hiding sources is opaque influence.
@given(
    suser_id=stg.suser_ids(),
    service_id=stg.service_ids(),
    decision_id=stg.decision_ids(),
    aggregate_id=stg.telemetry_ids(),
    telemetry_sources=st.lists(stg.telemetry_ids(), min_size=2, max_size=2, unique=True),
)
def test_aggregate_scalar_laundering_is_opaque_influence(
    suser_id: str,
    service_id: str,
    decision_id: str,
    aggregate_id: str,
    telemetry_sources: list[str],
) -> None:
    """Test aggregate scalar laundering is opaque influence.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        decision_id: Test input value.
        aggregate_id: Test input value.
        telemetry_sources: Test input value.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    telemetry_events = [
        stg.make_telemetry_event(
            telemetry_id,
            influences=True,
            explained=True,
            human_explainable=True,
            reports_to_service=True,
        )
        for telemetry_id in telemetry_sources
    ]
    telemetry_events.append(
        stg.make_telemetry_event(
            aggregate_id,
            influences=True,
            explained=True,
            human_explainable=True,
            reports_to_service=True,
        )
    )
    delegation_id = "delegation_aggregate"
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        telemetry_refs=[aggregate_id],
        telemetry_aggregate=True,
        telemetry_aggregate_sources=[],
    )
    events = telemetry_events + [stg.make_delegation_event(delegation_id, suser_id, service_id), action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    exemplars.capture_on_failure(
        exemplar_id="TM1.0-EX-TEL-AGG-001",
        kind="trust",
        events=events,
        receipts=receipts,
        report=report,
        assertion=lambda: assert_has_violation(report, TELEMETRY_VIOLATION.OPAQUE_INFLUENCE),
        source=exemplars.source_metadata(
            test_name="test_aggregate_scalar_laundering_is_opaque_influence"
        ),
        notes="Aggregate telemetry scalar without source attribution.",
        spec_map=["TM1.0-S009"],
    )


# Spec: TM1.0-S008, TM1.0-S009 | Property: P_TELEMETRY_NON_PRESCRIPTIVE, P_TELEMETRY_INFLUENCE_EXPLAINED
# Why: Self-originating telemetry forms a feedback loop and must be explicitly contained before it can justify action.
@given(
    suser_id=stg.suser_ids(),
    service_id=stg.service_ids(),
    decision_id=stg.decision_ids(),
    telemetry_id=stg.telemetry_ids(),
)
def test_self_originating_telemetry_requires_containment(
    suser_id: str,
    service_id: str,
    decision_id: str,
    telemetry_id: str,
) -> None:
    """Test self-originating telemetry requires containment.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        decision_id: Test input value.
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
        explained=True,
        human_explainable=True,
        reports_to_service=True,
        self_originating=True,
    )
    delegation_id = "delegation_feedback"
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        telemetry_refs=[telemetry_id],
        self_telemetry_contained=False,
    )
    events = [telemetry, stg.make_delegation_event(delegation_id, suser_id, service_id), action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    exemplars.capture_on_failure(
        exemplar_id="TM1.0-EX-FEEDBACK-SELFTELEM-001",
        kind="trust",
        events=events,
        receipts=receipts,
        report=report,
        assertion=lambda: assert_has_violation(report, TELEMETRY_VIOLATION.OPAQUE_INFLUENCE),
        source=exemplars.source_metadata(
            test_name="test_self_originating_telemetry_requires_containment"
        ),
        notes="Self-originating telemetry used without explicit containment.",
        spec_map=["TM1.0-S008", "TM1.0-S009"],
    )


# Spec: TM1.0-S020, TM1.0-S021 | Property: P_TRUST_ORDERING, P_REPORTING_OBLIGATIONS_UPWARD
# Why: TRUST ordering is Users > Services > Telemetry; inversions are structural violations.
# Why: Reporting flows upward with legibility; telemetry reports to services, services to users; constraints on reporting must be reported.
@given(
    suser_id=stg.suser_ids(),
    service_id=stg.service_ids(),
    decision_id=stg.decision_ids(),
    telemetry_id=stg.telemetry_ids(),
)
def test_telemetry_reports_to_service_and_ordering(suser_id: str, service_id: str, decision_id: str, telemetry_id: str) -> None:
    """Test telemetry reports to service and ordering.

    Args:
        suser_id: Test input value.
        service_id: Test input value.
        decision_id: Test input value.
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
        reports_to_service=False,
    )
    delegation_id = "delegation_tel"
    action = stg.make_service_action_event(
        decision_id=decision_id,
        suser_id=suser_id,
        service_id=service_id,
        delegation_id=delegation_id,
        ordering_inverted=True,
        telemetry_refs=[telemetry_id],
    )
    events = [telemetry, stg.make_delegation_event(delegation_id, suser_id, service_id), action]
    state, receipts = run_events(events)
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, events, receipts)
    assert_has_violation(report, ACCOUNTABILITY_VIOLATION.MISSING_REPORTING)
    assert_has_violation(report, TRUST_VIOLATION.ORDERING_INVERTED)


# Spec: TM1.0-S021 | Property: P_REPORTING_OBLIGATIONS_UPWARD
# Why: Reporting flows upward with legibility; telemetry reports to services, services to users; constraints on reporting must be reported.
@given(telemetry_id=stg.telemetry_ids())
def test_telemetry_reporting_obligation_satisfied(telemetry_id: str) -> None:
    """Test telemetry reporting obligation satisfied.

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
        reports_to_service=True,
    )
    state, receipts = run_events([telemetry])
    report = trust_impl.evaluate_trust(state)
    attach_debug(report, [telemetry], receipts)
    assert_no_violation(report, ACCOUNTABILITY_VIOLATION.MISSING_REPORTING)
