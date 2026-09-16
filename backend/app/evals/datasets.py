"""Fixed evaluation cases (plan.md §19's minimum counts). Plain Python data
— a small, version-controlled, type-checked dataset has no need for a
separate JSON-parsing/validation layer (plan.md §4's "avoid premature
abstraction" applies to eval data too).

Expected values for the scoring cases were computed once, independently of
`app/scoring.py`, via a standalone script (not committed) applying the same
documented formula (`plan.md` §10: `points = round(rating * weight, 2)`,
summed and rounded) — they are frozen literals here, not re-derived from the
function under test, so a real regression in `compute_score` would actually
be caught.
"""

from app.schemas import EvidenceItem

# --- Campaign parsing (10 cases; drives generate_campaign_plan's ICP output) --

CAMPAIGN_PARSING_CASES: list[dict] = [
    {
        "name": "animation_dubai",
        "brief": "Find animation studios in Dubai, UAE with 5-50 employees.",
        "offer": None,
        "expect_incomplete": False,
        "expect_industries": {"Animation studios"},
        "expect_locations": {"Dubai, UAE", "United Arab Emirates"},
        "expect_size_min": 5,
        "expect_size_max": 50,
    },
    {
        "name": "saas_san_francisco",
        "brief": "Find SaaS companies in San Francisco.",
        "offer": "workflow automation",
        "expect_incomplete": False,
        "expect_industries": {"SaaS companies"},
        "expect_locations": {"San Francisco, USA"},
        "expect_size_min": None,
        "expect_size_max": None,
    },
    {
        "name": "law_firms_london",
        "brief": "Find law firms in London, United Kingdom.",
        "offer": None,
        "expect_incomplete": False,
        "expect_industries": {"Law firms"},
        "expect_locations": {"London, UK", "United Kingdom"},
        "expect_size_min": None,
        "expect_size_max": None,
    },
    {
        "name": "vague_brief",
        "brief": "Find some good companies that might want our product.",
        "offer": None,
        "expect_incomplete": True,
        "expect_industries": set(),
        "expect_locations": set(),
        "expect_size_min": None,
        "expect_size_max": None,
    },
    {
        "name": "marketing_toronto_with_size",
        "brief": "Find marketing agencies in Toronto, Canada with 10-50 employees.",
        "offer": None,
        "expect_incomplete": False,
        "expect_industries": {"Marketing agencies", "Agencies"},
        "expect_locations": {"Toronto, Canada", "Canada"},
        "expect_size_min": 10,
        "expect_size_max": 50,
    },
    {
        "name": "no_keywords",
        "brief": "We want more customers for our business this quarter.",
        "offer": None,
        "expect_incomplete": True,
        "expect_industries": set(),
        "expect_locations": set(),
        "expect_size_min": None,
        "expect_size_max": None,
    },
    {
        "name": "consulting_singapore",
        "brief": "Find consulting firms in Singapore.",
        "offer": None,
        "expect_incomplete": False,
        "expect_industries": {"Consulting firms"},
        "expect_locations": {"Singapore"},
        "expect_size_min": None,
        "expect_size_max": None,
    },
    {
        "name": "ecommerce_berlin",
        "brief": "Find e-commerce companies in Berlin, Germany.",
        "offer": None,
        "expect_incomplete": False,
        "expect_industries": {"Ecommerce companies"},
        "expect_locations": {"Berlin, Germany"},
        "expect_size_min": None,
        "expect_size_max": None,
    },
    {
        "name": "restaurants_retail_us",
        "brief": "Find restaurants and retail businesses in the United States.",
        "offer": None,
        "expect_incomplete": False,
        "expect_industries": {"Restaurants", "Retail businesses"},
        "expect_locations": {"United States"},
        "expect_size_min": None,
        "expect_size_max": None,
    },
    {
        "name": "manufacturing_canada",
        "brief": "Find manufacturing companies in Canada.",
        "offer": None,
        "expect_incomplete": False,
        "expect_industries": {"Manufacturing companies"},
        "expect_locations": {"Canada"},
        "expect_size_min": None,
        "expect_size_max": None,
    },
]

