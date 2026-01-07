"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/violations.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Defines violation enums, report structure, and assertion helpers.
 Invariants:
   Violation enums are stable identifiers; report mutations are explicit via methods.
 Trust Boundaries:
   In-memory data structures only; no external I/O.
 Security / Safety Notes:
   N/A.
 Dependencies:
   dataclasses, enum.
 Operational Scope:
   Shared by the reference model and tests for evaluation output.
 Revision History:
   2026-01-06 COD  Added SSE header for auditability.
   2026-01-06 COD  Added narrative comments for violation taxonomy and helpers.
   2026-01-06 COD  Added invariants and trust boundary notes.
------------------------------------------------------------
 SSE Principles Observed:
   - Explicit Result-based API (no silent failures)
   - Narrative comments for auditability
   - No hidden state changes; all mutations are explicit
   - Modular structure with clear boundaries
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


# Violation taxonomies are stable identifiers referenced by tests and reports.
class TRUST_VIOLATION(str, Enum):
    """Enumerates trust-layer violation codes."""
    SUSER_UNIDENTIFIED = "TRUST_VIOLATION.SUSER_UNIDENTIFIED"
    SOVEREIGNTY_ASSUMED = "TRUST_VIOLATION.SOVEREIGNTY_ASSUMED"
    AUTHORITY_UNTRACEABLE = "TRUST_VIOLATION.AUTHORITY_UNTRACEABLE"
    DELEGATION_INVALID = "TRUST_VIOLATION.DELEGATION_INVALID"
    SOVEREIGNTY_DISPLACED = "TRUST_VIOLATION.SOVEREIGNTY_DISPLACED"
    AUTONOMY_OVERREACH = "TRUST_VIOLATION.AUTONOMY_OVERREACH"
    ACCOUNTABILITY_BREAK = "TRUST_VIOLATION.ACCOUNTABILITY_BREAK"
    DIRECTIONALITY_BREACH = "TRUST_VIOLATION.DIRECTIONALITY_BREACH"
    ORDERING_INVERTED = "TRUST_VIOLATION.ORDERING_INVERTED"


class CONSENT_VIOLATION(str, Enum):
    """Enumerates consent-related violation codes."""
    IMPLICIT_DELEGATION = "CONSENT_VIOLATION.IMPLICIT_DELEGATION"
    INVALID_CONSENT = "CONSENT_VIOLATION.INVALID_CONSENT"
    COERCED_OR_OPAQUE = "CONSENT_VIOLATION.COERCED_OR_OPAQUE"


class TELEMETRY_VIOLATION(str, Enum):
    """Enumerates telemetry-related violation codes."""
    PRESCRIPTIVE_USE = "TELEMETRY_VIOLATION.PRESCRIPTIVE_USE"
    OPAQUE_INFLUENCE = "TELEMETRY_VIOLATION.OPAQUE_INFLUENCE"


class SERVICE_VIOLATION(str, Enum):
    """Enumerates service sovereignty violation codes."""
    SOVEREIGN_SUBSTITUTION = "SERVICE_VIOLATION.SOVEREIGN_SUBSTITUTION"


class ACCOUNTABILITY_VIOLATION(str, Enum):
    """Enumerates accountability and reporting violation codes."""
    ILLEGIBLE_REPORTING = "ACCOUNTABILITY_VIOLATION.ILLEGIBLE_REPORTING"
    NON_LEGIBLE_EXPLANATION = "ACCOUNTABILITY_VIOLATION.NON_LEGIBLE_EXPLANATION"
    NON_ACCOUNTABLE_OUTCOME = "ACCOUNTABILITY_VIOLATION.NON_ACCOUNTABLE_OUTCOME"
    MISSING_REPORTING = "ACCOUNTABILITY_VIOLATION.MISSING_REPORTING"
    DIAGNOSTIC_GAP = "ACCOUNTABILITY_VIOLATION.DIAGNOSTIC_GAP"
    NON_ACTIONABLE_DISCLOSURE = "ACCOUNTABILITY_VIOLATION.NON_ACTIONABLE_DISCLOSURE"
    LIMITS_UNDISCLOSED = "ACCOUNTABILITY_VIOLATION.LIMITS_UNDISCLOSED"


