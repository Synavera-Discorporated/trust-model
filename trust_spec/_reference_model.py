"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/_reference_model.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Reference implementation of trust/respect state transitions, receipts, and evaluations.
 Invariants:
   Event and receipt logs are append-only; state updates are explicit.
 Trust Boundaries:
   Accepts event dictionaries as inputs; no external I/O or network access.
 Security / Safety Notes:
   Maintains in-memory consent and authority records; logs are timestamped and hash-chained.
 Dependencies:
   dataclasses, hashlib, json, trust_spec.violations.
 Operational Scope:
   Used by tests and stubs to model expected behavior.
 Revision History:
   2026-01-06 COD  Added SSE header and audit-log metadata; Added invariants and trust boundary notes; Default base time set for deterministic receipts; Added pressure-point checks for telemetry and drift authority; Preserve decision-time zero to catch posthoc authority gaps; Guard against posthoc authority in decision receipts; Added evaluator safety net for malformed inputs; Added narrative comments for evaluation and receipt logic.
------------------------------------------------------------
 SSE Principles Observed:
   - Explicit Result-based API (no silent failures)
   - Narrative comments for auditability
   - No hidden state changes; all mutations are explicit
   - Modular structure with clear boundaries
============================================================
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from trust_spec.violations import (
    ACCOUNTABILITY_VIOLATION,
    AUDIT_VIOLATION,
    CONSENT_VIOLATION,
    ENFORCEMENT_VIOLATION,
    EVALUATION_VIOLATION,
    GOVERNANCE_VIOLATION,
    RESPECT_VIOLATION,
    SERVICE_VIOLATION,
    STRUCTURAL_VIOLATION,
    TELEMETRY_VIOLATION,
    TRUST_VIOLATION,
    Report,
)

_KNOWN_EVENT_TYPES = {
    "delegation",
    "revoke_delegation",
    "consent",
    "withdraw_consent",
    "telemetry",
    "service_action",
    "shared_action",
    "time_advance",
    "boundary_declaration",
    "entry_condition",
    "entry_request",
    "boundary_rule",
    "revocation_policy",
    "default_setting",
    "federated_governance",
    "boundary_failure_modes",
    "respect_principles",
    "participation_declaration",
    "trust_audit",
    "respect_audit",
    "enforcement",
    "disclosure",
    "limitation_disclosure",
    "reductionist_metric",
}

# Deterministic base time makes receipts stable across runs for audit replay.
_DEFAULT_BASE_TIME_UTC = "2026-01-01T00:00:00Z"


def _default_base_time_utc() -> str:
    """Return the deterministic base UTC time for receipts.

    Returns:
        RFC-3339 UTC timestamp string.

    Resources:
        None.

    Raises:
        None.
    """
    return _DEFAULT_BASE_TIME_UTC


def _parse_rfc3339(value: str) -> datetime:
    """Parse an RFC-3339 timestamp string into a timezone-aware datetime.

    Args:
        value: RFC-3339 UTC timestamp string.

    Returns:
        Parsed timezone-aware datetime in UTC.

    Resources:
        None.

    Raises:
        ValueError: If the input is not a valid RFC-3339 timestamp.
    """
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    return datetime.fromisoformat(value)


