"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/assumptions.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Defines assumption identifiers and explanatory messages used by tests.
 Invariants:
   Assumption identifiers and messages are static constants.
 Trust Boundaries:
   No external inputs or side effects.
 Security / Safety Notes:
   N/A.
 Dependencies:
   N/A.
 Operational Scope:
   Imported by test modules to provide assertion messages.
 Revision History:
   2026-01-06 COD  Added SSE header for auditability; Added narrative comment for assumption catalog; Added invariants and trust boundary notes.
------------------------------------------------------------
 SSE Principles Observed:
   - Explicit Result-based API (no silent failures)
   - Narrative comments for auditability
   - No hidden state changes; all mutations are explicit
   - Modular structure with clear boundaries
============================================================
"""

# Assumption catalog: explicit, human-readable assertions used by tests.
ASSUMPTION_A001 = (
    "A001: Legible explanations are human-readable and tied to the specific decision context."
)
ASSUMPTION_A002 = (
    "A002: Revocable in principle requires a documented revocation path and receipt."
)
ASSUMPTION_A003 = (
    "A003: Withdrawal of consent blocks future uses tied to that consent or flags them invalid."
)
ASSUMPTION_A004 = (
    "A004: Shared-environment actions list affected S-Users in context metadata."
)
ASSUMPTION_A005 = (
    "A005: Receipts include an explicit authority chain (S-User -> delegation -> service)."
)
ASSUMPTION_A006 = (
    "A006: Boundaries are explicit objects with scope and constraints."
)
ASSUMPTION_A007 = (
    "A007: Contestability requires an explicit challenge mechanism with outcome receipts."
)
