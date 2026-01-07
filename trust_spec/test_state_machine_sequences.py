"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/test_state_machine_sequences.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   State-machine tests over mixed event sequences for trust and respect behavior.
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

from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from trust_spec import strategies as stg
import trust_impl
from trust_spec.violations import (
    ACCOUNTABILITY_VIOLATION,
    CONSENT_VIOLATION,
    ENFORCEMENT_VIOLATION,
    RESPECT_VIOLATION,
    TELEMETRY_VIOLATION,
    TRUST_VIOLATION,
    attach_debug,
    assert_has_violation,
)


# Spec: TM1.0-S003, TM1.0-S007, TM1.0-S019, TM1.0-S023, TM1.0-S025, TM1.0-S027, TM1.0-S032, TM1.0-S044 | Property: P_AUTHORITY_TRACEABLE, P_AUTOMATION_WITHIN_DELEGATION, P_DIRECTIONAL_ACCOUNTABILITY_REQUIREMENTS, P_SHARED_ENV_NO_UNILATERAL_IMPACT, P_AUTHORITY_CONTAINMENT, P_MULTIUSER_CONSENT, P_NON_COERCIVE_DEFAULTS, P_ENFORCEMENT_LEGIBLE_ATTRIBUTABLE_CONTESTABLE
# Why: This state machine bundles trust + respect properties to expose cross-property failures that only show up in long, mixed event sequences (authority traceability, delegation limits, shared-environment consent, defaults, enforcement legibility).
class TrustRespectStateMachine(RuleBasedStateMachine):
    """Purpose:
        Stateful harness for mixed trust/respect event sequences.

    Inputs/Outputs:
        Inputs: Event dictionaries applied via Hypothesis rules.
        Outputs: Expected violation sets and in-memory receipts.

    Error Behavior:
        Invariants may raise AssertionError on violations.

    Resources:
        In-memory state owned by the machine.

    Ownership:
        Owned by the Hypothesis runner for the test session.
    """
    def __init__(self) -> None:
        """Init.

        Args:
            None.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        super().__init__()
        self.state = trust_impl.State()
        self.events = []
        self.receipts = []
        self.expected_trust = set()
        self.expected_respect = set()

    def _apply(self, event: dict[str, object]) -> None:
        """Apply.

        Args:
            event: Test input value.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        self.state, new_receipts = trust_impl.apply_event(self.state, event)
        self.events.append(event)
        self.receipts.extend(new_receipts)
        self._expect(event)

    def _expect(self, event: dict[str, object]) -> None:
        """Expect.

        Args:
            event: Test input value.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        event_type = event.get("type")
        if event_type == "delegation":
            if not event.get("explicit") or not event.get("scoped") or not event.get("revocable"):
                self.expected_trust.add(TRUST_VIOLATION.DELEGATION_INVALID)
            if event.get("derived_from_use"):
                self.expected_trust.add(CONSENT_VIOLATION.IMPLICIT_DELEGATION)
            if not event.get("suser_can_revoke"):
                self.expected_trust.add(TRUST_VIOLATION.SOVEREIGNTY_DISPLACED)
        if event_type == "telemetry":
            if event.get("prescriptive_use"):
                self.expected_trust.add(TELEMETRY_VIOLATION.PRESCRIPTIVE_USE)
            if event.get("influences") and not event.get("explained"):
                self.expected_trust.add(TELEMETRY_VIOLATION.OPAQUE_INFLUENCE)
            if event.get("reports_to_service") is False:
                self.expected_trust.add(ACCOUNTABILITY_VIOLATION.MISSING_REPORTING)
        if event_type == "service_action":
            if not event.get("suser_id"):
                self.expected_trust.add(TRUST_VIOLATION.SUSER_UNIDENTIFIED)
            if not event.get("delegation_id"):
                self.expected_trust.add(TRUST_VIOLATION.AUTHORITY_UNTRACEABLE)
            if event.get("automated") and not event.get("within_scope"):
                self.expected_trust.add(TRUST_VIOLATION.AUTONOMY_OVERREACH)
            if event.get("report_to_suser") is False:
                self.expected_trust.add(ACCOUNTABILITY_VIOLATION.MISSING_REPORTING)
            if event.get("explanation_contextual") is False:
                self.expected_trust.add(ACCOUNTABILITY_VIOLATION.NON_LEGIBLE_EXPLANATION)
            chain_override = event.get("authority_chain_override")
            if chain_override is not None:
                if not isinstance(chain_override, list):
                    self.expected_trust.add(TRUST_VIOLATION.ACCOUNTABILITY_BREAK)
                else:
                    contains_branch = any(
                        isinstance(item, (list, dict)) for item in chain_override
                    )
                    terminates = bool(chain_override) and chain_override[-1] == event.get(
                        "suser_id"
                    )
                    if contains_branch or not terminates:
                        self.expected_trust.add(TRUST_VIOLATION.ACCOUNTABILITY_BREAK)
            if event.get("lower_layer_authority_accumulation"):
                self.expected_trust.add(TRUST_VIOLATION.DIRECTIONALITY_BREACH)
        if event_type == "shared_action":
            actor = event.get("actor_suser_id")
            affected = event.get("affected_susers", [])
            affects_others = any(suser != actor for suser in affected)
            if affects_others and event.get("consent_basis") not in {"mutual", "federated"}:
                self.expected_respect.add(RESPECT_VIOLATION.MUTUAL_CONSENT_MISSING)
            if event.get("cross_context") and not event.get("renewed_consent"):
                self.expected_respect.add(RESPECT_VIOLATION.CONTEXT_LEAK)
        if event_type == "default_setting":
            if (
                event.get("exploits_bias")
                or event.get("expands_scope")
                or event.get("privileges_platform")
                or not event.get("justifiable")
                or not event.get("reversible")
            ):
                self.expected_respect.add(RESPECT_VIOLATION.COERCIVE_DEFAULT)
        if event_type == "enforcement":
            if not event.get("attributable") or not event.get("enforcer_id"):
                self.expected_trust.add(ENFORCEMENT_VIOLATION.NO_ATTRIBUTION)

    @rule(event=stg.hostile_delegation_events())
    def add_delegation(self, event: dict[str, object]) -> None:
        """Add delegation.

        Args:
            event: Test input value.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        self._apply(event)

    @rule(event=stg.hostile_consent_events())
    def add_consent(self, event: dict[str, object]) -> None:
        """Add consent.

        Args:
            event: Test input value.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        self._apply(event)

    @rule(event=stg.hostile_telemetry_events())
    def add_telemetry(self, event: dict[str, object]) -> None:
        """Add telemetry.

        Args:
            event: Test input value.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        self._apply(event)

    @rule(event=stg.hostile_service_action_events())
    def add_service_action(self, event: dict[str, object]) -> None:
        """Add service action.

        Args:
            event: Test input value.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        self._apply(event)

    @rule(event=stg.hostile_shared_action_events())
    def add_shared_action(self, event: dict[str, object]) -> None:
        """Add shared action.

        Args:
            event: Test input value.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        self._apply(event)

    @rule(event=stg.hostile_default_events())
    def add_default(self, event: dict[str, object]) -> None:
        """Add default.

        Args:
            event: Test input value.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        self._apply(event)

    @rule(event=stg.hostile_enforcement_events())
    def add_enforcement(self, event: dict[str, object]) -> None:
        """Add enforcement.

        Args:
            event: Test input value.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        self._apply(event)

    @invariant()
    def expected_violations_present(self) -> None:
        """Expected violations present.

        Args:
            None.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            AssertionError: When a trust or respect property is violated.
        """
        trust_report = trust_impl.evaluate_trust(self.state)
        attach_debug(trust_report, self.events, self.receipts)
        for label in self.expected_trust:
            assert_has_violation(trust_report, label)

        respect_report = trust_impl.evaluate_respect(self.state)
        attach_debug(respect_report, self.events, self.receipts)
        for label in self.expected_respect:
            assert_has_violation(respect_report, label)


TestTrustRespectStateMachine = TrustRespectStateMachine.TestCase