# --- Planning (10 cases; drives generate_campaign_plan's search_plan output) --

PLANNING_CASES: list[dict] = [
    {
        "name": "single_industry_single_location",
        "brief": "Find law firms in New York.",
        "expect_query_count": 1,
        "expect_incomplete": False,
    },
    {
        "name": "single_industry_two_locations",
        "brief": "Find law firms in London, United Kingdom.",
        "expect_query_count": 2,  # "London, UK" AND "United Kingdom" both match
        "expect_incomplete": False,
    },
    {
        "name": "two_industries_one_location",
        "brief": "Find marketing agencies in Singapore.",
        "expect_query_count": 2,  # "Marketing agencies" AND "Agencies" both match
        "expect_incomplete": False,
    },
    {
        "name": "vague_brief_no_plan",
        "brief": "We want more customers.",
        "expect_query_count": 0,
        "expect_incomplete": True,
    },
    {
        "name": "consulting_singapore",
        "brief": "Find consulting firms in Singapore.",
        "expect_query_count": 1,
        "expect_incomplete": False,
    },
    {
        "name": "restaurants_and_retail_us",
        "brief": "Find restaurants and retail businesses in the United States.",
        "expect_query_count": 2,  # two industries, one location
        "expect_incomplete": False,
    },
    {
        "name": "ecommerce_berlin",
        "brief": "Find e-commerce companies in Berlin, Germany.",
        "expect_query_count": 1,
        "expect_incomplete": False,
    },
    {
        "name": "manufacturing_canada",
        "brief": "Find manufacturing companies in Canada.",
        "expect_query_count": 1,
        "expect_incomplete": False,
    },
    {
        "name": "saas_san_francisco",
        "brief": "Find SaaS companies in San Francisco.",
        "expect_query_count": 1,
        "expect_incomplete": False,
    },
    {
        "name": "no_keywords_at_all",
        "brief": "asdf qwer zxcv.",
        "expect_query_count": 0,
        "expect_incomplete": True,
    },
]

# --- Candidate validation (20 cases; drives has_sufficient_evidence) --------


def _fact() -> EvidenceItem:
    return EvidenceItem(
        type="fact", claim="A fact.", excerpt="excerpt", source_url="https://example.com"
    )


def _inference() -> EvidenceItem:
    return EvidenceItem(
        type="inference", claim="An inference.", excerpt="excerpt", source_url="https://example.com"
    )


def _unknown() -> EvidenceItem:
    return EvidenceItem(type="unknown", claim="An unknown.")


CANDIDATE_VALIDATION_CASES: list[dict] = [
    {"name": "empty_evidence", "evidence": [], "expected": False},
    {"name": "single_fact", "evidence": [_fact()], "expected": True},
    {"name": "single_inference_only", "evidence": [_inference()], "expected": False},
    {"name": "single_unknown_only", "evidence": [_unknown()], "expected": False},
    {"name": "fact_and_unknown", "evidence": [_fact(), _unknown()], "expected": True},
    {"name": "inference_and_unknown", "evidence": [_inference(), _unknown()], "expected": False},
    {"name": "two_facts", "evidence": [_fact(), _fact()], "expected": True},
    {"name": "two_inferences", "evidence": [_inference(), _inference()], "expected": False},
    {
        "name": "fact_inference_unknown",
        "evidence": [_fact(), _inference(), _unknown()],
        "expected": True,
    },
    {"name": "five_unknowns", "evidence": [_unknown() for _ in range(5)], "expected": False},
    {"name": "five_inferences", "evidence": [_inference() for _ in range(5)], "expected": False},
    {
        "name": "one_fact_among_many_unknowns",
        "evidence": [_inference(), _unknown(), _fact(), _unknown()],
        "expected": True,
    },
    {
        "name": "fact_last_in_list",
        "evidence": [_inference(), _unknown(), _inference(), _fact()],
        "expected": True,
    },
    {
        "name": "fact_first_in_list",
        "evidence": [_fact(), _inference(), _unknown()],
        "expected": True,
    },
    {"name": "ten_facts", "evidence": [_fact() for _ in range(10)], "expected": True},
    {
        "name": "many_inferences_and_unknowns_no_fact",
        "evidence": [_inference(), _inference(), _unknown(), _unknown()],
        "expected": False,
    },
    {
        "name": "large_mixed_with_one_fact",
        "evidence": [_unknown() for _ in range(4)] + [_fact()],
        "expected": True,
    },
    {
        "name": "large_mixed_without_fact",
        "evidence": [_unknown() for _ in range(4)] + [_inference()],
        "expected": False,
    },
    {
        "name": "inference_and_fact_together",
        "evidence": [_inference(), _fact()],
        "expected": True,
    },
    {
        "name": "only_unknowns_large",
        "evidence": [_unknown() for _ in range(8)],
        "expected": False,
    },
]

