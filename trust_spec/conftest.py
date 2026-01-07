"""
============================================================
 Synavera Project: trust-model
 Module: trust_spec/conftest.py
 Etiquette: Synavera Script Etiquette (SSE v1.2)
------------------------------------------------------------
 Purpose:
   Configures pytest and Hypothesis profiles for trust spec tests.
 Invariants:
   Configures pytest/Hypothesis only; does not alter test data.
 Trust Boundaries:
   Mutates sys.path and environment variables within pytest runtime only.
 Security / Safety Notes:
   Adjusts sys.path and sets HYPOTHESIS_SEED; run in a controlled test environment.
 Dependencies:
   pytest, hypothesis.
 Operational Scope:
   Loaded by pytest to register profiles and CLI options.
 Revision History:
   2026-01-06 COD  Added SSE header for auditability; Added narrative comments for profile and path setup; Added invariants and trust boundary notes; Delegated profile registration to hypothesis_profiles.
------------------------------------------------------------
 SSE Principles Observed:
   - Explicit Result-based API (no silent failures)
   - Narrative comments for auditability
   - No hidden state changes; all mutations are explicit
   - Modular structure with clear boundaries
============================================================
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest
from hypothesis import settings

from trust_spec.hypothesis_profiles import PROFILES, register_profiles


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register TRUST-specific pytest CLI options.

    Args:
        parser: Pytest argument parser used to register options.

    Returns:
        None.

    Resources:
        None.

    Raises:
        None.
    """
    parser.addoption(
        "--trust-profile",
        action="store",
        default=None,
        help=(
            "Alias for Hypothesis profile: ci, deep, or stress "
            "(use --hypothesis-profile if preferred)"
        ),
    )
    parser.addoption(
        "--trust-seed",
        action="store",
        type=int,
        default=None,
        help="Alias for Hypothesis seed (use --hypothesis-seed if preferred)",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure Hypothesis profiles and trust-spec environment hooks.

    Args:
        config: Pytest configuration instance populated with CLI options.

    Returns:
        None.

    Resources:
        None.

    Raises:
        pytest.UsageError: If an unknown Hypothesis profile is selected.
    """
    # Make trust_spec importable before repo root so trust_impl resolves locally.
    spec_dir = Path(__file__).resolve().parent
    root = spec_dir.parent
    if str(spec_dir) not in sys.path:
        sys.path.insert(0, str(spec_dir))
    if str(root) not in sys.path:
        insert_at = 1 if sys.path and sys.path[0] == str(spec_dir) else 0
        sys.path.insert(insert_at, str(root))

    register_profiles()

    profile_name = config.getoption("trust_profile")
    if profile_name is None:
        profile_name = getattr(config.option, "hypothesis_profile", None)
    if profile_name is None:
        profile_name = "ci"
    seed = config.getoption("trust_seed")
    if seed is not None and getattr(config.option, "hypothesis_seed", None) is None:
        config.option.hypothesis_seed = seed
        os.environ.setdefault("HYPOTHESIS_SEED", str(seed))

    if profile_name not in PROFILES:
        raise pytest.UsageError(f"Unknown Hypothesis profile: {profile_name}")

    settings.load_profile(profile_name)
