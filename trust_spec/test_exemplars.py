"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/test_exemplars.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Replays captured exemplars to ensure violation labels stay stable.
 Invariants:
   Tests mutate only in-memory state via trust_impl.apply_event.
 Trust Boundaries:
   No external I/O; reads local exemplar JSON only.
 Security / Safety Notes:
   JSON inputs are local and treated as untrusted; evaluator must not crash.
 Dependencies:
   pytest, json, pathlib, trust_impl.
 Operational Scope:
   Executed under pytest as part of the trust-spec suite.
 Revision History:
   2026-01-06 COD  Created exemplar replay verification test.
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
from pathlib import Path

import pytest

import trust_impl


_CAPTURE_DIR = Path(__file__).resolve().parent / "exemplars" / "_captures"


# Meta-invariant: exemplars must replay to the same violation labels.
# Why: Frozen failures should remain auditable as the model evolves.
def test_exemplar_replay_matches_recorded_violations() -> None:
    """Test exemplar replay matches recorded violations.

    Args:
        None.

    Returns:
        None.

    Resources:
        In-memory state only.

    Raises:
        AssertionError: When exemplar replay results drift from recorded violations.
    """
    if not _CAPTURE_DIR.exists():
        pytest.skip("No exemplar capture directory found.")
    bundle_paths = sorted(_CAPTURE_DIR.glob("*.json"))
    if not bundle_paths:
        pytest.skip("No exemplars captured yet.")

    for bundle_path in bundle_paths:
        bundle = json.loads(bundle_path.read_text())
        kind = bundle.get("kind")
        events = bundle.get("events", [])
        expected = sorted(bundle.get("violations", {}).get("labels", []))

        state = trust_impl.State()
        for event in events:
            state, _ = trust_impl.apply_event(state, dict(event))

        if kind == "trust":
            report = trust_impl.evaluate_trust(state)
        elif kind == "respect":
            report = trust_impl.evaluate_respect(state)
        else:
            raise AssertionError(f"Unsupported exemplar kind: {kind}")

        actual = sorted(report.labels())
        assert actual == expected, f"Exemplar drift in {bundle_path.name}"