# --- Deduplication (15 cases; drives normalize_domain) ----------------------

DEDUPLICATION_CASES: list[dict] = [
    {"name": "bare_domain", "input": "example.com", "expected": "example.com"},
    {"name": "with_www", "input": "www.example.com", "expected": "example.com"},
    {"name": "with_https", "input": "https://example.com", "expected": "example.com"},
    {"name": "with_http", "input": "http://example.com", "expected": "example.com"},
    {
        "name": "with_https_and_www",
        "input": "https://www.example.com",
        "expected": "example.com",
    },
    {"name": "with_path", "input": "https://example.com/about", "expected": "example.com"},
    {
        "name": "with_path_and_www_and_query",
        "input": "https://www.example.com/pricing?x=1",
        "expected": "example.com",
    },
    {"name": "mixed_case", "input": "HTTPS://WWW.Example.COM", "expected": "example.com"},
    {
        "name": "subdomain_preserved",
        "input": "https://blog.example.com",
        "expected": "blog.example.com",
    },
    {"name": "trailing_slash", "input": "example.com/", "expected": "example.com"},
    {"name": "different_tld", "input": "example.co", "expected": "example.co"},
    {
        "name": "www_only_no_scheme",
        "input": "www.example.com/path",
        "expected": "example.com",
    },
    {
        "name": "hyphenated_domain",
        "input": "https://my-company.example",
        "expected": "my-company.example",
    },
    {
        "name": "port_number_preserved",
        "input": "https://example.com:8080/page",
        "expected": "example.com:8080",
    },
    {"name": "uppercase_www", "input": "WWW.EXAMPLE.COM", "expected": "example.com"},
]

# --- Scoring (20 cases; drives compute_score) -------------------------------

_DEFAULT_WEIGHTS = {
    "industry_fit": 20,
    "geography_fit": 10,
    "company_size_fit": 10,
    "pain_point_evidence": 20,
    "buying_signal": 15,
    "contact_relevance": 10,
    "recency": 10,
    "evidence_completeness": 5,
}

_CONTACT_HEAVY_WEIGHTS = {
    "industry_fit": 5,
    "geography_fit": 5,
    "company_size_fit": 5,
    "pain_point_evidence": 5,
    "buying_signal": 5,
    "contact_relevance": 65,
    "recency": 5,
    "evidence_completeness": 5,
}

_INDUSTRY_ONLY_WEIGHTS = {
    "industry_fit": 100,
    "geography_fit": 0,
    "company_size_fit": 0,
    "pain_point_evidence": 0,
    "buying_signal": 0,
    "contact_relevance": 0,
    "recency": 0,
    "evidence_completeness": 0,
}

_CRITERIA_ORDER = (
    "industry_fit",
    "geography_fit",
    "company_size_fit",
    "pain_point_evidence",
    "buying_signal",
    "contact_relevance",
    "recency",
    "evidence_completeness",
)


def _signals(*values: float) -> dict[str, float]:
    return dict(zip(_CRITERIA_ORDER, values, strict=True))


