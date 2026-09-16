"""Runs the six live-endpoint evaluation categories against whichever
providers are currently configured (fixture by default — see
specs/phase-5-hardening.md, Non-goals, for why this session's own
verification run forces fixture mode regardless of `backend/.env`).
"""

from app.agent import has_sufficient_evidence
from app.config import get_settings
from app.evals import datasets
from app.outreach import assemble_body, check_quality
from app.providers import get_language_model_provider, normalize_domain
from app.schemas import EvalCaseResult, EvalCategoryResult, EvalReport
from app.scoring import compute_score


def _category_result(category: str, cases: list[EvalCaseResult]) -> EvalCategoryResult:
    total = len(cases)
    passed = sum(1 for c in cases if c.passed)
    return EvalCategoryResult(
        category=category,
        total=total,
        passed=passed,
        pass_rate=(passed / total) if total else 0.0,
        cases=cases,
    )


async def run_campaign_parsing() -> EvalCategoryResult:
    provider = get_language_model_provider()
    cases: list[EvalCaseResult] = []
    for case in datasets.CAMPAIGN_PARSING_CASES:
        result = await provider.generate_campaign_plan(
            brief=case["brief"], offer=case["offer"], target_lead_count=20
        )
        icp = result.icp
        ok = (
            set(icp.industries) == case["expect_industries"]
            and set(icp.locations) == case["expect_locations"]
            and icp.company_size_min == case["expect_size_min"]
            and icp.company_size_max == case["expect_size_max"]
            and (not icp.industries or not icp.locations) == case["expect_incomplete"]
        )
        cases.append(
            EvalCaseResult(
                name=case["name"],
                passed=ok,
                detail=None
                if ok
                else f"industries={icp.industries} locations={icp.locations} "
                f"size=({icp.company_size_min},{icp.company_size_max})",
            )
        )
    return _category_result("campaign_parsing", cases)


async def run_planning() -> EvalCategoryResult:
    provider = get_language_model_provider()
    cases: list[EvalCaseResult] = []
    for case in datasets.PLANNING_CASES:
        result = await provider.generate_campaign_plan(
            brief=case["brief"], offer=None, target_lead_count=20
        )
        incomplete = not result.icp.industries or not result.icp.locations
        query_count_ok = len(result.search_plan) == case["expect_query_count"]
        shape_ok = all(" in " in q.query and q.rationale.strip() for q in result.search_plan)
        ok = query_count_ok and shape_ok and incomplete == case["expect_incomplete"]
        cases.append(
            EvalCaseResult(
                name=case["name"],
                passed=ok,
                detail=None
                if ok
                else f"got {len(result.search_plan)} queries: "
                f"{[q.query for q in result.search_plan]}",
            )
        )
    return _category_result("planning", cases)


def run_candidate_validation() -> EvalCategoryResult:
    cases = [
        EvalCaseResult(
            name=case["name"],
            passed=has_sufficient_evidence(case["evidence"]) == case["expected"],
        )
        for case in datasets.CANDIDATE_VALIDATION_CASES
    ]
    return _category_result("candidate_validation", cases)


def run_deduplication() -> EvalCategoryResult:
    cases = []
    for case in datasets.DEDUPLICATION_CASES:
        actual = normalize_domain(case["input"])
        ok = actual == case["expected"]
        cases.append(
            EvalCaseResult(name=case["name"], passed=ok, detail=None if ok else f"got {actual!r}")
        )
    return _category_result("deduplication", cases)


def run_scoring() -> EvalCategoryResult:
    cases = []
    for case in datasets.SCORING_CASES:
        result = compute_score(case["signals"], case["weights"])
        ok = result.total == case["expected"]
        cases.append(
            EvalCaseResult(
                name=case["name"], passed=ok, detail=None if ok else f"got {result.total}"
            )
        )
    return _category_result("scoring", cases)


def run_outreach_grounding() -> EvalCategoryResult:
    cases = []
    for case in datasets.OUTREACH_GROUNDING_CASES:
        passed_check, reasons = check_quality(
            body=case["body"], evidence_refs=case["evidence_refs"], evidence=case["evidence"]
        )
        ok = passed_check == case["expected_passed"]
        cases.append(
            EvalCaseResult(
                name=case["name"], passed=ok, detail=None if ok else f"reasons={reasons}"
            )
        )
    return _category_result("outreach_grounding", cases)


async def run_all() -> EvalReport:
    settings = get_settings()
    categories = [
        await run_campaign_parsing(),
        await run_planning(),
        run_candidate_validation(),
        run_deduplication(),
        run_scoring(),
        run_outreach_grounding(),
    ]
    total_cases = sum(c.total for c in categories)
    total_passed = sum(c.passed for c in categories)
    return EvalReport(
        categories=categories,
        overall_pass_rate=(total_passed / total_cases) if total_cases else 0.0,
        provider_mode={
            "llm": settings.llm_provider,
            "search": settings.search_provider,
            "extraction": settings.extraction_provider,
        },
    )


__all__ = [
    "assemble_body",
    "run_all",
    "run_campaign_parsing",
    "run_candidate_validation",
    "run_deduplication",
    "run_outreach_grounding",
    "run_planning",
    "run_scoring",
]
