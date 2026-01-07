<!--
Title: TRUST Spec Tests — README
Version: 1.0.1
Status: Stable
SSE Profile: Markdown & Documentation v1.3
Audience: Developers, implementers, auditors
Addressability: Formal
Scope: Running and interpreting the TRUST/RESPECT test harness; excludes production guarantees.
Last Reviewed: 2026-01-06 (UTC)
Security / Safety: Describes local test execution; no elevated privileges required.
License: CC BY-SA 4.0
Copyright: © 2026 James I.T. Wylie
Linked Artifacts:
  - Root Overview: README.md
  - Whitepaper: trust_model_v1.0.1.md
  - Test Suite: trust_spec/ (SSE-Python v1.2)
-->

# TRUST Spec Tests

This directory contains an **executable specification harness** for the TRUST and RESPECT models.

It translates the normative statements in the TRUST whitepaper into **property-based tests** and evaluates them against a **reference model and a stub system-under-test (SUT)** under adversarial conditions.

---

## What this *is*

* A **spec-to-property test suite** derived directly from the TRUST / RESPECT whitepaper.
* A **reference evaluation harness** that checks whether a system exhibits required structural properties, including:

  * authority traceability
  * delegation validity
  * consent integrity
  * telemetry subordination
  * accountability and reporting
  * boundary governance
  * non-interference in shared environments
* An **exemplar capture path** (opt-in) that freezes minimal failing cases as reviewable artifacts.
* An **adversarial test environment**, covering:

  * stateful event sequences
  * time-based attacks (expiry, delay, accumulation)
  * partial visibility and redaction
  * compliance-gaming patterns
  * retroactive “fixing” attempts
* A **tool for implementers, auditors, and reviewers** to validate that an implementation does not silently violate TRUST / RESPECT principles.

---

## What this is *not*

* **Not a production implementation** of TRUST or RESPECT.
* **Not a reference architecture** or prescribed system design.
* **Not a security proof** or a claim of real-world safety.
* **Not an endorsement** of any particular technical stack, protocol, UI, or governance mechanism.
* **Not a guarantee** that any given implementation is “trustworthy” in practice.
* **Not an auto-capture system** unless explicitly enabled for exemplar harvesting.

Passing these tests does **not** mean a system is ethical, compliant, or safe.
It means it satisfies the **explicit structural constraints tested here**, and nothing more.

---

## What “all tests passing” actually means

When all tests pass, it means:

* The tested system **does not violate** any of the encoded TRUST / RESPECT properties **within the modeled scope**.
* Structural failures such as:

  * implicit delegation
  * authority laundering
  * telemetry-driven enforcement
  * non-legible accountability
  * coercive or irreversible defaults
  * boundary leakage
  * compliance gaming
  * time-based authority abuse
    are **detected and flagged**.
* Violations **cannot be erased retroactively** by later “compliant” events.
* Missing, delayed, redacted, or obfuscated information is treated as a **failure**, not as “unknown”.

In short: passing tests means the system remains accountable **even under adversarial sequencing**, not merely in ideal or happy-path flows.

---

## Scope and limits

This harness models:

* Discrete events and append-only receipts
* Explicit identities, scopes, and delegation chains
* Abstract time advancement
* Logical authority, consent, enforcement, and reporting relationships

It does **not** model:

* UI/UX coercion beyond what is explicitly encoded
* Legal or jurisdiction-specific interpretation
* Human comprehension variance
* Social or organisational power dynamics outside the defined model
* Real-world enforcement institutions

If a concern cannot be expressed as a property here, it is **out of scope by design**, not ignored.

---

## How to use this test suite

These tests are designed to be run against **any implementation** of TRUST / RESPECT by swapping the system-under-test import.

### Run CI profile (fast, deterministic)

From the repository root:

```
pytest -q trust_spec --hypothesis-profile=ci
```

From inside `trust_spec/`:

```
pytest -q . --hypothesis-profile=ci
```

### Run deep profile (adversarial stress)

From the repository root:

```
pytest -q trust_spec --hypothesis-profile=deep
```

From inside `trust_spec/`:

```
pytest -q . --hypothesis-profile=deep
```

### Hypothesis profiles

This suite defines three Hypothesis profiles:

* `ci`: Fast, deterministic, and minimal. Use this on every commit.
* `deep`: Broader adversarial search. Use for manual or scheduled runs.
* `stress`: Adversarial search tuned for harvesting invalid-state exemplars.
  Slow by design; pairs well with `TRUST_EXEMPLARS=1`.

Example usage from inside `trust_spec/`:

```
pytest -q . --hypothesis-profile=ci
pytest -q . --hypothesis-profile=deep
TRUST_EXEMPLARS=1 pytest -q . --hypothesis-profile=stress
```

### Exemplar capture (opt-in)

Exemplar capture is disabled by default. To enable it for explicitly marked tests:

```
TRUST_EXEMPLARS=1 pytest -q . --hypothesis-profile=stress
```

Captured JSON bundles are written under `trust_spec/exemplars/_captures/` and rendered Markdown is written to `trust_spec/exemplars/_rendered/`.

### Reproduce failures with a seed

From the repository root:

```
pytest -q trust_spec --hypothesis-profile=ci --hypothesis-seed=12345
```

From inside `trust_spec/`:

```
pytest -q . --hypothesis-profile=ci --hypothesis-seed=12345
```

---

## Swapping in a real implementation

All tests import the system under test via:

```
from trust_spec._sut_stub import api as trust_impl
```

Replace this import with your real implementation to evaluate it against the TRUST / RESPECT specification.

If your implementation fails these tests, the failure represents a **specific, named structural violation**, not a stylistic disagreement.

---

## Design intent

This harness exists to make **disagreement precise**.

If you believe a TRUST or RESPECT requirement is wrong, incomplete, or misinterpreted, the correct response is to challenge or extend the **property definition**, not to bypass or weaken the test.

---

© 2026 James I.T. Wylie.  
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