class STRUCTURAL_VIOLATION(str, Enum):
    """Enumerates structural or invalid-state violation codes."""
    INVALID_STATE = "STRUCTURAL_VIOLATION.INVALID_STATE"
    JUSTIFIED_INVALIDITY = "STRUCTURAL_VIOLATION.JUSTIFIED_INVALIDITY"


class RESPECT_VIOLATION(str, Enum):
    """Enumerates shared-environment respect violation codes."""
    UNILATERAL_IMPACT = "RESPECT_VIOLATION.UNILATERAL_IMPACT"
    BOUNDARY_IGNORED = "RESPECT_VIOLATION.BOUNDARY_IGNORED"
    CONTEXT_LEAK = "RESPECT_VIOLATION.CONTEXT_LEAK"
    NON_INTERFERENCE_BREACH = "RESPECT_VIOLATION.NON_INTERFERENCE_BREACH"
    MUTUAL_CONSENT_MISSING = "RESPECT_VIOLATION.MUTUAL_CONSENT_MISSING"
    UNILATERAL_CONSENT_BASIS = "RESPECT_VIOLATION.UNILATERAL_CONSENT_BASIS"
    COERCIVE_DEFAULT = "RESPECT_VIOLATION.COERCIVE_DEFAULT"
    PRINCIPLE_BREACH = "RESPECT_VIOLATION.PRINCIPLE_BREACH"
    IMPLICIT_BOUNDARIES = "RESPECT_VIOLATION.IMPLICIT_BOUNDARIES"
    OPAQUE_ENFORCEMENT = "RESPECT_VIOLATION.OPAQUE_ENFORCEMENT"
    DIAGNOSTIC_GAP = "RESPECT_VIOLATION.DIAGNOSTIC_GAP"


class GOVERNANCE_VIOLATION(str, Enum):
    """Enumerates governance and boundary violation codes."""
    INTERFACE_GAP = "GOVERNANCE_VIOLATION.INTERFACE_GAP"
    MISSING_ENTRY_CONDITIONS = "GOVERNANCE_VIOLATION.MISSING_ENTRY_CONDITIONS"
    REVOCATION_DEFECT = "GOVERNANCE_VIOLATION.REVOCATION_DEFECT"
    FEDERATED_GAP = "GOVERNANCE_VIOLATION.FEDERATED_GAP"
    FAILURE_MODE_IGNORED = "GOVERNANCE_VIOLATION.FAILURE_MODE_IGNORED"


class EVALUATION_VIOLATION(str, Enum):
    """Enumerates evaluation integrity violation codes."""
    UNDETERMINABLE_PASS = "EVALUATION_VIOLATION.UNDETERMINABLE_PASS"
    REDUCTIONISM = "EVALUATION_VIOLATION.REDUCTIONISM"


class AUDIT_VIOLATION(str, Enum):
    """Enumerates audit minimum violations."""
    TRUST_MINIMUM_MISSING = "AUDIT_VIOLATION.TRUST_MINIMUM_MISSING"
    RESPECT_MINIMUM_MISSING = "AUDIT_VIOLATION.RESPECT_MINIMUM_MISSING"


class ENFORCEMENT_VIOLATION(str, Enum):
    """Enumerates enforcement accountability violations."""
    SOVEREIGNTY_INCOMPATIBLE = "ENFORCEMENT_VIOLATION.SOVEREIGNTY_INCOMPATIBLE"
    NO_ATTRIBUTION = "ENFORCEMENT_VIOLATION.NO_ATTRIBUTION"