def _event_time_utc(base_time_utc: str, event_time: int) -> str:
    """Translate a logical clock tick into an RFC-3339 UTC timestamp.

    Args:
        base_time_utc: Base RFC-3339 UTC time for clock zero.
        event_time: Logical clock value in seconds since base.

    Returns:
        RFC-3339 UTC timestamp for the event.

    Resources:
        None.

    Raises:
        ValueError: If the base timestamp is malformed.
    """
    base = _parse_rfc3339(base_time_utc)
    timestamp = base + timedelta(seconds=event_time)
    return timestamp.isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical_json(data: Dict[str, Any]) -> str:
    """Serialize data to a canonical JSON string for hashing.

    Args:
        data: Dictionary payload to serialize.

    Returns:
        Canonical JSON string with stable key ordering.

    Resources:
        None.

    Raises:
        TypeError: If data contains non-serializable values.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash_chain(payload: Dict[str, Any], prev_hash: Optional[str]) -> str:
    """Compute a SHA-256 hash for a payload chained to a previous hash.

    Args:
        payload: Payload to hash.
        prev_hash: Previous hash in the chain, if any.

    Returns:
        Hex-encoded SHA-256 hash.

    Resources:
        None.

    Raises:
        TypeError: If the payload cannot be serialized to JSON.
    """
    material = {"prev_hash": prev_hash, "payload": payload}
    return hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _strip_hash_fields(entry: Dict[str, Any], keys: Tuple[str, ...]) -> Dict[str, Any]:
    """Return a copy of the entry without hash metadata fields.

    Args:
        entry: Receipt or event dictionary containing hash fields.
        keys: Hash-related keys to remove.

    Returns:
        Dictionary copy without the specified hash fields.

    Resources:
        None.

    Raises:
        None.
    """
    payload = dict(entry)
    for key in keys:
        payload.pop(key, None)
    return payload


@dataclass
class State:
    """In-memory trust model state used by the reference evaluator.

    Holds append-only event and receipt logs plus derived indices for lookup.
    Resources:
        In-memory only; no external ownership.
    """
    susers: set = field(default_factory=set)
    services: set = field(default_factory=set)
    telemetry_sources: set = field(default_factory=set)
    delegations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    consents: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    telemetry: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    boundaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    entry_conditions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    shared_actions: List[Dict[str, Any]] = field(default_factory=list)
    defaults: List[Dict[str, Any]] = field(default_factory=list)
    enforcement: List[Dict[str, Any]] = field(default_factory=list)
    audits: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    disclosures: List[Dict[str, Any]] = field(default_factory=list)
    limitation_disclosures: List[Dict[str, Any]] = field(default_factory=list)
    event_log: List[Dict[str, Any]] = field(default_factory=list)
    receipt_log: List[Dict[str, Any]] = field(default_factory=list)
    next_receipt_id: int = 1
    clock: int = 0
    telemetry_exposure: Dict[str, int] = field(default_factory=dict)
    base_time_utc: str = field(default_factory=_default_base_time_utc)
    event_hash_prev: Optional[str] = None
    receipt_hash_prev: Optional[str] = None


def _clone_state(state: State) -> State:
    """Deep-copy the trust model state.

    Args:
        state: Current state snapshot to clone.

    Returns:
        Independent deep copy of the state.

    Resources:
        None.

    Raises:
        None.
    """
    return copy.deepcopy(state)


def _event_id(event: Dict[str, Any]) -> str:
    """Build a stable identifier for an event based on its content.

    Args:
        event: Event dictionary containing type and identifying keys.

    Returns:
        Stable event identifier string.

    Resources:
        None.

    Raises:
        None.
    """
    for key in (
        "delegation_id",
        "consent_id",
        "telemetry_id",
        "decision_id",
        "environment_id",
        "enforcement_id",
        "default_id",
        "audit_id",
        "disclosure_id",
        "limitation_id",
    ):
        if key in event and event[key] is not None:
            return f"{event['type']}:{event[key]}"
    return f"{event['type']}:event-{id(event)}"


def apply_event(state: State, event: Dict[str, Any]) -> Tuple[State, List[Dict[str, Any]]]:
    """Apply an event to state and emit receipts with audit metadata.

    Args:
        state: Current state snapshot.
        event: Event dictionary to apply.

    Returns:
        Tuple of (new_state, receipts) after applying the event.

    Resources:
        None.

    Raises:
        None. Unknown event types are recorded as error receipts.
    """
    # Clone before mutation so callers can treat State as immutable snapshots.
    new_state = _clone_state(state)
    event_time = new_state.clock
    event = dict(event)
    receipts: List[Dict[str, Any]] = []
    event_type = event.get("type")
    # Always strip upstream hashes so we can rebuild a clean chain locally.
    event.pop("event_hash", None)
    event.pop("event_hash_prev", None)
    event.pop("time_utc", None)

    # Unknown event types are logged as errors rather than raising.
    if event_type is None or event_type not in _KNOWN_EVENT_TYPES:
        original_type = event_type
        event["type"] = "error"
        event["original_type"] = original_type
        event["error"] = (
            "missing_event_type" if original_type is None else f"unknown_event_type:{original_type}"
        )
        event_time_utc = _event_time_utc(new_state.base_time_utc, event_time)
        event["time"] = event_time
        event["time_utc"] = event_time_utc
        event_hash = _hash_chain(
            _strip_hash_fields(event, ("event_hash", "event_hash_prev")),
            new_state.event_hash_prev,
        )
        event["event_hash_prev"] = new_state.event_hash_prev
        event["event_hash"] = event_hash
        new_state.event_hash_prev = event_hash
        new_state.event_log.append(event)

        def _add_error_receipt() -> None:
            """Record an error receipt for invalid event types.

            Returns:
                None.

            Resources:
                None.

            Raises:
                None.
            """
            receipt = {
                "type": "error_receipt",
                "event_type": original_type,
                "error": event["error"],
            }
            receipt["receipt_id"] = new_state.next_receipt_id
            receipt["time"] = event_time
            receipt["time_utc"] = event_time_utc
            receipt_hash = _hash_chain(
                _strip_hash_fields(receipt, ("receipt_hash", "receipt_hash_prev")),
                new_state.receipt_hash_prev,
            )
            receipt["receipt_hash_prev"] = new_state.receipt_hash_prev
            receipt["receipt_hash"] = receipt_hash
            new_state.receipt_hash_prev = receipt_hash
            new_state.next_receipt_id += 1
            receipts.append(receipt)

        _add_error_receipt()
        new_state.receipt_log.extend(receipts)
        return new_state, receipts

    # Normal events enter the audit log with hash chaining for traceability.
    event_time_utc = _event_time_utc(new_state.base_time_utc, event_time)
    event["time"] = event_time
    event["time_utc"] = event_time_utc
    event_hash = _hash_chain(
        _strip_hash_fields(event, ("event_hash", "event_hash_prev")),
        new_state.event_hash_prev,
    )
    event["event_hash_prev"] = new_state.event_hash_prev
    event["event_hash"] = event_hash
    new_state.event_hash_prev = event_hash
    new_state.event_log.append(event)

    def _add_receipt(data: Dict[str, Any]) -> None:
        """Append a receipt with audit hashes to the receipt buffer.

        Args:
            data: Receipt payload to enrich and append.

        Returns:
            None.

        Resources:
            None.

        Raises:
            None.
        """
        # Receipts are chained to preserve order and support audit verification.
        data["receipt_id"] = new_state.next_receipt_id
        data["time"] = event_time
        data["time_utc"] = event_time_utc
        receipt_hash = _hash_chain(
            _strip_hash_fields(data, ("receipt_hash", "receipt_hash_prev")),
            new_state.receipt_hash_prev,
        )
        data["receipt_hash_prev"] = new_state.receipt_hash_prev
        data["receipt_hash"] = receipt_hash
        new_state.receipt_hash_prev = receipt_hash
        new_state.next_receipt_id += 1
        receipts.append(data)

    # Authority establishment and delegation lifecycle.
    if event_type == "delegation":
        delegation_id = event["delegation_id"]
        scope = event.get("scope") or {}
        duration = scope.get("duration")
        expires_at = event.get("expires_at")
        if expires_at is None and duration is not None:
            expires_at = event_time + duration
        event["issued_at"] = event_time
        event["expires_at"] = expires_at
        new_state.delegations[delegation_id] = event
        new_state.susers.add(event.get("suser_id"))
        new_state.services.add(event.get("grantee_id"))
        receipt = {
            "type": "delegation_receipt",
            "delegation_id": delegation_id,
            "suser_id": event.get("suser_id"),
            "grantee_id": event.get("grantee_id"),
            "explicit": event.get("explicit"),
            "scoped": event.get("scoped"),
            "revocable": event.get("revocable"),
            "suser_can_inspect": event.get("suser_can_inspect"),
            "suser_can_contest": event.get("suser_can_contest"),
            "suser_can_revoke": event.get("suser_can_revoke"),
            "derived_from_use": event.get("derived_from_use"),
            "scope": event.get("scope"),
            "revocation_path": event.get("revocation_path"),
            "issued_at": event_time,
            "expires_at": expires_at,
        }
        _add_receipt(receipt)
    elif event_type == "revoke_delegation":
        delegation_id = event["delegation_id"]
        delay = int(event.get("delay") or 0)
        delay_disclosed = event.get("delay_disclosed")
        effective_at = event_time + delay
        if delegation_id in new_state.delegations:
            delegation = new_state.delegations[delegation_id]
            delegation["revocation_requested_at"] = event_time
            delegation["revocation_effective_at"] = effective_at
            if delay == 0:
                delegation["revoked"] = True
        receipt = {
            "type": "delegation_revocation_receipt",
            "delegation_id": delegation_id,
            "revoked": delay == 0,
            "delay": delay,
            "delay_disclosed": delay_disclosed,
            "requested_at": event_time,
            "effective_at": effective_at,
        }
        _add_receipt(receipt)
    # Consent lifecycle (issued and withdrawn).
    elif event_type == "consent":
        consent_id = event["consent_id"]
        new_state.consents[consent_id] = event
        new_state.susers.add(event.get("suser_id"))
        receipt = {
            "type": "consent_receipt",
            "consent_id": consent_id,
            "suser_id": event.get("suser_id"),
            "purpose": event.get("purpose"),
            "informed": event.get("informed"),
            "specific": event.get("specific"),
            "revocable": event.get("revocable"),
            "revocation_effective": event.get("revocation_effective"),
            "bundled": event.get("bundled"),
            "coerced": event.get("coerced"),
            "dark_pattern": event.get("dark_pattern"),
            "assumed_by_use": event.get("assumed_by_use"),
        }
        _add_receipt(receipt)
    elif event_type == "withdraw_consent":
        consent_id = event["consent_id"]
        if consent_id in new_state.consents:
            new_state.consents[consent_id]["withdrawn"] = True
        receipt = {
            "type": "consent_withdrawal_receipt",
            "consent_id": consent_id,
            "withdrawn": True,
        }
        _add_receipt(receipt)
    # Telemetry records feed later influence checks.
    elif event_type == "telemetry":
        telemetry_id = event["telemetry_id"]
        new_state.telemetry[telemetry_id] = event
        new_state.telemetry_sources.add(telemetry_id)
        new_state.telemetry_exposure[telemetry_id] = (
            new_state.telemetry_exposure.get(telemetry_id, 0) + 1
        )
        receipt = {
            "type": "telemetry_receipt",
            "telemetry_id": telemetry_id,
            "influences": event.get("influences"),
            "explained": event.get("explained"),
            "human_explainable": event.get("human_explainable"),
            "prescriptive_use": event.get("prescriptive_use"),
            "reports_to_service": event.get("reports_to_service"),
            "self_originating": event.get("self_originating"),
            "exposure_count": new_state.telemetry_exposure.get(telemetry_id, 1),
        }
        _add_receipt(receipt)
    # Service actions generate decision receipts with authority chains.
    elif event_type == "service_action":
        decision_id = event["decision_id"]
        new_state.decisions.append(event)
        new_state.services.add(event.get("service_id"))
        new_state.susers.add(event.get("suser_id"))
        delegation_id = event.get("delegation_id")
        authority_chain: List[str] = []
        chain_override = event.get("authority_chain_override")
        if chain_override is not None:
            authority_chain = list(chain_override)
        elif delegation_id in new_state.delegations:
            authority_chain = [delegation_id, new_state.delegations[delegation_id].get("suser_id")]
        receipt = {
            "type": "decision_receipt",
            "decision_id": decision_id,
            "suser_id": event.get("suser_id"),
            "service_id": event.get("service_id"),
            "delegation_id": delegation_id,
            "consent_id": event.get("consent_id"),
            "telemetry_refs": event.get("telemetry_refs", []),
            "explanation": event.get("explanation"),
            "explanation_legible": event.get("explanation_legible"),
            "report_to_suser": event.get("report_to_suser"),
            "contest_path": event.get("contest_path"),
            "revocation_path": event.get("revocation_path"),
            "authority_chain": authority_chain,
            "context_id": event.get("context_id"),
            "affected_susers": event.get("affected_susers", []),
            "reporting_constraints": event.get("reporting_constraints"),
            "reporting_constraints_disclosed": event.get(
                "reporting_constraints_disclosed"
            ),
            "decision_time": event_time,
            "delivered_to_suser": event.get("receipt_delivered"),
            "explanation_delivered": event.get("explanation_delivered"),
            "redacted_fields": event.get("redacted_fields") or [],
            "explanation_contextual": event.get("explanation_contextual"),
        }
        _add_receipt(receipt)
    # Shared-environment actions are tracked separately for RESPECT.
    elif event_type == "shared_action":
        new_state.shared_actions.append(event)
        receipt = {
            "type": "shared_action_receipt",
            "environment_id": event.get("environment_id"),
            "actor_suser_id": event.get("actor_suser_id"),
            "affected_susers": event.get("affected_susers", []),
            "consent_basis": event.get("consent_basis"),
        }
        _add_receipt(receipt)
    # Logical time moves only via explicit time_advance events.
    elif event_type == "time_advance":
        ticks = int(event.get("ticks") or 0)
        new_state.clock += ticks
        receipt = {
            "type": "time_receipt",
            "ticks": ticks,
            "from_time": event_time,
            "to_time": new_state.clock,
        }
        _add_receipt(receipt)
    # Boundary governance events model shared-environment controls.
    elif event_type == "boundary_declaration":
        environment_id = event["environment_id"]
        new_state.boundaries[environment_id] = event
        receipt = {
            "type": "boundary_receipt",
            "environment_id": environment_id,
            "explicit": event.get("explicit"),
            "scope": event.get("scope"),
            "constraints": event.get("constraints"),
        }
        _add_receipt(receipt)
    elif event_type == "entry_condition":
        environment_id = event["environment_id"]
        new_state.entry_conditions[environment_id] = event
        receipt = {
            "type": "entry_condition_receipt",
            "environment_id": environment_id,
            "conditions_defined": event.get("conditions_defined"),
        }
        _add_receipt(receipt)
    elif event_type == "entry_request":
        receipt = {
            "type": "entry_request_receipt",
            "environment_id": event.get("environment_id"),
            "entry_conditions_met": event.get("entry_conditions_met"),
            "entry_conditions_declared": event.get("entry_conditions_declared"),
        }
        _add_receipt(receipt)
    elif event_type == "boundary_rule":
        environment_id = event.get("environment_id")
        new_state.boundaries.setdefault(environment_id, {}).update(event)
        receipt = {
            "type": "boundary_rule_receipt",
            "environment_id": environment_id,
            "interface_rules_present": event.get("interface_rules_present"),
        }
        _add_receipt(receipt)
    elif event_type == "revocation_policy":
        receipt = {
            "type": "revocation_policy_receipt",
            "environment_id": event.get("environment_id"),
            "monitoring": event.get("monitoring"),
            "revocation_legible": event.get("revocation_legible"),
            "revocation_contestable": event.get("revocation_contestable"),
            "revocation_delay": event.get("revocation_delay"),
            "revocation_delay_disclosed": event.get("revocation_delay_disclosed"),
        }
        _add_receipt(receipt)
    elif event_type == "default_setting":
        duration = event.get("duration")
        expires_at = event.get("expires_at")
        if expires_at is None and duration is not None:
            expires_at = event_time + duration
        event["issued_at"] = event_time
        event["expires_at"] = expires_at
        new_state.defaults.append(event)
        receipt = {
            "type": "default_receipt",
            "default_id": event.get("default_id"),
            "justifiable": event.get("justifiable"),
            "reversible": event.get("reversible"),
            "active": event.get("active", True),
            "issued_at": event_time,
            "expires_at": expires_at,
        }
        _add_receipt(receipt)
    elif event_type == "federated_governance":
        new_state.boundaries.setdefault(event.get("environment_id"), {}).update(event)
        receipt = {
            "type": "federated_receipt",
            "environment_id": event.get("environment_id"),
            "entry_exit_defined": event.get("entry_exit_defined"),
            "non_interference": event.get("non_interference"),
            "auditability": event.get("auditability"),
            "contestable": event.get("contestable"),
        }
        _add_receipt(receipt)
    elif event_type == "boundary_failure_modes":
        receipt = {
            "type": "failure_modes_receipt",
            "environment_id": event.get("environment_id"),
            "implicit_consent": event.get("implicit_consent"),
            "opaque_enforcement": event.get("opaque_enforcement"),
            "hidden_influence": event.get("hidden_influence"),
            "irrevocable_participation": event.get("irrevocable_participation"),
        }
        _add_receipt(receipt)
    elif event_type == "respect_principles":
        receipt = {
            "type": "respect_principles_receipt",
            "environment_id": event.get("environment_id"),
            "boundary_integrity": event.get("boundary_integrity"),
            "non_coercion": event.get("non_coercion"),
            "mutual_legibility": event.get("mutual_legibility"),
            "contextual_consent": event.get("contextual_consent"),
            "contestability": event.get("contestability"),
        }
        _add_receipt(receipt)
    elif event_type == "participation_declaration":
        receipt = {
            "type": "participation_declaration_receipt",
            "environment_id": event.get("environment_id"),
            "scope_declared": event.get("scope_declared"),
            "influence_declared": event.get("influence_declared"),
            "boundaries_declared": event.get("boundaries_declared"),
            "enforcement_legible": event.get("enforcement_legible"),
            "enforcement_proportionate": event.get("enforcement_proportionate"),
            "enforcement_contestable": event.get("enforcement_contestable"),
        }
        _add_receipt(receipt)
    # Audits record minimum compliance checkpoints.
    elif event_type == "trust_audit":
        new_state.audits["trust"] = event
        receipt = {
            "type": "trust_audit_receipt",
            "audit_id": event.get("audit_id"),
            "minimum_met": event.get("minimum_met"),
        }
        _add_receipt(receipt)
    elif event_type == "respect_audit":
        new_state.audits["respect"] = event
        receipt = {
            "type": "respect_audit_receipt",
            "audit_id": event.get("audit_id"),
            "minimum_met": event.get("minimum_met"),
        }
        _add_receipt(receipt)
    # Enforcement actions must remain attributable and contestable.
    elif event_type == "enforcement":
        new_state.enforcement.append(event)
        receipt = {
            "type": "enforcement_receipt",
            "enforcement_id": event.get("enforcement_id"),
            "enforcer_id": event.get("enforcer_id"),
            "proportionate": event.get("proportionate"),
            "transparent": event.get("transparent"),
            "contestable": event.get("contestable"),
            "reversible": event.get("reversible"),
            "punitive": event.get("punitive"),
            "attributable": event.get("attributable"),
            "contest_path": event.get("contest_path"),
        }
        _add_receipt(receipt)
    # Disclosures surface system limits and user actionability.
    elif event_type == "disclosure":
        new_state.disclosures.append(event)
        receipt = {
            "type": "disclosure_receipt",
            "disclosure_id": event.get("disclosure_id"),
            "user_actionable": event.get("user_actionable"),
        }
        _add_receipt(receipt)
    elif event_type == "limitation_disclosure":
        new_state.limitation_disclosures.append(event)
        receipt = {
            "type": "limitation_receipt",
            "limitation_id": event.get("limitation_id"),
            "limits_disclosed": event.get("limits_disclosed"),
        }
        _add_receipt(receipt)

    new_state.receipt_log.extend(receipts)
    return new_state, receipts


def _evaluate_trust_unsafe(state: State) -> Report:
    """Evaluate trust violations based on recorded events and receipts.

    Args:
        state: State snapshot containing event and receipt logs.

    Returns:
        Report describing trust violations and evidence.

    Resources:
        None.

    Raises:
        None.
    """
    report = Report(kind="trust")

    # Collect evidence first so we can emit all applicable violations together.
    invalid_state = False
    justification_evidence: List[str] = []
    missing_reporting_evidence: List[str] = []
    delegation_invalid_evidence: List[str] = []
    implicit_delegation_evidence: List[str] = []
    sovereignty_displaced_evidence: List[str] = []
    consent_invalid_evidence: List[str] = []
    consent_coerced_evidence: List[str] = []
    telemetry_prescriptive_evidence: List[str] = []
    telemetry_opaque_evidence: List[str] = []
    telemetry_reporting_evidence: List[str] = []

    def _delegation_active_at(delegation: Dict[str, Any], when: int) -> bool:
        """Check whether a delegation is active at a logical timestamp.

        Args:
            delegation: Delegation event dictionary.
            when: Logical time to evaluate.

        Returns:
            True if the delegation is active at the given time.

        Resources:
            None.

        Raises:
            None.
        """
        issued_at = delegation.get("issued_at")
        if issued_at is not None and when < issued_at:
            return False
        expires_at = delegation.get("expires_at")
        if expires_at is not None and when >= expires_at:
            return False
        effective_at = delegation.get("revocation_effective_at")
        if effective_at is not None:
            return when < effective_at
        return not delegation.get("revoked", False)

    def record_justification(event: Dict[str, Any]) -> None:
        """Record justification evidence for invalid states.

        Args:
            event: Event dictionary containing justification text.

        Returns:
            None.

        Resources:
            None.

        Raises:
            None.
        """
        # Justifications preserve operator intent when a state is invalid.
        justification = event.get("justification")
        if justification:
            justification_evidence.append(
                f"{_event_id(event)}:justification:{justification}"
            )

    for event in state.event_log:
        # Reductionism scores are tracked as violations rather than ignored.
        if event.get("type") == "reductionist_metric":
            report.score = event.get("score")
        if event.get("type") == "delegation" and event.get("revocable") is False:
            record_justification(event)
        if event.get("type") == "consent" and (
            event.get("bundled")
            or event.get("coerced")
            or event.get("dark_pattern")
            or event.get("assumed_by_use")
        ):
            record_justification(event)
        if event.get("type") == "telemetry" and (
            event.get("prescriptive_use")
            or (event.get("influences") and not event.get("explained"))
            or (event.get("influences") and not event.get("human_explainable"))
        ):
            record_justification(event)

    for receipt in state.receipt_log:
        receipt_id = receipt.get("receipt_id")
        evidence = f"receipt:{receipt_id}" if receipt_id is not None else "receipt:unknown"
        # Receipts drive accountability checks even if events are missing.
        if receipt.get("type") == "decision_receipt" and receipt.get("report_to_suser") is False:
            missing_reporting_evidence.append(evidence)
        if receipt.get("type") == "decision_receipt":
            decision_time = receipt.get("decision_time")
            authority_chain = receipt.get("authority_chain") or []
            if decision_time is not None:
                # Guard against posthoc authority: receipts must not cite delegations issued later.
                for entry in authority_chain:
                    if not isinstance(entry, str):
                        continue
                    delegation = state.delegations.get(entry)
                    issued_at = delegation.get("issued_at") if delegation else None
                    if issued_at is not None and issued_at > decision_time:
                        report.add_violation(TRUST_VIOLATION.AUTHORITY_UNTRACEABLE.value, [evidence])
                        break
        if receipt.get("type") == "delegation_receipt":
            if (
                receipt.get("explicit") is False
                or receipt.get("scoped") is False
                or receipt.get("revocable") is False
            ):
                delegation_invalid_evidence.append(evidence)
            if receipt.get("derived_from_use"):
                implicit_delegation_evidence.append(evidence)
            if (
                receipt.get("suser_can_inspect") is False
                or receipt.get("suser_can_contest") is False
                or receipt.get("suser_can_revoke") is False
            ):
                sovereignty_displaced_evidence.append(evidence)
            if receipt.get("revocable") is False:
                invalid_state = True
        if receipt.get("type") == "consent_receipt":
            if (
                receipt.get("informed") is False
                or receipt.get("specific") is False
                or receipt.get("revocable") is False
                or receipt.get("revocation_effective") is False
            ):
                consent_invalid_evidence.append(evidence)
            if (
                receipt.get("bundled")
                or receipt.get("coerced")
                or receipt.get("dark_pattern")
                or receipt.get("assumed_by_use")
            ):
                consent_coerced_evidence.append(evidence)
                invalid_state = True
        if receipt.get("type") == "telemetry_receipt":
            if receipt.get("prescriptive_use"):
                telemetry_prescriptive_evidence.append(evidence)
            if receipt.get("influences") and not receipt.get("explained"):
                telemetry_opaque_evidence.append(evidence)
                invalid_state = True
            if receipt.get("influences") and not receipt.get("human_explainable"):
                invalid_state = True
            if receipt.get("reports_to_service") is False:
                telemetry_reporting_evidence.append(evidence)
                missing_reporting_evidence.append(evidence)

    for delegation in state.delegations.values():
        evidence = [_event_id(delegation)]
        if not delegation.get("explicit") or not delegation.get("scoped") or not delegation.get(
            "revocable"
        ):
            report.add_violation(TRUST_VIOLATION.DELEGATION_INVALID.value, evidence)
        if not delegation.get("suser_can_inspect") or not delegation.get("suser_can_contest"):
            report.add_violation(TRUST_VIOLATION.SOVEREIGNTY_DISPLACED.value, evidence)
        if not delegation.get("suser_can_revoke"):
            report.add_violation(TRUST_VIOLATION.SOVEREIGNTY_DISPLACED.value, evidence)
        if delegation.get("derived_from_use"):
            report.add_violation(CONSENT_VIOLATION.IMPLICIT_DELEGATION.value, evidence)
        if not delegation.get("revocable"):
            invalid_state = True
            record_justification(delegation)

    for consent in state.consents.values():
        evidence = [_event_id(consent)]
        if (
            not consent.get("informed")
            or not consent.get("specific")
            or not consent.get("revocable")
            or not consent.get("revocation_effective")
        ):
            report.add_violation(CONSENT_VIOLATION.INVALID_CONSENT.value, evidence)
        if (
            consent.get("bundled")
            or consent.get("coerced")
            or consent.get("dark_pattern")
            or consent.get("assumed_by_use")
        ):
            report.add_violation(CONSENT_VIOLATION.COERCED_OR_OPAQUE.value, evidence)
            invalid_state = True
            record_justification(consent)

    for telemetry in state.telemetry.values():
        evidence = [_event_id(telemetry)]
        if telemetry.get("prescriptive_use"):
            report.add_violation(TELEMETRY_VIOLATION.PRESCRIPTIVE_USE.value, evidence)
        if telemetry.get("influences") and not telemetry.get("explained"):
            report.add_violation(TELEMETRY_VIOLATION.OPAQUE_INFLUENCE.value, evidence)
            invalid_state = True
            record_justification(telemetry)
        if telemetry.get("influences") and not telemetry.get("human_explainable"):
            invalid_state = True
            record_justification(telemetry)
        if telemetry.get("reports_to_service") is False:
            report.add_violation(ACCOUNTABILITY_VIOLATION.MISSING_REPORTING.value, evidence)

    for decision in state.decisions:
        evidence = [_event_id(decision)]
        suser_id = decision.get("suser_id")
        # Decisions must anchor authority to an identifiable S-User.
        if not suser_id:
            report.add_violation(TRUST_VIOLATION.SUSER_UNIDENTIFIED.value, evidence)
            invalid_state = True
            record_justification(decision)
        if decision.get("admin_override"):
            report.add_violation(TRUST_VIOLATION.SOVEREIGNTY_ASSUMED.value, evidence)
        delegation_id = decision.get("delegation_id")
        delegation = state.delegations.get(delegation_id)
        decision_time_value = decision.get("time")
        decision_time = (
            int(decision_time_value) if decision_time_value is not None else state.clock
        )
        # Decision-time authority cannot be retroactively established.
        if (
            not delegation
            or delegation.get("suser_id") != suser_id
            or not _delegation_active_at(delegation, decision_time)
        ):
            report.add_violation(TRUST_VIOLATION.AUTHORITY_UNTRACEABLE.value, evidence)
        if decision.get("automated") and not decision.get("within_scope"):
            report.add_violation(TRUST_VIOLATION.AUTONOMY_OVERREACH.value, evidence)
        if decision.get("behavior_drift") and not decision.get("mutation_authority"):
            report.add_violation(TRUST_VIOLATION.AUTONOMY_OVERREACH.value, evidence)
        if (
            not decision.get("disclosed")
            or not decision.get("justified")
            or not decision.get("basis_in_delegation")
        ):
            report.add_violation(SERVICE_VIOLATION.SOVEREIGN_SUBSTITUTION.value, evidence)
        if decision.get("ordering_inverted"):
            report.add_violation(TRUST_VIOLATION.ORDERING_INVERTED.value, evidence)
        if not decision.get("report_to_suser"):
            report.add_violation(ACCOUNTABILITY_VIOLATION.MISSING_REPORTING.value, evidence)
        if decision.get("reporting_constraints") and not decision.get(
            "reporting_constraints_disclosed"
        ):
            report.add_violation(ACCOUNTABILITY_VIOLATION.MISSING_REPORTING.value, evidence)
        if decision.get("report_to_suser") and not decision.get("explanation_legible"):
            report.add_violation(ACCOUNTABILITY_VIOLATION.ILLEGIBLE_REPORTING.value, evidence)
        if not decision.get("explanation_legible"):
            report.add_violation(ACCOUNTABILITY_VIOLATION.NON_LEGIBLE_EXPLANATION.value, evidence)
        if not decision.get("explanation"):
            report.add_violation(ACCOUNTABILITY_VIOLATION.NON_LEGIBLE_EXPLANATION.value, evidence)
        if decision.get("explanation_contextual") is False:
            report.add_violation(ACCOUNTABILITY_VIOLATION.NON_LEGIBLE_EXPLANATION.value, evidence)
        if not decision.get("contest_path") or not decision.get("revocation_path"):
            report.add_violation(ACCOUNTABILITY_VIOLATION.NON_ACCOUNTABLE_OUTCOME.value, evidence)
        if not decision.get("authority_chain_complete"):
            report.add_violation(TRUST_VIOLATION.ACCOUNTABILITY_BREAK.value, evidence)
        telemetry_refs = decision.get("telemetry_refs", [])
        # Aggregate influence must be attributable to named sources.
        if len(telemetry_refs) > 1 and not decision.get("telemetry_attribution_complete", True):
            report.add_violation(TELEMETRY_VIOLATION.OPAQUE_INFLUENCE.value, evidence)
        if decision.get("telemetry_aggregate"):
            aggregate_sources = decision.get("telemetry_aggregate_sources") or []
            if not aggregate_sources:
                report.add_violation(TELEMETRY_VIOLATION.OPAQUE_INFLUENCE.value, evidence)
            else:
                missing_sources = [source for source in aggregate_sources if source not in telemetry_refs]
                if missing_sources:
                    report.add_violation(TELEMETRY_VIOLATION.OPAQUE_INFLUENCE.value, evidence)
        if telemetry_refs:
            uses_self_originating = any(
                state.telemetry.get(telemetry_id, {}).get("self_originating")
                for telemetry_id in telemetry_refs
            )
            # Self-originating telemetry requires explicit containment.
            if uses_self_originating and not decision.get("self_telemetry_contained"):
                report.add_violation(TELEMETRY_VIOLATION.OPAQUE_INFLUENCE.value, evidence)
        chain_override = decision.get("authority_chain_override")
        if chain_override is not None:
            if not isinstance(chain_override, list):
                report.add_violation(TRUST_VIOLATION.ACCOUNTABILITY_BREAK.value, evidence)
            else:
                contains_branch = any(isinstance(item, (list, dict)) for item in chain_override)
                terminates = len(chain_override) > 0 and chain_override[-1] == suser_id
                if contains_branch or not terminates:
                    report.add_violation(TRUST_VIOLATION.ACCOUNTABILITY_BREAK.value, evidence)
        if decision.get("lower_layer_authority_accumulation") or not decision.get(
            "higher_layer_can_intervene"
        ):
            report.add_violation(TRUST_VIOLATION.DIRECTIONALITY_BREACH.value, evidence)
        if decision.get("diagnostic_ready") is False:
            report.add_violation(ACCOUNTABILITY_VIOLATION.DIAGNOSTIC_GAP.value, evidence)
        if decision.get("inferred_intent"):
            invalid_state = True
            record_justification(decision)
        consent_id = decision.get("consent_id")
        if consent_id and state.consents.get(consent_id, {}).get("withdrawn"):
            report.add_violation(CONSENT_VIOLATION.INVALID_CONSENT.value, evidence)

    if invalid_state:
        # Invalid states are always surfaced even when specific violations exist.
        report.add_violation(STRUCTURAL_VIOLATION.INVALID_STATE.value, ["structural"])
        if justification_evidence:
            report.add_violation(
                STRUCTURAL_VIOLATION.JUSTIFIED_INVALIDITY.value, justification_evidence
            )

    if delegation_invalid_evidence:
        report.add_violation(
            TRUST_VIOLATION.DELEGATION_INVALID.value, delegation_invalid_evidence
        )
    if implicit_delegation_evidence:
        report.add_violation(
            CONSENT_VIOLATION.IMPLICIT_DELEGATION.value, implicit_delegation_evidence
        )
    if sovereignty_displaced_evidence:
        report.add_violation(
            TRUST_VIOLATION.SOVEREIGNTY_DISPLACED.value, sovereignty_displaced_evidence
        )
    if consent_invalid_evidence:
        report.add_violation(
            CONSENT_VIOLATION.INVALID_CONSENT.value, consent_invalid_evidence
        )
    if consent_coerced_evidence:
        report.add_violation(
            CONSENT_VIOLATION.COERCED_OR_OPAQUE.value, consent_coerced_evidence
        )
    if telemetry_prescriptive_evidence:
        report.add_violation(
            TELEMETRY_VIOLATION.PRESCRIPTIVE_USE.value, telemetry_prescriptive_evidence
        )
    if telemetry_opaque_evidence:
        report.add_violation(
            TELEMETRY_VIOLATION.OPAQUE_INFLUENCE.value, telemetry_opaque_evidence
        )
    if telemetry_reporting_evidence:
        report.add_violation(
            ACCOUNTABILITY_VIOLATION.MISSING_REPORTING.value, telemetry_reporting_evidence
        )
    if missing_reporting_evidence:
        report.add_violation(
            ACCOUNTABILITY_VIOLATION.MISSING_REPORTING.value, missing_reporting_evidence
        )

    audit = state.audits.get("trust")
    if audit is not None and not audit.get("minimum_met"):
        report.add_violation(AUDIT_VIOLATION.TRUST_MINIMUM_MISSING.value, [_event_id(audit)])

    for disclosure in state.disclosures:
        if not disclosure.get("user_actionable"):
            report.add_violation(
                ACCOUNTABILITY_VIOLATION.NON_ACTIONABLE_DISCLOSURE.value, [_event_id(disclosure)]
            )

    for limitation in state.limitation_disclosures:
        if not limitation.get("limits_disclosed"):
            report.add_violation(
                ACCOUNTABILITY_VIOLATION.LIMITS_UNDISCLOSED.value, [_event_id(limitation)]
            )

    for enforcement in state.enforcement:
        evidence = [_event_id(enforcement)]
        if (
            not enforcement.get("proportionate")
            or not enforcement.get("transparent")
            or not enforcement.get("contestable")
            or (enforcement.get("reversible") is False)
            or enforcement.get("punitive")
        ):
            report.add_violation(ENFORCEMENT_VIOLATION.SOVEREIGNTY_INCOMPATIBLE.value, evidence)
        if not enforcement.get("attributable") or not enforcement.get("enforcer_id"):
            report.add_violation(ENFORCEMENT_VIOLATION.NO_ATTRIBUTION.value, evidence)

    if any(event.get("undeterminable") for event in state.event_log):
        report.add_violation(EVALUATION_VIOLATION.UNDETERMINABLE_PASS.value, ["undeterminable"])

    if report.score is not None:
        report.add_violation(EVALUATION_VIOLATION.REDUCTIONISM.value, ["reductionism"])

    report.debug = {"events": state.event_log, "receipts": state.receipt_log}
    return report


def evaluate_trust(state: State) -> Report:
    """Evaluate trust violations with a safety net for malformed inputs.

    Args:
        state: State snapshot containing event and receipt logs.

    Returns:
        Report describing trust violations and evidence.

    Resources:
        None.

    Raises:
        None. Malformed inputs are surfaced as INVALID_STATE and ACCOUNTABILITY_BREAK.
    """
    try:
        return _evaluate_trust_unsafe(state)
    except Exception as exc:
        # Evaluator must be total: classify malformed inputs rather than crash.
        report = Report(kind="trust")
        report.add_violation(STRUCTURAL_VIOLATION.INVALID_STATE.value, ["evaluator"])
        report.add_violation(TRUST_VIOLATION.ACCOUNTABILITY_BREAK.value, ["evaluator"])
        report.debug = {
            "events": getattr(state, "event_log", []),
            "receipts": getattr(state, "receipt_log", []),
            "evaluator_error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }
        return report


def _receipt_visible_to_suser(receipt: Dict[str, Any], suser_id: str) -> bool:
    """Check whether a receipt is visible to a given S-User.

    Args:
        receipt: Receipt dictionary to inspect.
        suser_id: S-User identifier requesting visibility.

    Returns:
        True if the receipt should be visible to the S-User.

    Resources:
        None.

    Raises:
        None.
    """
    # Visibility rules preserve accountability while respecting redaction.
    receipt_type = receipt.get("type")
    if receipt_type == "decision_receipt":
        delivered = receipt.get("delivered_to_suser")
        if delivered is None:
            delivered = receipt.get("report_to_suser") is not False
        return receipt.get("suser_id") == suser_id and bool(delivered)
    if receipt_type in {"delegation_receipt", "consent_receipt"}:
        return receipt.get("suser_id") == suser_id
    if receipt_type == "shared_action_receipt":
        affected = receipt.get("affected_susers", [])
        return receipt.get("actor_suser_id") == suser_id or suser_id in affected
    return False


def _redact_receipt(receipt: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of a receipt with redacted fields removed.

    Args:
        receipt: Receipt dictionary to redact.

    Returns:
        Redacted receipt dictionary.

    Resources:
        None.

    Raises:
        None.
    """
    # Redaction enforces declared visibility limits without dropping the receipt itself.
    view = dict(receipt)
    redacted = set(view.get("redacted_fields") or [])
    if view.get("explanation_delivered") is False:
        redacted.update({"explanation", "explanation_legible"})
    for field in redacted:
        view.pop(field, None)
    if redacted:
        view["redacted_fields"] = sorted(redacted)
    return view


