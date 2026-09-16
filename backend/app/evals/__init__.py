"""Deterministic evaluation harness (plan.md §19/§20; specs/phase-5-hardening.md).

Six of `plan.md`'s seven fixed-case categories live here (campaign-parsing,
planning, candidate-validation, deduplication, scoring, outreach-grounding)
— each exercises the real production function it evaluates, never a
reimplementation. The seventh, failure/recovery, needs the full database-
backed research graph and is verified in `tests/test_evals.py` instead
(see this package's parent spec, Non-goals, for why).
"""
