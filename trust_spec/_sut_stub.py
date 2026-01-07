"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/_sut_stub.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Stub API that points tests at the reference model implementation.
 Invariants:
   Stub re-exports the reference model API without mutation.
 Trust Boundaries:
   No external I/O; delegates to in-process reference model.
 Security / Safety Notes:
   Swapping to a real implementation changes the system-under-test behavior.
 Dependencies:
   types.SimpleNamespace, trust_spec._reference_model.
 Operational Scope:
   Imported by tests as trust_impl.
 Revision History:
   2026-01-06 COD  Added SSE header for auditability.
   2026-01-06 COD  Added narrative comment for stub binding.
   2026-01-06 COD  Added invariants and trust boundary notes.
------------------------------------------------------------
 SSE Principles Observed:
   - Explicit Result-based API (no silent failures)
   - Narrative comments for auditability
   - No hidden state changes; all mutations are explicit
   - Modular structure with clear boundaries
============================================================
"""

from types import SimpleNamespace

from trust_spec import _reference_model as ref

# Stable binding: tests import trust_impl while pointing at the reference model here.
api = SimpleNamespace(
    State=ref.State,
    apply_event=ref.apply_event,
    evaluate_trust=ref.evaluate_trust,
    evaluate_trust_view=ref.evaluate_trust_view,
    evaluate_respect=ref.evaluate_respect,
    query_decision=ref.query_decision,
    suser_view=ref.suser_view,
)
