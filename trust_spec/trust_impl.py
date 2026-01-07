"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/trust_impl.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Provides a stable import target for the system-under-test API.
 Invariants:
   Re-export surface is fixed and explicit.
 Trust Boundaries:
   No external I/O; delegates to trust_spec._sut_stub.
 Security / Safety Notes:
   This wrapper exports the stub API; swapping the source changes test behavior.
 Dependencies:
   trust_spec._sut_stub.
 Operational Scope:
   Imported by tests as trust_impl to access SUT functions and state types.
 Revision History:
   2026-01-06 COD  Added SSE header and compatibility wrapper.
   2026-01-06 COD  Added invariants and trust boundary notes.
   2026-01-06 COD  Clarified trust boundary delegation target.
   2026-01-06 COD  Added narrative comment for re-export intent.
------------------------------------------------------------
 SSE Principles Observed:
   - Explicit Result-based API (no silent failures)
   - Narrative comments for auditability
   - No hidden state changes; all mutations are explicit
   - Modular structure with clear boundaries
============================================================
"""

from __future__ import annotations

from trust_spec._sut_stub import api as _api

# Re-export the SUT surface so tests have a stable import path.
State = _api.State
apply_event = _api.apply_event
evaluate_trust = _api.evaluate_trust
evaluate_trust_view = _api.evaluate_trust_view
evaluate_respect = _api.evaluate_respect
query_decision = _api.query_decision
suser_view = _api.suser_view

__all__ = [
    "State",
    "apply_event",
    "evaluate_trust",
    "evaluate_trust_view",
    "evaluate_respect",
    "query_decision",
    "suser_view",
]
