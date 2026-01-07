"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/exemplars.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Capture, normalize, and render invalid-state exemplars from test failures.
 Invariants:
   Exemplar capture is opt-in and never mutates test outcomes.
 Trust Boundaries:
   Writes local JSON/Markdown artifacts only when TRUST_EXEMPLARS is set.
 Security / Safety Notes:
   No external I/O; redact volatile receipt fields for audit stability.
 Dependencies:
   json, os, pathlib, datetime, trust_spec.violations.
 Operational Scope:
   Used by selected tests to freeze failing sequences as reviewable artifacts.
Revision History:
   2026-01-06 COD  Created exemplar capture and rendering helpers; Switched exemplar index updates to append-only with rebuild flag.
------------------------------------------------------------
 SSE Principles Observed:
   - Explicit Result-based API (no silent failures)
   - Narrative comments for auditability
   - No hidden state changes; all mutations are explicit
   - Modular structure with clear boundaries
============================================================
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from trust_spec.violations import Report


EXEMPLAR_ENV_VAR = "TRUST_EXEMPLARS"
_INDEX_REBUILD_ENV = "TRUST_EXEMPLARS_REBUILD_INDEX"

_BASE_DIR = Path(__file__).resolve().parent / "exemplars"
_CAPTURE_DIR = _BASE_DIR / "_captures"
_RENDER_DIR = _BASE_DIR / "_rendered"
_README_PATH = _BASE_DIR / "README.md"

# Volatile fields are stripped so exemplars remain stable across runs.
_VOLATILE_EVENT_FIELDS = {"event_hash", "event_hash_prev", "time_utc"}
_VOLATILE_RECEIPT_FIELDS = {"receipt_hash", "receipt_hash_prev", "receipt_id", "time_utc"}