SCORING_CASES: list[dict] = [
    {
        "name": "all_ones",
        "signals": _signals(*([1.0] * 8)),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 100,
    },
    {
        "name": "all_zeros",
        "signals": _signals(*([0.0] * 8)),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 0,
    },
    {
        "name": "all_halves",
        "signals": _signals(*([0.5] * 8)),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 50,
    },
    {
        "name": "strong_qualified",
        "signals": _signals(1.0, 1.0, 1.0, 1.0, 0.8, 0.5, 1.0, 1.0),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 92,
    },
    {
        "name": "moderate_needs_review",
        "signals": _signals(0.8, 1.0, 0.5, 0.5, 0.5, 0.3, 0.5, 0.6),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 60,
    },
    {
        "name": "weak_rejected",
        "signals": _signals(0.1, 0.0, 0.5, 0.2, 0.2, 0.2, 0.3, 0.4),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 21,
    },
    {
        "name": "industry_only",
        "signals": _signals(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 20,
    },
    {
        "name": "geography_only",
        "signals": _signals(0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 10,
    },
    {
        "name": "pain_point_only",
        "signals": _signals(0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 20,
    },
    {
        "name": "three_quarters_all",
        "signals": _signals(*([0.75] * 8)),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 75,
    },
    {
        "name": "one_third_all",
        "signals": _signals(*([0.33] * 8)),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 33,
    },
    {
        "name": "nine_tenths_all",
        "signals": _signals(*([0.9] * 8)),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 90,
    },
    {
        "name": "zigzag_signals",
        "signals": _signals(0.6, 0.4, 0.2, 0.8, 0.6, 0.4, 0.2, 0.8),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 53,
    },
    {
        "name": "alternating_full_half",
        "signals": _signals(1.0, 0.5, 1.0, 0.5, 1.0, 0.5, 1.0, 0.5),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 78,
    },
    {
        "name": "engagement_only",
        "signals": _signals(0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 40,
    },
    {
        "name": "fit_only_no_engagement",
        "signals": _signals(1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        "weights": _DEFAULT_WEIGHTS,
        "expected": 40,
    },
    {
        "name": "contact_heavy_weights_moderate_signals",
        "signals": _signals(0.8, 1.0, 0.5, 0.5, 0.5, 0.3, 0.5, 0.6),
        "weights": _CONTACT_HEAVY_WEIGHTS,
        "expected": 42,
    },
    {
        "name": "industry_only_weights_moderate_signals",
        "signals": _signals(0.8, 1.0, 0.5, 0.5, 0.5, 0.3, 0.5, 0.6),
        "weights": _INDUSTRY_ONLY_WEIGHTS,
        "expected": 80,
    },
    {
        "name": "industry_only_weights_mixed_signals",
        "signals": _signals(0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.9),
        "weights": _INDUSTRY_ONLY_WEIGHTS,
        "expected": 70,
    },
    {
        "name": "all_ones_any_weights",
        "signals": _signals(*([1.0] * 8)),
        "weights": _CONTACT_HEAVY_WEIGHTS,
        "expected": 100,
    },
]

# --- Outreach grounding (20 cases; drives check_quality / assemble_body) ---

_GROUNDING_FACT = EvidenceItem(
    type="fact",
    claim="Acme has 20 employees.",
    excerpt="Acme has 20 employees.",
    source_url="https://acme.example",
    confidence=0.9,
)
_GROUNDING_INFERENCE = EvidenceItem(
    type="inference",
    claim="Acme is likely hiring.",
    excerpt="recently posted open roles",
    source_url="https://acme.example",
    confidence=0.6,
)
_GROUNDING_UNKNOWN = EvidenceItem(type="unknown", claim="No pricing was found.")

_CLEAN_BODY = (
    "Hi Acme team,\n\nWe noticed your team recently grew.\n\nWe help teams like "
    "yours with workflow automation.\n\nWould you be open to a quick call?\n\n"
    "Best regards"
)
_LONG_BODY = " ".join(["word"] * 140)
_SPAM_BODY = (
    "Hi Acme team,\n\nAct now to save big with our 100% free offer!\n\n"
    "Limited time only.\n\nBest regards"
)

OUTREACH_GROUNDING_CASES: list[dict] = [
    {
        "name": "clean_grounded_short",
        "body": _CLEAN_BODY,
        "evidence_refs": [0],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": True,
    },
    {
        "name": "grounded_via_inference",
        "body": _CLEAN_BODY,
        "evidence_refs": [0],
        "evidence": [_GROUNDING_INFERENCE],
        "expected_passed": True,
    },
    {
        "name": "grounded_multiple_refs",
        "body": _CLEAN_BODY,
        "evidence_refs": [0, 1],
        "evidence": [_GROUNDING_FACT, _GROUNDING_INFERENCE],
        "expected_passed": True,
    },
    {
        "name": "empty_refs_ungrounded",
        "body": _CLEAN_BODY,
        "evidence_refs": [],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": False,
    },
    {
        "name": "ref_points_at_unknown",
        "body": _CLEAN_BODY,
        "evidence_refs": [0],
        "evidence": [_GROUNDING_UNKNOWN],
        "expected_passed": False,
    },
    {
        "name": "ref_out_of_range",
        "body": _CLEAN_BODY,
        "evidence_refs": [5],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": False,
    },
    {
        "name": "negative_ref_out_of_range",
        "body": _CLEAN_BODY,
        "evidence_refs": [-1],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": False,
    },
    {
        "name": "too_long_body",
        "body": _LONG_BODY,
        "evidence_refs": [0],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": False,
    },
    {
        "name": "blocklisted_phrase",
        "body": _SPAM_BODY,
        "evidence_refs": [0],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": False,
    },
    {
        "name": "everything_wrong_at_once",
        "body": _LONG_BODY + " act now 100% free",
        "evidence_refs": [],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": False,
    },
    {
        "name": "one_ref_valid_one_invalid",
        "body": _CLEAN_BODY,
        "evidence_refs": [0, 9],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": False,
    },
    {
        "name": "mixed_valid_and_unknown_refs",
        "body": _CLEAN_BODY,
        "evidence_refs": [0, 1],
        "evidence": [_GROUNDING_FACT, _GROUNDING_UNKNOWN],
        "expected_passed": False,
    },
    {
        "name": "clean_body_no_blocklist_variant",
        "body": (
            "Hi Acme team,\n\nWe saw your latest product launch.\n\nWe'd love to "
            "help streamline that workflow.\n\nOpen to a 15-minute chat?\n\nBest,\nJamie"
        ),
        "evidence_refs": [0],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": True,
    },
    {
        "name": "risk_free_phrase",
        "body": "Hi team,\n\nTry it risk-free today.\n\noffer\n\ncta\n\nBest regards",
        "evidence_refs": [0],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": False,
    },
    {
        "name": "guarantee_phrase",
        "body": "Hi team,\n\nWe guarantee results.\n\noffer\n\ncta\n\nBest regards",
        "evidence_refs": [0],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": False,
    },
    {
        "name": "no_obligation_phrase",
        "body": "Hi team,\n\nNo obligation to sign up.\n\noffer\n\ncta\n\nBest regards",
        "evidence_refs": [0],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": False,
    },
    {
        "name": "exactly_129_words_passes_length",
        "body": " ".join(["word"] * 129),
        "evidence_refs": [0],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": True,
    },
    {
        "name": "exactly_130_words_fails_length",
        "body": " ".join(["word"] * 130),
        "evidence_refs": [0],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": False,
    },
    {
        "name": "dollar_sign_spam",
        "body": "Hi team,\n\nEarn $$$ fast.\n\noffer\n\ncta\n\nBest regards",
        "evidence_refs": [0],
        "evidence": [_GROUNDING_FACT],
        "expected_passed": False,
    },
    {
        "name": "grounded_second_of_two_items",
        "body": _CLEAN_BODY,
        "evidence_refs": [1],
        "evidence": [_GROUNDING_UNKNOWN, _GROUNDING_FACT],
        "expected_passed": True,
    },
]
