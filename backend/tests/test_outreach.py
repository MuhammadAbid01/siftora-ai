from app.outreach import assemble_body, check_quality
from app.providers import FixtureLanguageModelProvider
from app.schemas import EvidenceItem

FACT = EvidenceItem(
    type="fact",
    claim="Acme has 20 employees.",
    excerpt="Acme has 20 employees.",
    source_url="https://acme.example",
    confidence=0.9,
)
UNKNOWN = EvidenceItem(type="unknown", claim="No contact email was found.")


class TestAssembleBody:
    def test_includes_all_pieces_and_named_signoff(self) -> None:
        body = assemble_body(
            company_name="Acme",
            sender_name="Jamie",
            observation="We noticed your team grew.",
            offer_line="We help with workflow automation.",
            cta="Would you be open to a quick call?",
        )
        assert "Hi Acme team," in body
        assert "We noticed your team grew." in body
        assert "We help with workflow automation." in body
        assert "Would you be open to a quick call?" in body
        assert "Best,\nJamie" in body

    def test_falls_back_to_generic_signoff_without_sender_name(self) -> None:
        body = assemble_body(
            company_name="Acme", sender_name=None, observation="o", offer_line="f", cta="c"
        )
        assert "Best regards" in body


class TestCheckQuality:
    def test_passes_a_clean_grounded_draft(self) -> None:
        body = assemble_body(
            company_name="Acme",
            sender_name="Jamie",
            observation="We noticed your team grew.",
            offer_line="We help with workflow automation.",
            cta="Open to a quick call?",
        )
        ok, reasons = check_quality(body=body, evidence_refs=[0], evidence=[FACT])
        assert ok is True
        assert reasons == []

    def test_fails_when_evidence_refs_is_empty(self) -> None:
        ok, reasons = check_quality(body="A short body.", evidence_refs=[], evidence=[FACT])
        assert ok is False
        assert "ungrounded" in reasons

    def test_fails_when_ref_points_at_an_unknown_item(self) -> None:
        ok, reasons = check_quality(body="A short body.", evidence_refs=[0], evidence=[UNKNOWN])
        assert ok is False
        assert "ungrounded" in reasons

    def test_fails_when_ref_is_out_of_range(self) -> None:
        ok, reasons = check_quality(body="A short body.", evidence_refs=[5], evidence=[FACT])
        assert ok is False
        assert "ungrounded" in reasons

    def test_fails_when_body_is_130_words_or_more(self) -> None:
        long_body = " ".join(["word"] * 130)
        ok, reasons = check_quality(body=long_body, evidence_refs=[0], evidence=[FACT])
        assert ok is False
        assert "too_long" in reasons

    def test_passes_at_129_words(self) -> None:
        body = " ".join(["word"] * 129)
        ok, reasons = check_quality(body=body, evidence_refs=[0], evidence=[FACT])
        assert "too_long" not in reasons

    def test_fails_on_blocklisted_phrase(self) -> None:
        body = "Hi team,\n\nAct now to save big!\n\noffer line\n\ncta\n\nBest regards"
        ok, reasons = check_quality(body=body, evidence_refs=[0], evidence=[FACT])
        assert ok is False
        assert "blocklisted_phrase" in reasons

    def test_can_fail_for_multiple_reasons_at_once(self) -> None:
        long_body = "Act now! " + " ".join(["word"] * 130)
        ok, reasons = check_quality(body=long_body, evidence_refs=[], evidence=[FACT])
        assert ok is False
        assert set(reasons) == {"too_long", "ungrounded", "blocklisted_phrase"}


class TestFixtureDraftOutreach:
    async def test_normal_company_grounds_in_the_first_fact_or_inference(self) -> None:
        provider = FixtureLanguageModelProvider()
        evidence = [UNKNOWN, FACT]

        result = await provider.draft_outreach(
            icp={},
            offer="workflow automation",
            company_name="Acme",
            domain="acme.example",
            evidence=evidence,
            channel="email",
            sender_name=None,
            attempt=0,
        )

        assert result.evidence_refs == [1]
        assert result.observation == FACT.claim
        assert result.subject and result.offer_line and result.cta

    async def test_draft_ungroundable_fixture_company_always_returns_empty_refs(self) -> None:
        provider = FixtureLanguageModelProvider()
        evidence = [
            EvidenceItem(
                type="fact",
                claim="Thinclaim Robotics has 30 employees and is based in Berlin, Germany.",
                excerpt="Thinclaim Robotics has 30 employees.",
                source_url="https://thinclaimrobotics.example",
                confidence=0.9,
            )
        ]

        for attempt in (0, 1):
            result = await provider.draft_outreach(
                icp={},
                offer=None,
                company_name="Thinclaim Robotics",
                domain="thinclaimrobotics.example",
                evidence=evidence,
                channel="email",
                sender_name=None,
                attempt=attempt,
            )
            assert result.evidence_refs == []

    async def test_no_groundable_evidence_returns_empty_refs(self) -> None:
        provider = FixtureLanguageModelProvider()

        result = await provider.draft_outreach(
            icp={},
            offer=None,
            company_name="Acme",
            domain="acme.example",
            evidence=[UNKNOWN],
            channel="email",
            sender_name=None,
            attempt=0,
        )

        assert result.evidence_refs == []
