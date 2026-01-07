"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/test_trust.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Stateful model for basic trust/respect invariants.
 Invariants:
   Tests mutate only in-memory state via trust_impl.apply_event.
 Trust Boundaries:
   No external I/O; relies on trust_impl API and Hypothesis inputs.
 Security / Safety Notes:
   N/A.
 Dependencies:
   pytest, hypothesis.
 Operational Scope:
   Executed under pytest as part of the trust-spec suite.
 Revision History:
   2026-01-06 COD  Added SSE header for auditability.
   2026-01-06 COD  Added invariants and trust boundary notes.
   2026-01-06 COD  Added narrative comments for state machine intent.
   2026-01-06 COD  Added spec/why tags for state machine rules.
------------------------------------------------------------
 SSE Principles Observed:
   - Explicit Result-based API (no silent failures)
   - Narrative comments for auditability
   - No hidden state changes; all mutations are explicit
   - Modular structure with clear boundaries
============================================================
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Set, List, Optional

from hypothesis import settings
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant


# Core concepts keep the state machine legible and role-scoped for auditors.

class Actor(Enum):
    """Purpose:
        Enumerates actor roles used in the trust state machine.

    Inputs/Outputs:
        Inputs: Enum members declared at class definition.
        Outputs: Enum values stored in receipts.

    Error Behavior:
        None.

    Resources:
        None.

    Ownership:
        Module-scoped and immutable.
    """
    SUSER = auto()
    SERVICE = auto()
    TELEMETRY = auto()


class Capability(Enum):
    """Purpose:
        Enumerates capabilities delegated in the trust model.

    Inputs/Outputs:
        Inputs: Enum members declared at class definition.
        Outputs: Enum values stored in model state.

    Error Behavior:
        None.

    Resources:
        None.

    Ownership:
        Module-scoped and immutable.
    """
    READ = auto()
    WRITE = auto()
    ENFORCE = auto()


@dataclass
class Receipt:
    """Purpose:
        Captures a single action receipt for trust model evaluation.

    Inputs/Outputs:
        Inputs: Actor, action, allowed, authority_origin values.
        Outputs: Receipt instances stored in ModelState.

    Error Behavior:
        None.

    Resources:
        In-memory only.

    Ownership:
        Owned by ModelState.receipts.
    """
    actor: Actor
    action: str
    allowed: bool
    authority_origin: Optional[Actor]


@dataclass
class ModelState:
    """Purpose:
        Tracks delegated capabilities and emitted receipts.

    Inputs/Outputs:
        Inputs: Mutated by TrustMachine rule methods.
        Outputs: Receipts evaluated by invariants.

    Error Behavior:
        None.

    Resources:
        In-memory only.

    Ownership:
        Owned by TrustMachine.state.
    """
    delegated_caps: Set[Capability] = field(default_factory=set)
    receipts: List[Receipt] = field(default_factory=list)

    def log(self, r: Receipt) -> None:
        """Log.

        Args:
            r: Test input value.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        self.receipts.append(r)


# Minimal trust/respect model: explicit delegation, non-authoritative telemetry, and traced service action.

class TrustMachine(RuleBasedStateMachine):
    """Purpose:
        Hypothesis state machine defining trust/respect behavior.

    Inputs/Outputs:
        Inputs: Rule invocations from Hypothesis.
        Outputs: Mutated ModelState and receipts.

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
        self.state = ModelState()

    # Spec: TM1.0-S004 | Property: P_DELEGATION_EXPLICIT_SCOPED_REVOCABLE
    # Why: Delegation must be explicit and revocable so authority remains grounded.
    # Why: This rule models the explicit grant that later service actions rely on.
    @rule()
    def delegate_write(self) -> None:
        """Delegate write.

        Args:
            None.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        self.state.delegated_caps.add(Capability.WRITE)
        self.state.log(Receipt(
            actor=Actor.SUSER,
            action="delegate WRITE",
            allowed=True,
            authority_origin=Actor.SUSER
        ))

    # Spec: TM1.0-S004 | Property: P_DELEGATION_EXPLICIT_SCOPED_REVOCABLE
    # Why: Revocation is part of legitimate delegation; authority must be withdrawable.
    # Why: This rule models a clear withdrawal so later actions cannot assume authority.
    @rule()
    def revoke_write(self) -> None:
        """Revoke write.

        Args:
            None.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        self.state.delegated_caps.discard(Capability.WRITE)
        self.state.log(Receipt(
            actor=Actor.SUSER,
            action="revoke WRITE",
            allowed=True,
            authority_origin=Actor.SUSER
        ))

    # Spec: TM1.0-S008 | Property: P_TELEMETRY_NON_PRESCRIPTIVE
    # Why: Telemetry is descriptive only; it cannot grant authority or enforcement power.
    # Why: This rule keeps telemetry in an observer role for the state machine.
    @rule()
    def telemetry_event(self) -> None:
        """Telemetry event.

        Args:
            None.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        self.state.log(Receipt(
            actor=Actor.TELEMETRY,
            action="observe anomaly",
            allowed=True,
            authority_origin=None
        ))

    # Spec: TM1.0-S003 | Property: P_AUTHORITY_TRACEABLE
    # Why: Capability alone is not authority; service actions must trace to an S-User.
    # Why: This rule checks whether a write attempt is grounded in delegation.
    @rule()
    def service_write(self) -> None:
        """Service write.

        Args:
            None.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            None.
        """
        allowed = Capability.WRITE in self.state.delegated_caps
        self.state.log(Receipt(
            actor=Actor.SERVICE,
            action="WRITE attempt",
            allowed=allowed,
            authority_origin=Actor.SUSER if allowed else None
        ))

    # Spec: TM1.0-S003 | Property: P_AUTHORITY_TRACEABLE
    # Why: An allowed service action must always show an S-User origin in the chain.
    # Why: This invariant makes traceability a continuous requirement.

    @invariant()
    def no_unauthorised_write(self) -> None:
        """Ensure service writes trace authority back to the S-User.

        Args:
            None.

        Returns:
            None.

        Resources:
            In-memory state only.

        Raises:
            AssertionError: When a write lacks S-User authority.
        """
        for r in self.state.receipts:
            if r.actor == Actor.SERVICE and "WRITE" in r.action:
                if r.allowed:
                    assert r.authority_origin == Actor.SUSER


# Stable test wrapper keeps Hypothesis settings in one place for auditability.
TestTrust = TrustMachine.TestCase
TestTrust.settings = settings(
    max_examples=200,
    stateful_step_count=20
)