def suser_view(state: State, suser_id: str) -> Dict[str, Any]:
    """Build an S-User scoped view of decisions and receipts.

    Args:
        state: State snapshot containing event and receipt logs.
        suser_id: S-User identifier for the requested view.

    Returns:
        Dictionary containing decisions and visible receipts for the S-User.

    Resources:
        None.

    Raises:
        None.
    """
    # The view is receipt-only; decisions are interpreted through audit artifacts.
    receipts: List[Dict[str, Any]] = []
    for receipt in state.receipt_log:
        if _receipt_visible_to_suser(receipt, suser_id):
            receipts.append(_redact_receipt(receipt))
    return {"suser_id": suser_id, "receipts": receipts}


def evaluate_trust_view(state: State, suser_id: str) -> Report:
    """Evaluate trust violations visible to an S-User.

    Args:
        state: State snapshot containing event and receipt logs.
        suser_id: S-User identifier requesting the view.

    Returns:
        Report describing trust violations in the S-User view.

    Resources:
        None.

    Raises:
        None.
    """
    report = Report(kind="trust_view")
    view = suser_view(state, suser_id)
    # Decision receipts are grouped by decision_id to validate per-decision accountability.
    view_receipts = [
        receipt
        for receipt in view["receipts"]
        if receipt.get("type") == "decision_receipt"
    ]
    receipts_by_decision: Dict[str, List[Dict[str, Any]]] = {}
    for receipt in view_receipts:
        decision_id = receipt.get("decision_id")
        receipts_by_decision.setdefault(decision_id, []).append(receipt)

    for decision in state.decisions:
        decision_id = decision.get("decision_id")
        affected = decision.get("affected_susers", [])
        if decision.get("suser_id") != suser_id and suser_id not in affected:
            continue
        receipts = receipts_by_decision.get(decision_id, [])
        if not receipts:
            report.add_violation(
                ACCOUNTABILITY_VIOLATION.MISSING_REPORTING.value,
                [f"decision:{decision_id}:missing_receipt"],
            )
            continue
        for receipt in receipts:
            receipt_id = receipt.get("receipt_id")
            evidence = [f"receipt:{receipt_id}" if receipt_id is not None else "receipt:unknown"]
            if not receipt.get("explanation"):
                report.add_violation(
                    ACCOUNTABILITY_VIOLATION.NON_LEGIBLE_EXPLANATION.value, evidence
                )
            if receipt.get("report_to_suser") is not True:
                report.add_violation(
                    ACCOUNTABILITY_VIOLATION.MISSING_REPORTING.value, evidence
                )
            if not receipt.get("explanation_legible"):
                report.add_violation(
                    ACCOUNTABILITY_VIOLATION.ILLEGIBLE_REPORTING.value, evidence
                )
            if receipt.get("explanation_contextual") is False:
                report.add_violation(
                    ACCOUNTABILITY_VIOLATION.NON_LEGIBLE_EXPLANATION.value, evidence
                )
            if decision.get("telemetry_refs") and not receipt.get("telemetry_refs"):
                report.add_violation(TELEMETRY_VIOLATION.OPAQUE_INFLUENCE.value, evidence)
            if not receipt.get("contest_path") or not receipt.get("revocation_path"):
                report.add_violation(
                    ACCOUNTABILITY_VIOLATION.NON_ACCOUNTABLE_OUTCOME.value, evidence
                )
            chain = receipt.get("authority_chain")
            contains_branch = isinstance(chain, list) and any(
                isinstance(item, (list, dict)) for item in chain
            )
            terminates = isinstance(chain, list) and chain and chain[-1] == suser_id
            if not chain or contains_branch or not terminates:
                report.add_violation(TRUST_VIOLATION.ACCOUNTABILITY_BREAK.value, evidence)
    report.debug = {"events": state.event_log, "receipts": view["receipts"]}
    return report


