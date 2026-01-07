<!--
Title: Synavera Script Etiquette — Python Profile
Version: 1.2
Status: Stable
SSE Profile: Python Variant v1.2; Markdown & Documentation v1.2; Universal SSE v1.2
Audience: Python developers, maintainers, auditors, and Synavera tooling authors
Scope: Defines Python-specific etiquette layered atop Universal SSE v1.2; covers structure, safety, auditability, environment discipline, errors, packaging, I/O boundaries, and runtime expectations. Does **not** define framework-specific policy (e.g., Django, FastAPI) unless explicitly noted.
Last Reviewed: 2025-12-09 (UTC)
Security / Safety: Non-compliant Python code may cause data loss, silent failure, injection vulnerabilities, or privilege misuse. This document defines required safeguards.
Linked Artifacts:
  - Universal SSE: v1.2
  - SSE-Markdown & Documentation: v1.3
  - SSE-JSON: v1.2
  - SSE-YAML: v1.2
Owner: Synavera Standards Authority (SSA)
Applies To: Synavera Python codebases targeting Python 3.10+
Tags: sse, python, audit, safety, guidelines
-->

# Synavera Script Etiquette — Python Profile v1.2

Python under Synavera is treated as a clarity-first, safety-bound environment. It enables rapid
expression — but without the discipline of explicit contracts, runtime checks, and careful module
design, Python can also introduce ambiguity and security risks. This profile defines the Python-
specific etiquette expected when writing Synavera-grade software.

---

## 1. Verbosity vs Brevity
**Chosen Approach:** Explicit + Intent-Driven

Python allows very concise code. Synavera requires that code remain explicit instead:
- Prefer descriptive variable, function, and module names.
- Avoid clever one-liners that hide control flow.
- Avoid dynamic metaprogramming unless explicitly justified.
- Use type hints for all public APIs and for internal boundaries where it improves clarity.

Silence and implicit behaviour are fragility; explicitness is security.

---

## 2. Error Handling and Fault Philosophy
**Chosen Approach:** Exception-last; explicit result objects or raised errors with context

Rules:
- Public APIs should return `Result[T, E]`-like objects or raise documented exceptions.
- Never swallow exceptions. Catch blocks must:
  - log with timestamp,
  - redact sensitive values,
  - rethrow or translate deterministically.
- Any failure that crosses a subsystem boundary must leave an auditable log entry.
- Tracebacks must never reveal secrets.
- Use domain-specific exception hierarchies.

Example boundary wrapper:
```python
class SseError(Exception):
    def __init__(self, code: str, message: str, *, context: dict | None = None):
        super().__init__(message)
        self.code = code
        self.context = context or {}
```

**Security Note:** Errors must not leak tokens, credentials, PII, or raw object dumps.

---

## 3. Organizational Structure
**Chosen Approach:** Modular + import-safe + dependency-injected

Python’s import system makes hidden side effects easy. Synavera forbids them.

Requirements:
- Module imports must not mutate global state.
- No work at import time beyond constant definitions.
- All I/O, secret loading, and environment checks must be inside functions.
- Break systems into coherent, testable modules.
- Dependencies must be injected (constructor or function injection), not hidden.
- Avoid singletons; prefer explicit ownership.

**TODO [SSE-PY-STRUCT-01]:** Define a canonical Synavera Python project layout analogous to SSE-C Core.

---

## 4. Commentary, Documentation, and Narrative Context
**Chosen Approach:** Storytelling with Security/Safety annotations

Each `.py` file must begin with an SSE header describing purpose, invariants, trust boundaries, and
risk. Public functions and classes require docstrings defining:
- purpose,
- inputs/outputs,
- error behaviour,
- lifetime/ownership of resources.

Sensitive operations require `Security:` or `Safety:` annotations.

Comments explain **why**, not code mechanics.

---

## 5. Aesthetic and Formatting Conventions
**Chosen Approach:** Tool-enforced consistency + Synavera discipline

- Formatting via `black`.
- Imports sorted with `isort`.
- Static analysis via `ruff` with strict rules.
- UTF-8 encoding; newline at EOF.
- No alignment tricks, compressed lambdas, or dense comprehensions.
- Whitespace separates conceptual blocks.

