"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/test_assumptions.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Tests assumption compliance for explanations, revocation, consent, and receipts.
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

from trust_spec import assumptions as asm
from trust_spec import strategies as stg
import trust_impl


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


# Spec: TM1.0-S013, TM1.0-S014 | Property: P_TRANSPARENCY_NEEDS_LEGIBILITY, P_EXPLANATIONS_LEGIBLE (Assumption A001)
# Why: Transparency without legibility fails accountability; raw logs alone are insufficient.
# Why: Explanations must be accessible, contextual, and relevant to decisions affecting the S-User.

def test_assumption_legible_explanation_includes_context() -> None:
    """Test assumption legible explanation includes context.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    suser_id = "suser_a"
    service_id = "service_a"
    decision_id = "decision_a"
    context_id = "ctx_a"
    delegation_id = "delegation_a"
    explanation = f"decision={decision_id} context={context_id}"
    events = [
        stg.make_delegation_event(delegation_id, suser_id, service_id),
        stg.make_service_action_event(
            decision_id=decision_id,
            suser_id=suser_id,
            service_id=service_id,
            delegation_id=delegation_id,
            context_id=context_id,
            explanation=explanation,
        ),
    ]
    state, _ = run_events(events)
    response = trust_impl.query_decision(state, decision_id)
    if context_id not in (response.get("explanation") or ""):
        raise AssertionError(asm.ASSUMPTION_A001)


# Spec: TM1.0-S004, TM1.0-S011 | Property: P_DELEGATION_EXPLICIT_SCOPED_REVOCABLE, P_CONSENT_VALID_CRITERIA (Assumption A002)
# Why: Legitimate delegation is explicit, scoped, and revocable in principle.
# Why: Valid consent is informed, specific, and revocable with meaningful effect; constraints must be disclosed.

def test_assumption_revocation_path_and_receipt_present() -> None:
    """Test assumption revocation path and receipt present.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    delegation_id = "delegation_revocation"
    suser_id = "suser_a"
    service_id = "service_a"
    delegation = stg.make_delegation_event(
        delegation_id,
        suser_id,
        service_id,
        revocation_path="revoke",
    )
    revoke = stg.make_revoke_delegation_event(delegation_id)
    _, receipts = run_events([delegation, revoke])
    if not any(r.get("type") == "delegation_revocation_receipt" for r in receipts):
        raise AssertionError(asm.ASSUMPTION_A002)


# Spec: TM1.0-S011, TM1.0-S012 | Property: P_CONSENT_VALID_CRITERIA, P_CONSENT_INVALID_FORMS (Assumption A003)
# Why: Valid consent is informed, specific, and revocable with meaningful effect; constraints must be disclosed.
# Why: Bundled/coerced consent, dark patterns, continued-use assumptions, or non-withdrawable consent are invalid.

def test_assumption_withdrawal_blocks_future_use() -> None:
    """Test assumption withdrawal blocks future use.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    consent_id = "consent_a"
    suser_id = "suser_a"
    service_id = "service_a"
    decision_id = "decision_a"
    delegation_id = "delegation_a"
    events = [
        stg.make_consent_event(consent_id, suser_id),
        stg.make_withdraw_consent_event(consent_id),
        stg.make_delegation_event(delegation_id, suser_id, service_id),
        stg.make_service_action_event(
            decision_id=decision_id,
            suser_id=suser_id,
            service_id=service_id,
            delegation_id=delegation_id,
            consent_id=consent_id,
        ),
    ]
    state, _ = run_events(events)
    report = trust_impl.evaluate_trust(state)
    if "CONSENT_VIOLATION.INVALID_CONSENT" not in report.labels():
        raise AssertionError(asm.ASSUMPTION_A003)


# Spec: TM1.0-S023, TM1.0-S027 | Property: P_SHARED_ENV_NO_UNILATERAL_IMPACT, P_MULTIUSER_CONSENT (Assumption A004)
# Why: One S-User's delegation may not affect another without legible, contestable consent or governance basis.
# Why: Multi-user actions require mutual/federated consent; implicit consent is insufficient; impact must be legible; scope constrained if consent cannot be obtained.

def test_assumption_shared_actions_list_affected_susers() -> None:
    """Test assumption shared actions list affected susers.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    action = stg.make_shared_action_event(
        environment_id="env_a",
        actor_suser_id="suser_a",
        affected_susers=["suser_a", "suser_b"],
    )
    _, receipts = run_events([action])
    receipt = next((r for r in receipts if r.get("type") == "shared_action_receipt"), {})
    if not receipt.get("affected_susers"):
        raise AssertionError(asm.ASSUMPTION_A004)


# Spec: TM1.0-S003, TM1.0-S018 | Property: P_AUTHORITY_TRACEABLE, P_ACCOUNTABILITY_FLOW_TO_SUSER (Assumption A005)
# Why: Authority must trace to the S-User; capability alone is not authority and is invalid without it.
# Why: Where authority exists, accountability must flow back to the consequence-bearing entity.

def test_assumption_authority_chain_in_receipt() -> None:
    """Test assumption authority chain in receipt.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    suser_id = "suser_a"
    service_id = "service_a"
    decision_id = "decision_a"
    delegation_id = "delegation_a"
    events = [
        stg.make_delegation_event(delegation_id, suser_id, service_id),
        stg.make_service_action_event(
            decision_id=decision_id,
            suser_id=suser_id,
            service_id=service_id,
            delegation_id=delegation_id,
        ),
    ]
    _, receipts = run_events(events)
    receipt = next((r for r in receipts if r.get("type") == "decision_receipt"), {})
    if not receipt.get("authority_chain"):
        raise AssertionError(asm.ASSUMPTION_A005)


# Spec: TM1.0-S036 | Property: P_RESPECT_EXPLICIT_BOUNDARIES (Assumption A006)
# Why: RESPECT requires explicit boundaries (no centralised control required).

def test_assumption_boundaries_are_explicit_objects() -> None:
    """Test assumption boundaries are explicit objects.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When a trust or respect property is violated.
    """
    boundary = stg.make_boundary_declaration_event("env_a", explicit=True)
    _, receipts = run_events([boundary])
    receipt = next((r for r in receipts if r.get("type") == "boundary_receipt"), {})
    if not receipt.get("scope") or not receipt.get("constraints"):
        raise AssertionError(asm.ASSUMPTION_A006)


# Spec: TM1.0-S043, TM1.0-S044 | Property: P_SOVEREIGNTY_COMPATIBLE_ENFORCEMENT, P_ENFORCEMENT_LEGIBLE_ATTRIBUTABLE_CONTESTABLE (Assumption A007)
# Why: Enforcement must not undermine sovereignty; it is proportionate, transparent, contestable, reversible where feasible; punitive/opaque enforcement is incompatible.
# Why: Enforcement must be legible, attributable, and contestable by affected S-Users.

def test_assumption_contestability_receipt_present() -> None:
    """Test assumption contestability receipt present.

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
        enforcement_id="enforce_a",
        enforcer_id="service_a",
        contest_path="contest",
    )
    _, receipts = run_events([enforcement])
    receipt = next((r for r in receipts if r.get("type") == "enforcement_receipt"), {})
    if not receipt.get("contest_path"):
        raise AssertionError(asm.ASSUMPTION_A007)