# Report structures capture violations and evidence in a predictable format.
@dataclass
class ViolationRecord:
    """Captures a single violation instance and supporting evidence."""
    label: str
    evidence_ids: List[str] = field(default_factory=list)
    details: str = ""


@dataclass
class Report:
    """Aggregates violations and debug evidence for an evaluation run."""
    kind: str
    violations: List[ViolationRecord] = field(default_factory=list)
    debug: Dict[str, Any] = field(default_factory=dict)
    score: Optional[float] = None

    def add_violation(
        self, label: str, evidence_ids: Optional[Iterable[str]] = None, details: str = ""
    ) -> None:
        """Append a violation record to the report.

        Args:
            label: Violation label or enum value.
            evidence_ids: Evidence identifiers supporting the violation.
            details: Optional human-readable details.

        Returns:
            None.

        Resources:
            None.

        Raises:
            None.
        """
        ids = list(evidence_ids) if evidence_ids else []
        self.violations.append(ViolationRecord(label=label, evidence_ids=ids, details=details))

    def labels(self) -> List[str]:
        """Return the list of violation labels in this report.

        Returns:
            List of violation label strings.

        Resources:
            None.

        Raises:
            None.
        """
        return [v.label for v in self.violations]

    def evidence_index(self) -> Dict[str, List[str]]:
        """Build an index of evidence ids by violation label.

        Returns:
            Mapping of violation label to evidence identifiers.

        Resources:
            None.

        Raises:
            None.
        """
        index: Dict[str, List[str]] = {}
        for violation in self.violations:
            index.setdefault(violation.label, []).extend(violation.evidence_ids)
        return index


def _label_value(label: Any) -> str:
    """Normalize a label or enum into a string value.

    Args:
        label: Enum or string label.

    Returns:
        String label value.

    Resources:
        None.

    Raises:
        None.
    """
    if isinstance(label, Enum):
        return label.value
    return str(label)


# Debug attachment is explicit so tests can audit the evidence trail.
def attach_debug(report: Report, events: List[Dict[str, Any]], receipts: List[Dict[str, Any]]) -> None:
    """Attach debug event/receipt context to a report.

    Args:
        report: Report instance to annotate.
        events: Event list captured during evaluation.
        receipts: Receipt list captured during evaluation.

    Returns:
        None.

    Resources:
        None.

    Raises:
        None.
    """
    report.debug = {"events": events, "receipts": receipts}


def _format_debug(report: Report) -> str:
    """Format report debug data for assertion messages.

    Args:
        report: Report instance with debug context.

    Returns:
        Human-readable debug string.

    Resources:
        None.

    Raises:
        None.
    """
    debug = report.debug or {}
    events = debug.get("events", [])
    receipts = debug.get("receipts", [])
    lines = ["debug:"]
    lines.append(f"  events={events}")
    lines.append(f"  receipts={receipts}")
    if report.violations:
        lines.append("  evidence_ids=")
        for violation in report.violations:
            lines.append(f"    {violation.label}: {violation.evidence_ids}")
    return "\n".join(lines)


def assert_no_violation(report: Report, label: Any) -> None:
    """Assert that a violation is absent from the report.

    Args:
        report: Report instance to inspect.
        label: Violation label or enum value to check.

    Returns:
        None.

    Resources:
        None.

    Raises:
        AssertionError: If the violation is present.
    """
    value = _label_value(label)
    if value in report.labels():
        message = f"Unexpected violation: {value}\n{_format_debug(report)}"
        raise AssertionError(message)


def assert_has_violation(report: Report, label: Any) -> None:
    """Assert that a violation is present in the report.

    Args:
        report: Report instance to inspect.
        label: Violation label or enum value to check.

    Returns:
        None.

    Resources:
        None.

    Raises:
        AssertionError: If the violation is missing.
    """
    value = _label_value(label)
    if value not in report.labels():
        message = f"Missing expected violation: {value}\n{_format_debug(report)}"
        raise AssertionError(message)