---

## 6. Ethical Layer
**Chosen Approach:** User Agency + Explicit Consent

Python programs may be automation-heavy. All potentially destructive behaviour must:
- be explicitly documented,
- require operator confirmation or safe flags,
- avoid silent network calls or telemetry.

Sensitive material must never be logged. Users remain sovereign.

---

## 7. Auditability and Temporal Trace
**Chosen Approach:** Immutable, structured, timestamped

Logging requirements:
- RFC-3339 timestamps.
- Structured logs (JSON or key-value).
- Redacted sensitive fields.
- Append-only with archival rotation.
- Optional SHA-256 chaining.

All operational events must be traceable.

---

## 8. Environment, Virtualization, and Reproducibility
**Chosen Approach:** Deterministic execution + explicit environment rules

Python environments are notoriously mutable. Synavera mandates:
- Locked dependencies with `requirements.lock` or `poetry.lock`.
- Python version fixed per project (min Python 3.10).
- Virtual environments mandatory for local development.
- No implicit activation in scripts.
- Environment variables validated before use.
- Runtime behaviour must be reproducible.

**Safety Note:** A missing dependency or mismatched Python version must fail early.

---

## 9. Resource Management (Files, Processes, Network)
**Chosen Approach:** Context-managed + explicit boundaries

- Always use context managers (`with`) for resources.
- All network operations must:
  - log destination,
  - include timeout,
  - document security expectations.
- File operations must:
  - validate paths,
  - avoid implicit directory creation,
  - explicitly document destructive effects.

**Security Note:** Never open files or sockets using unvalidated user input.

---

## 10. Type System, Contracts, and Defensive Edges
**Chosen Approach:** Annotated + validated + defensive

Requirements:
- All public APIs must use type hints.
- Use `typing` or `pydantic`/`attrs`/`dataclasses` for explicit contracts.
- Validate inputs at subsystem boundaries.
- Avoid dynamic attribute injection (`__dict__` hacks).
- Unsafe introspection or monkey-patching must be:
  - minimal,
  - justified,
  - documented,
  - tested.

**TODO [SSE-PY-SAFETY-02]:** Define approved frameworks for contracts (pydantic v2, typing-extensions rules).

---

## 11. Concurrency and Asynchrony
**Chosen Approach:** Structured + predictable + context-managed

Python supports threads, multiprocessing, and async — each with risk.

Rules:
- Choose one model per subsystem.
- Async code must use `asyncio` with explicit cancellation and timeouts.
- No implicit background tasks.
- Concurrency primitives must be documented with ownership.
- Thread and process pools must be lifecycle-bound.
- Test concurrency assumptions with stress tests.

---

## 12. Testing, Quality Gates, and CI
**Chosen Approach:** Prove it works; prove it stays working

CI requirements:
- Unit tests (pytest) must be deterministic.
- Integration tests run in isolated environments.
- Property-based tests for domain surfaces.
- Fuzzing for untrusted input handlers.
- Static analysis (ruff) blocking.
- Coverage thresholds enforced.
- Documentation builds must pass without warnings.

---

## 13. Logging and Observability
**Chosen Approach:** Structured, stable, privacy-aware

Logging rules:
- Use structured logs everywhere.
- Avoid default Python `print()` in production code.
- Use correlation IDs for distributed systems.
- Sensitive data always redacted.

Metrics and tracing must be opt-in.

---

## 14. Packaging, Distribution, and Supply Chain
**Chosen Approach:** Reproducible, minimal, verifiable

Requirements:
- Use `pyproject.toml` as canonical metadata source.
- All dependencies must be pinned.
- Wheels preferred over source installs.
- No post-install scripts.
- Signed artifacts recommended.
- Clear changelogs with migration notes.

---

## 15. Data Handling and Privacy
**Chosen Approach:** Minimalism + explicit lineage

- Only collect/store what is needed.
- Secrets must never be unencrypted at rest.
- Temporary files/caches must be bounded in scope.
- Exported data must include schema/version markers.

---

## 16. SSE-Python Standard Template (v1.2)
```python
"""============================================================
Synavera Project: [PROJECT / MODULE NAME]
Module: [path/to/file.py]
Etiquette: Synavera Script

