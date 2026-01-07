"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/hypothesis_profiles.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Registers Hypothesis profiles used by the trust-spec test suite.
 Invariants:
   Profile names are stable and settings are explicit.
 Trust Boundaries:
   No external I/O; uses Hypothesis configuration only.
 Security / Safety Notes:
   Profile settings affect test determinism and runtime.
 Dependencies:
   hypothesis.
 Operational Scope:
   Imported by pytest to register profiles before tests run.
 Revision History:
   2026-01-06 COD  Created shared profile registry with stress profile; Renamed exemplar profile to stress for clarity.
------------------------------------------------------------
 SSE Principles Observed:
   - Explicit Result-based API (no silent failures)
   - Narrative comments for auditability
   - No hidden state changes; all mutations are explicit
   - Modular structure with clear boundaries
============================================================
"""

from __future__ import annotations

from hypothesis import HealthCheck, Phase, settings


# Profile definitions are a stable API for test execution.
PROFILES = {
    "ci": dict(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
        derandomize=True,
        database=None,
    ),
    "deep": dict(
        max_examples=500,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
        derandomize=False,
        database=None,
    ),
    # Stress profile: prioritize discovery and shrinking over speed.
    "stress": dict(
        max_examples=2000,
        deadline=None,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.data_too_large,
            HealthCheck.filter_too_much,
        ],
        phases=[
            Phase.explicit,
            Phase.reuse,
            Phase.generate,
            Phase.target,
            Phase.shrink,
        ],
        derandomize=False,
    ),
}


def register_profiles() -> None:
    """Register all Hypothesis profiles used by the test suite.

    Args:
        None.

    Returns:
        None.

    Resources:
        None.

    Raises:
        None.
    """
    for name, profile in PROFILES.items():
        settings.register_profile(name, **profile)