def _evaluate_respect_unsafe(state: State) -> Report:
    """Evaluate respect violations based on shared-environment rules.

    Args:
        state: State snapshot containing event and receipt logs.

    Returns:
        Report describing respect violations and evidence.

    Resources:
        None.

    Raises:
        None.
    """
    report = Report(kind="respect")
    revocation_delay_disclosed_at: Optional[int] = None

    for event in state.event_log:
        # Track earliest disclosure so later delays can be judged fairly.
        if (
            event.get("type") == "revocation_policy"
            and event.get("revocation_delay")
            and event.get("revocation_delay_disclosed")
        ):
            event_time = int(event.get("time") or 0)
            if revocation_delay_disclosed_at is None:
                revocation_delay_disclosed_at = event_time
            else:
                revocation_delay_disclosed_at = min(
                    revocation_delay_disclosed_at, event_time
                )

    for event in state.event_log:
        if event.get("type") == "reductionist_metric":
            report.score = event.get("score")

    for action in state.shared_actions:
        evidence = [_event_id(action)]
        # Shared actions are evaluated for consent, scope, and boundary integrity.
        affected = action.get("affected_susers", [])
        actor = action.get("actor_suser_id")
        affects_others = any(suser != actor for suser in affected)
        consent_basis = action.get("consent_basis")
        if affects_others and (consent_basis not in {"mutual", "federated"}):
            report.add_violation(RESPECT_VIOLATION.UNILATERAL_IMPACT.value, evidence)
            report.add_violation(RESPECT_VIOLATION.MUTUAL_CONSENT_MISSING.value, evidence)
        if affects_others and not action.get("consent_legible"):
            report.add_violation(RESPECT_VIOLATION.UNILATERAL_IMPACT.value, evidence)
        if not action.get("boundary_constraints_met") or not action.get("internal_accountable"):
            report.add_violation(RESPECT_VIOLATION.BOUNDARY_IGNORED.value, evidence)
        if action.get("cross_context") and not action.get("renewed_consent"):
            report.add_violation(RESPECT_VIOLATION.CONTEXT_LEAK.value, evidence)
        if affects_others and not action.get("influence_disclosed"):
            report.add_violation(RESPECT_VIOLATION.NON_INTERFERENCE_BREACH.value, evidence)
        if affects_others and consent_basis == "unilateral":
            report.add_violation(RESPECT_VIOLATION.UNILATERAL_CONSENT_BASIS.value, evidence)
        if affects_others and consent_basis == "none" and not action.get("scope_constrained"):
            report.add_violation(RESPECT_VIOLATION.MUTUAL_CONSENT_MISSING.value, evidence)
        if action.get("diagnostic_ready") is False:
            report.add_violation(RESPECT_VIOLATION.DIAGNOSTIC_GAP.value, evidence)

    for entry in state.entry_conditions.values():
        # Entry conditions must exist before access is granted.
        if not entry.get("conditions_defined"):
            report.add_violation(
                GOVERNANCE_VIOLATION.MISSING_ENTRY_CONDITIONS.value, [_event_id(entry)]
            )

    for event in state.event_log:
        if event.get("type") == "entry_request":
            evidence = [_event_id(event)]
            if not event.get("entry_conditions_declared") or not event.get(
                "entry_conditions_met"
            ):
                report.add_violation(
                    GOVERNANCE_VIOLATION.MISSING_ENTRY_CONDITIONS.value, evidence
                )
        if event.get("type") == "boundary_rule":
            if event.get("interface_rules_present") is False:
                report.add_violation(
                    GOVERNANCE_VIOLATION.INTERFACE_GAP.value, [_event_id(event)]
                )
        if event.get("type") == "revocation_policy":
            evidence = [_event_id(event)]
            if (
                not event.get("monitoring")
                or not event.get("revocation_legible")
                or not event.get("revocation_contestable")
            ):
                report.add_violation(GOVERNANCE_VIOLATION.REVOCATION_DEFECT.value, evidence)
            if event.get("revocation_delay") and not event.get("revocation_delay_disclosed"):
                report.add_violation(GOVERNANCE_VIOLATION.REVOCATION_DEFECT.value, evidence)
        if event.get("type") == "revoke_delegation":
            delay = int(event.get("delay") or 0)
            if delay:
                disclosed = event.get("delay_disclosed")
                event_time = int(event.get("time") or 0)
                if disclosed is False or (
                    disclosed is None
                    and (
                        revocation_delay_disclosed_at is None
                        or event_time < revocation_delay_disclosed_at
                    )
                ):
                    report.add_violation(
                        GOVERNANCE_VIOLATION.REVOCATION_DEFECT.value, [_event_id(event)]
                    )
        if event.get("type") == "boundary_declaration":
            if not event.get("explicit"):
                report.add_violation(
                    RESPECT_VIOLATION.IMPLICIT_BOUNDARIES.value, [_event_id(event)]
                )
        if event.get("type") == "federated_governance":
            evidence = [_event_id(event)]
            if (
                not event.get("entry_exit_defined")
                or not event.get("non_interference")
                or not event.get("auditability")
                or not event.get("contestable")
            ):
                report.add_violation(GOVERNANCE_VIOLATION.FEDERATED_GAP.value, evidence)
        if event.get("type") == "boundary_failure_modes":
            evidence = [_event_id(event)]
            if (
                event.get("implicit_consent")
                or event.get("opaque_enforcement")
                or event.get("hidden_influence")
                or event.get("irrevocable_participation")
            ):
                report.add_violation(GOVERNANCE_VIOLATION.FAILURE_MODE_IGNORED.value, evidence)
        if event.get("type") == "respect_principles":
            evidence = [_event_id(event)]
            if (
                not event.get("boundary_integrity")
                or not event.get("non_coercion")
                or not event.get("mutual_legibility")
                or not event.get("contextual_consent")
                or not event.get("contestability")
            ):
                report.add_violation(RESPECT_VIOLATION.PRINCIPLE_BREACH.value, evidence)
        if event.get("type") == "participation_declaration":
            evidence = [_event_id(event)]
            if (
                not event.get("scope_declared")
                or not event.get("influence_declared")
                or not event.get("boundaries_declared")
                or not event.get("enforcement_legible")
                or not event.get("enforcement_proportionate")
                or not event.get("enforcement_contestable")
            ):
                report.add_violation(RESPECT_VIOLATION.OPAQUE_ENFORCEMENT.value, evidence)

    for default in state.defaults:
        evidence = [_event_id(default)]
        expires_at = default.get("expires_at")
        # Defaults must remain reversible and non-coercive over time.
        if (
            default.get("exploits_bias")
            or default.get("expands_scope")
            or default.get("privileges_platform")
            or not default.get("justifiable")
            or not default.get("reversible")
            or (
                default.get("active", True)
                and expires_at is not None
                and state.clock >= expires_at
            )
        ):
            report.add_violation(RESPECT_VIOLATION.COERCIVE_DEFAULT.value, evidence)

    audit = state.audits.get("respect")
    if audit is not None and not audit.get("minimum_met"):
        report.add_violation(AUDIT_VIOLATION.RESPECT_MINIMUM_MISSING.value, [_event_id(audit)])

    for enforcement in state.enforcement:
        evidence = [_event_id(enforcement)]
        if (
            not enforcement.get("proportionate")
            or not enforcement.get("transparent")
            or not enforcement.get("contestable")
            or (enforcement.get("reversible") is False)
            or enforcement.get("punitive")
        ):
            report.add_violation(ENFORCEMENT_VIOLATION.SOVEREIGNTY_INCOMPATIBLE.value, evidence)
        if not enforcement.get("attributable") or not enforcement.get("enforcer_id"):
            report.add_violation(ENFORCEMENT_VIOLATION.NO_ATTRIBUTION.value, evidence)

    if any(event.get("undeterminable") for event in state.event_log):
        report.add_violation(EVALUATION_VIOLATION.UNDETERMINABLE_PASS.value, ["undeterminable"])

    if report.score is not None:
        report.add_violation(EVALUATION_VIOLATION.REDUCTIONISM.value, ["reductionism"])

    report.debug = {"events": state.event_log, "receipts": state.receipt_log}
    return report