def exemplars_enabled() -> bool:
    """Return whether exemplar capture is enabled.

    Args:
        None.

    Returns:
        True when TRUST_EXEMPLARS is set to a truthy value.

    Resources:
        None.

    Raises:
        None.
    """
    # Capture is explicit and opt-in to avoid polluting normal test runs.
    value = os.environ.get(EXEMPLAR_ENV_VAR, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _index_rebuild_enabled() -> bool:
    """Return whether the exemplar index should be rebuilt.

    Args:
        None.

    Returns:
        True when TRUST_EXEMPLARS_REBUILD_INDEX is set to a truthy value.

    Resources:
        Environment variable TRUST_EXEMPLARS_REBUILD_INDEX.

    Raises:
        None.
    """
    # Rebuild is explicit so index updates remain append-only by default.
    value = os.environ.get(_INDEX_REBUILD_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _utc_now() -> str:
    """Return the current UTC time as an RFC-3339 timestamp string.

    Args:
        None.

    Returns:
        RFC-3339 UTC timestamp string.

    Resources:
        None.

    Raises:
        None.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def source_metadata(
    test_name: str,
    *,
    hypothesis_profile: Optional[str] = None,
    hypothesis_seed: Optional[str] = None,
    pytest_nodeid: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """Build a source metadata record for an exemplar bundle.

    Args:
        test_name: Name of the failing test.
        hypothesis_profile: Hypothesis profile name if known.
        hypothesis_seed: Hypothesis seed if known.
        pytest_nodeid: Optional pytest nodeid for traceability.

    Returns:
        Source metadata dictionary for the exemplar bundle.

    Resources:
        None.

    Raises:
        None.
    """
    return {
        "test_name": test_name,
        "hypothesis_profile": hypothesis_profile or os.environ.get("HYPOTHESIS_PROFILE"),
        "hypothesis_seed": hypothesis_seed or os.environ.get("HYPOTHESIS_SEED"),
        "pytest_nodeid": pytest_nodeid or os.environ.get("PYTEST_CURRENT_TEST"),
    }


def _normalize_events(events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize events by removing volatile fields.

    Args:
        events: Iterable of event dictionaries.

    Returns:
        List of normalized event dictionaries.

    Resources:
        None.

    Raises:
        None.
    """
    normalized: List[Dict[str, Any]] = []
    for event in events:
        # Preserve order while stripping volatile hash/time fields.
        cleaned = {key: value for key, value in event.items() if key not in _VOLATILE_EVENT_FIELDS}
        normalized.append(cleaned)
    return normalized


def _normalize_receipts(receipts: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize receipts by removing volatile fields.

    Args:
        receipts: Iterable of receipt dictionaries.

    Returns:
        List of normalized receipt dictionaries.

    Resources:
        None.

    Raises:
        None.
    """
    normalized: List[Dict[str, Any]] = []
    for receipt in receipts:
        # Receipts are normalized to keep replay stable across time/hash differences.
        cleaned = {
            key: value for key, value in receipt.items() if key not in _VOLATILE_RECEIPT_FIELDS
        }
        normalized.append(cleaned)
    return normalized


def _canonical_json(payload: Dict[str, Any]) -> str:
    """Serialize payload to canonical JSON.

    Args:
        payload: JSON-serializable payload.

    Returns:
        Canonical JSON string with stable ordering.

    Resources:
        None.

    Raises:
        TypeError: If payload contains non-serializable values.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _bundle_violations(report: Report) -> Dict[str, Any]:
    """Extract canonical violation data from a report.

    Args:
        report: Report instance to extract from.

    Returns:
        Dictionary with sorted labels and evidence mapping.

    Resources:
        None.

    Raises:
        None.
    """
    # Labels and evidence are sorted to keep bundle diffs deterministic.
    labels = sorted(set(report.labels()))
    evidence_index = report.evidence_index()
    evidence = {label: sorted(set(items)) for label, items in evidence_index.items()}
    return {"labels": labels, "evidence": evidence}


def build_bundle(
    *,
    exemplar_id: str,
    kind: str,
    events: Iterable[Dict[str, Any]],
    receipts: Iterable[Dict[str, Any]],
    report: Report,
    source: Dict[str, Optional[str]],
    notes: Optional[str] = None,
    spec_map: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build an exemplar bundle from events, receipts, and a report.

    Args:
        exemplar_id: Stable exemplar identifier string.
        kind: trust or respect for the initial implementation.
        events: Ordered list of event dictionaries.
        receipts: Receipt dictionaries captured during evaluation.
        report: Report instance containing violations.
        source: Source metadata for the exemplar.
        notes: Optional narrative notes.
        spec_map: Optional list of spec identifiers.

    Returns:
        Exemplar bundle dictionary ready for serialization.

    Resources:
        None.

    Raises:
        None.
    """
    # Bundle content is normalized now so JSON output remains deterministic.
    bundle = {
        "id": exemplar_id,
        "created_utc": _utc_now(),
        "source": source,
        "kind": kind,
        "events": _normalize_events(events),
        "receipts": _normalize_receipts(receipts),
        "violations": _bundle_violations(report),
    }
    if notes is not None:
        bundle["notes"] = notes
    if spec_map is not None:
        bundle["spec_map"] = spec_map
    return bundle


def _ensure_dirs() -> None:
    """Ensure exemplar directories exist.

    Args:
        None.

    Returns:
        None.

    Resources:
        Local filesystem under trust_spec/exemplars.

    Raises:
        OSError: If directories cannot be created.
    """
    # Idempotent directory creation keeps capture safe in concurrent runs.
    _CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    _RENDER_DIR.mkdir(parents=True, exist_ok=True)


def write_bundle(bundle: Dict[str, Any]) -> Path:
    """Write the exemplar bundle to canonical JSON.

    Args:
        bundle: Exemplar bundle dictionary.

    Returns:
        Path to the written JSON file.

    Resources:
        Local filesystem under trust_spec/exemplars.

    Raises:
        OSError: If writing fails.
    """
    # Canonical JSON is used so diffs reflect semantic changes only.
    _ensure_dirs()
    output_path = _CAPTURE_DIR / f"{bundle['id']}.json"
    output_path.write_text(_canonical_json(bundle) + "\n")
    return output_path


def _humanize_label(label: str) -> str:
    """Return a readable label phrase from a violation identifier.

    Args:
        label: Violation label string.

    Returns:
        Humanized label text.

    Resources:
        None.

    Raises:
        None.
    """
    # Humanized labels are used for narrative summaries, not enforcement logic.
    suffix = label.split(".")[-1].replace("_", " ").lower()
    return suffix


def _violation_sentence(label: str) -> str:
    """Build a narrative sentence for a violation label.

    Args:
        label: Violation label string.

    Returns:
        Narrative sentence for the violation.

    Resources:
        None.

    Raises:
        None.
    """
    # Templates keep narrative explanations consistent across exemplars.
    prefix = label.split(".")[0] if "." in label else label
    human = _humanize_label(label)
    templates = {
        "TRUST_VIOLATION": "Authority or delegation integrity failed ({human}).",
        "ACCOUNTABILITY_VIOLATION": "Reporting or legibility failed ({human}).",
        "TELEMETRY_VIOLATION": "Telemetry influence rules failed ({human}).",
        "CONSENT_VIOLATION": "Consent integrity failed ({human}).",
        "RESPECT_VIOLATION": "Shared-environment respect rules failed ({human}).",
        "GOVERNANCE_VIOLATION": "Governance or boundary rules failed ({human}).",
        "SERVICE_VIOLATION": "Service sovereignty rules failed ({human}).",
        "STRUCTURAL_VIOLATION": "State structure is invalid ({human}).",
        "AUDIT_VIOLATION": "Audit minimums were not satisfied ({human}).",
        "ENFORCEMENT_VIOLATION": "Enforcement accountability failed ({human}).",
        "EVALUATION_VIOLATION": "Evaluation integrity failed ({human}).",
    }
    template = templates.get(prefix, "Violation recorded ({human}).")
    return template.format(human=human)


def _render_json_block(payload: Dict[str, Any]) -> str:
    """Render a JSON payload as a fenced code block.

    Args:
        payload: JSON-serializable payload.

    Returns:
        Markdown code block string.

    Resources:
        None.

    Raises:
        TypeError: If payload contains non-serializable values.
    """
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True)
    return f"```json\n{text}\n```"


def _render_events(events: List[Dict[str, Any]]) -> str:
    """Render events as a JSON block.

    Args:
        events: Normalized event list.

    Returns:
        Markdown JSON block string.

    Resources:
        None.

    Raises:
        TypeError: If events are not JSON-serializable.
    """
    return _render_json_block(events)


def _render_receipts(receipts: List[Dict[str, Any]]) -> str:
    """Render receipts as a JSON block.

    Args:
        receipts: Normalized receipt list.

    Returns:
        Markdown JSON block string.

    Resources:
        None.

    Raises:
        TypeError: If receipts are not JSON-serializable.
    """
    return _render_json_block(receipts)


def render_markdown(bundle: Dict[str, Any]) -> str:
    """Render a Markdown exemplar page from a bundle.

    Args:
        bundle: Exemplar bundle dictionary.

    Returns:
        Markdown string for the exemplar.

    Resources:
        None.

    Raises:
        None.
    """
    # Rendering is template-driven to keep exemplars readable and consistent.
    source = bundle.get("source", {})
    labels = bundle.get("violations", {}).get("labels", [])
    notes = bundle.get("notes")
    spec_map = bundle.get("spec_map")

    narrative_lines = [f"- `{label}`: {_violation_sentence(label)}" for label in labels]
    narrative = "\n".join(narrative_lines) if narrative_lines else "- (No violations recorded.)"

    remedy_prefixes = {label.split(".")[0] for label in labels}
    remedy_map = {
        "TRUST_VIOLATION": "Provide explicit delegation before the decision time and ensure the chain is complete.",
        "ACCOUNTABILITY_VIOLATION": "Publish legible receipts with contest/revoke paths and reporting constraints disclosed.",
        "TELEMETRY_VIOLATION": "Explain telemetry influence and prevent telemetry from acting as authority.",
        "CONSENT_VIOLATION": "Ensure consent is informed, specific, revocable, and not implied by use.",
        "RESPECT_VIOLATION": "Define shared-environment boundaries and require mutual, legible consent.",
        "GOVERNANCE_VIOLATION": "Declare entry conditions and boundary governance with contestable revocation.",
        "SERVICE_VIOLATION": "Require delegated authority and disclosure for service actions.",
        "STRUCTURAL_VIOLATION": "Fix malformed or inconsistent event/receipt data.",
        "AUDIT_VIOLATION": "Provide audit minimums before asserting compliance.",
        "ENFORCEMENT_VIOLATION": "Make enforcement attributable, proportionate, and contestable.",
        "EVALUATION_VIOLATION": "Avoid reductionist scoring; document contextual evaluation inputs.",
    }
    remedy_lines = [
        f"- {remedy_map[prefix]}"
        for prefix in sorted(remedy_prefixes)
        if prefix in remedy_map
    ]
    remedy = "\n".join(remedy_lines) if remedy_lines else "- Review violation labels and address the missing authority or disclosures."

    header = (
        "<!--\n"
        f"Title: TRUST Spec Exemplar — {bundle.get('id')}\n"
        "Version: 1.0.2\n"
        "Status: Generated\n"
        "SSE Profile: Markdown & Documentation v1.3\n"
        "Audience: Developers, implementers, auditors\n"
        "Scope: Invalid-state exemplar derived from trust/respect evaluation\n"
        "Security / Safety: Contains redacted receipts; no secrets should be present\n"
        "-->\n"
    )
    content = [
        header,
        f"# Exemplar {bundle.get('id')}",
        "",
        "## Context",
        f"- Kind: {bundle.get('kind')}",
        f"- Created: {bundle.get('created_utc')}",
        f"- Source test: {source.get('test_name')}",
        f"- Hypothesis profile: {source.get('hypothesis_profile')}",
        f"- Hypothesis seed: {source.get('hypothesis_seed')}",
        f"- Pytest nodeid: {source.get('pytest_nodeid')}",
    ]
    if spec_map:
        content.extend(["- Spec map: " + ", ".join(spec_map)])
    content.extend(
        [
            "",
            "## Violations",
            "\n".join([f"- `{label}`" for label in labels]) or "- (None)",
            "",
            "## Events",
            _render_events(bundle.get("events", [])),
            "",
            "## Receipts",
            _render_receipts(bundle.get("receipts", [])),
            "",
            "## Narrative",
            narrative,
            "",
            "## What Would Make This Valid",
            remedy,
        ]
    )
    if notes:
        content.extend(["", "## Notes", notes])
    return "\n".join(content).strip() + "\n"


def write_rendered(bundle: Dict[str, Any]) -> Path:
    """Write the rendered exemplar Markdown.

    Args:
        bundle: Exemplar bundle dictionary.

    Returns:
        Path to the written Markdown file.

    Resources:
        Local filesystem under trust_spec/exemplars.

    Raises:
        OSError: If writing fails.
    """
    # Rendered output is generated alongside JSON for human review.
    _ensure_dirs()
    output_path = _RENDER_DIR / f"{bundle['id']}.md"
    output_path.write_text(render_markdown(bundle))
    return output_path


def update_index() -> None:
    """Update the exemplar README index with available rendered files.

    Args:
        None.

    Returns:
        None.

    Resources:
        Local filesystem under trust_spec/exemplars.
        Environment variable TRUST_EXEMPLARS_REBUILD_INDEX.

    Raises:
        OSError: If writing fails.
    """
    # Index updates are append-only by default to preserve audit history.
    _ensure_dirs()
    rendered = sorted(path.name for path in _RENDER_DIR.glob("*.md"))
    header = (
        "<!--\n"
        "Title: TRUST Spec Exemplars — Index\n"
        "Version: 1.0.2\n"
        "Status: Generated\n"
        "SSE Profile: Markdown & Documentation v1.3\n"
        "Audience: Developers, implementers, auditors\n"
        "Scope: Index of invalid-state exemplar renderings\n"
        "Security / Safety: Links only; no secrets should be present\n"
        "Generation: Produced by trust_spec/exemplars.py when TRUST_EXEMPLARS=1\n"
        "Index Update: Append-only unless TRUST_EXEMPLARS_REBUILD_INDEX=1\n"
        "-->\n"
    )
    lines = [
        header,
        "# TRUST Spec Exemplars",
        "",
        "This index links generated exemplar renderings.",
        "Entries are appended by default to preserve the audit trail.",
        "Set TRUST_EXEMPLARS_REBUILD_INDEX=1 to rebuild the index.",
        "",
    ]
    if _index_rebuild_enabled() or not _README_PATH.exists():
        if rendered:
            lines.extend([f"- `_rendered/{name}`" for name in rendered])
        else:
            lines.append("- (No exemplars captured yet.)")
        _README_PATH.write_text("\n".join(lines).strip() + "\n")
        return

    existing = _README_PATH.read_text().splitlines()
    existing_entries = {
        line for line in existing if line.startswith("- `_rendered/") and line.endswith("`")
    }
    new_entries = [
        f"- `_rendered/{name}`"
        for name in rendered
        if f"- `_rendered/{name}`" not in existing_entries
    ]
    if not new_entries:
        return
    with _README_PATH.open("a", encoding="utf-8") as handle:
        if existing and existing[-1] != "":
            handle.write("\n")
        handle.write("\n".join(new_entries) + "\n")


def capture_on_failure(
    *,
    exemplar_id: str,
    kind: str,
    events: Iterable[Dict[str, Any]],
    receipts: Iterable[Dict[str, Any]],
    report: Report,
    assertion: Callable[[], None],
    source: Dict[str, Optional[str]],
    notes: Optional[str] = None,
    spec_map: Optional[List[str]] = None,
) -> None:
    """Run an assertion and capture an exemplar bundle on failure.

    Args:
        exemplar_id: Stable exemplar identifier string.
        kind: trust or respect for the initial implementation.
        events: Ordered list of event dictionaries.
        receipts: Receipt dictionaries captured during evaluation.
        report: Report instance containing violations.
        assertion: Callable that raises AssertionError on failure.
        source: Source metadata for the exemplar.
        notes: Optional narrative notes.
        spec_map: Optional list of spec identifiers.

    Returns:
        None.

    Resources:
        Local filesystem under trust_spec/exemplars if capture is enabled.

    Raises:
        AssertionError: Re-raised after capture.
    """
    try:
        assertion()
    except AssertionError:
        # Best-effort capture is isolated; failures here never mask the test failure.
        if exemplars_enabled():
            try:
                bundle = build_bundle(
                    exemplar_id=exemplar_id,
                    kind=kind,
                    events=events,
                    receipts=receipts,
                    report=report,
                    source=source,
                    notes=notes,
                    spec_map=spec_map,
                )
                write_bundle(bundle)
                write_rendered(bundle)
                update_index()
            except Exception:
                # Best-effort capture only; evaluator behavior remains unchanged.
                pass
        raise
