"""Deterministic lead scoring (plan.md §10).

Pure functions, no I/O: given the same signals and weights, `compute_score`
always returns the same result. The LLM produces `CriterionSignals` at
analysis time (see app/providers.py); nothing here calls a model.
"""

from app.schemas import CRITERIA_FIELDS, ScoreBreakdownItem, ScoreThresholds

CriterionRatings = dict[str, float]


class ScoreResult:
    __slots__ = ("total", "breakdown")

    def __init__(self, total: int, breakdown: list[ScoreBreakdownItem]) -> None:
        self.total = total
        self.breakdown = breakdown


def compute_score(signals: CriterionRatings, weights: dict[str, int]) -> ScoreResult:
    breakdown: list[ScoreBreakdownItem] = []
    total = 0.0

    for criterion in CRITERIA_FIELDS:
        rating = signals[criterion]
        weight = weights[criterion]
        points = round(rating * weight, 2)
        total += points
        breakdown.append(
            ScoreBreakdownItem(criterion=criterion, rating=rating, weight=weight, points=points)  # type: ignore[arg-type]
        )

    return ScoreResult(total=round(total), breakdown=breakdown)


def decide_qualification(score: int, thresholds: ScoreThresholds) -> str:
    if score >= thresholds.qualified_min:
        return "qualified"
    if score >= thresholds.needs_review_min:
        return "needs_review"
    return "rejected"
