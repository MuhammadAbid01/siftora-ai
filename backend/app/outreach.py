"""Deterministic outreach assembly and quality checks (plan.md §3, §11).

`LanguageModelProvider.draft_outreach` may only propose an observation, an
offer line, and a call-to-action — this module is the deterministic code
that assembles them into a final email body and enforces the rules
(length, grounding, spam/urgency phrasing) that plan.md requires application
code, not the LLM, to enforce. Mirrors app/scoring.py's "LLM proposes, code
enforces" split.
"""

from app.schemas import EvidenceItem

MAX_WORDS = 130

# A small, fixed, case-insensitive blocklist of spam/false-urgency phrases
# (plan.md §11: "no fake urgency, metrics, or deceptive wording"). This is a
# deterministic heuristic, not a claim of semantic tone analysis — see
# specs/phase-4-outreach.md, Risks.
BLOCKLIST: tuple[str, ...] = (
    "act now",
    "100% free",
    "risk-free",
    "buy now",
    "limited time",
    "guarantee",
    "$$$",
    "no obligation",
    "click here now",
    "urgent",
)


def assemble_body(
    *,
    company_name: str,
    sender_name: str | None,
    observation: str,
    offer_line: str,
    cta: str,
) -> str:
    """Builds the final email body from LLM-proposed pieces with a fixed
    template the LLM never sees or controls — "one observation, one offer,
    one CTA" is structural, not a hope about model compliance.
    """
    greeting = f"Hi {company_name} team,"
    signoff = f"Best,\n{sender_name}" if sender_name else "Best regards"
    return "\n\n".join([greeting, observation, offer_line, cta, signoff])


def check_quality(
    *, body: str, evidence_refs: list[int], evidence: list[EvidenceItem]
) -> tuple[bool, list[str]]:
    """Pure function: same inputs always produce the same (passed, reasons).

    Failure reasons (any number may apply):
      - "too_long": body is 130 words or more (plan.md §11).
      - "ungrounded": evidence_refs is empty, or references an index that's
        out of range or points at an "unknown"-type item (an unknown by
        definition carries no excerpt/source — grounding a claim in it would
        be exactly the invented-evidence behavior plan.md forbids).
      - "blocklisted_phrase": the body contains a spam/false-urgency phrase.
    """
    reasons: list[str] = []

    if len(body.split()) >= MAX_WORDS:
        reasons.append("too_long")

    if not evidence_refs:
        reasons.append("ungrounded")
    else:
        for idx in evidence_refs:
            if idx < 0 or idx >= len(evidence) or evidence[idx].type == "unknown":
                reasons.append("ungrounded")
                break

    lowered = body.lower()
    if any(phrase in lowered for phrase in BLOCKLIST):
        reasons.append("blocklisted_phrase")

    return (len(reasons) == 0, reasons)