def evaluate_respect(state: State) -> Report:
    """Evaluate respect violations with a safety net for malformed inputs.

    Args:
        state: State snapshot containing event and receipt logs.

    Returns:
        Report describing respect violations and evidence.

    Resources:
        None.

    Raises:
        None. Malformed inputs are surfaced as INVALID_STATE and ACCOUNTABILITY_BREAK.
    """
    try:
        return _evaluate_respect_unsafe(state)
    except Exception as exc:
        # Evaluator must be total: classify malformed inputs rather than crash.
        report = Report(kind="respect")
        report.add_violation(STRUCTURAL_VIOLATION.INVALID_STATE.value, ["evaluator"])
        report.add_violation(TRUST_VIOLATION.ACCOUNTABILITY_BREAK.value, ["evaluator"])
        report.debug = {
            "events": getattr(state, "event_log", []),
            "receipts": getattr(state, "receipt_log", []),
            "evaluator_error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }
        return report


def query_decision(state: State, decision_id: str) -> Dict[str, Any]:
    """Return a decision summary and receipt references by decision id.

    Args:
        state: State snapshot containing event and receipt logs.
        decision_id: Decision identifier to query.

    Returns:
        Decision dictionary with receipts and visibility flags if present.

    Resources:
        None.

    Raises:
        None. Missing decisions return a minimal non-legible response.
    """
    # The query surface is intentionally minimal: it mirrors what an audit view should expose.
    decision = None
    for item in reversed(state.decisions):
        if item.get("decision_id") == decision_id:
            decision = item
            break
    if decision is None:
        return {"decision_id": decision_id, "legible": False}
    response = {
        "decision_id": decision_id,
        "origin": decision.get("service_id"),
        "data_influence": decision.get("telemetry_refs", []),
        "authoriser": decision.get("suser_id"),
        "inspector": decision.get("suser_id"),
        "revoker": decision.get("suser_id"),
        "legible": decision.get("explanation_legible"),
        "explanation": decision.get("explanation"),
        "context_id": decision.get("context_id"),
        "affected_susers": decision.get("affected_susers", []),
    }
    return response
