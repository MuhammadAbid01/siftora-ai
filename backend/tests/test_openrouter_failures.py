"""The OpenRouter response shapes that made "Generate plan" fail opaquely.

OpenRouter reports upstream problems (rate limits, provider timeouts,
unavailable models) as **HTTP 200 with an `{"error": ...}` body and no
`choices` key**, so `raise_for_status()` passes and indexing `choices`
raised a `KeyError` that reached the user as a bare "response could not be
parsed". Reasoning models add two more shapes: a null `content` (which made
`json.loads(None)` raise an *uncaught* `TypeError`) and JSON wrapped in
prose or markdown fences.
"""

import json as json_lib

import httpx
import pytest

from app.providers import (
    LLMOutputError,
    LLMUnavailableError,
    OpenRouterLanguageModelProvider,
    _coerce_plan_payload,
)
from app.schemas import PlanExtraction

VALID_PLAN = {
    "icp": {"industries": ["Design agencies"], "locations": ["Dubai, UAE"]},
    "search_plan": [{"query": "design agencies in Dubai", "rationale": "r"}],
}


class _Response:
    """The parts of `httpx.Response` the adapter actually reads."""

    def __init__(self, text: str = "", *, status_code: int = 200, payload: dict | None = None):
        self.text = text
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        if self._payload is not None:
            return self._payload
        return {"choices": [{"message": {"content": self.text}}]}


def _provider() -> OpenRouterLanguageModelProvider:
    return OpenRouterLanguageModelProvider(api_key="fake-key", model="fake-model")


def _patch(monkeypatch: pytest.MonkeyPatch, response: object) -> None:
    async def fake_post(self: httpx.AsyncClient, url: str, json: dict | None = None, **_kw):
        return response

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)


async def _generate() -> PlanExtraction:
    return await _provider().generate_campaign_plan(
        brief="Find design agencies in Dubai.", offer=None, target_lead_count=10
    )


class TestFailureModes:
    async def test_error_envelope_on_http_200_is_reported_as_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch(
            monkeypatch,
            _Response(payload={"error": {"message": "A Timeout Occurred", "code": 504}}),
        )

        with pytest.raises(LLMUnavailableError) as exc_info:
            await _generate()

        # The real cause must reach the caller, not be flattened away.
        assert "A Timeout Occurred" in str(exc_info.value)

    async def test_missing_choices_is_reported_as_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch(monkeypatch, _Response(payload={}))
        with pytest.raises(LLMUnavailableError):
            await _generate()

    async def test_null_content_does_not_raise_an_uncaught_type_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch(
            monkeypatch,
            _Response(
                payload={"choices": [{"message": {"content": None}, "finish_reason": "length"}]}
            ),
        )

        with pytest.raises(LLMOutputError) as exc_info:
            await _generate()
        assert "empty completion" in str(exc_info.value)

    async def test_a_timeout_produces_a_non_empty_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_post(self: httpx.AsyncClient, url: str, json: dict | None = None, **_kw):
            raise httpx.ReadTimeout("")

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        with pytest.raises(LLMUnavailableError) as exc_info:
            await _generate()
        # `str(httpx.ReadTimeout(""))` is "" — that emptiness must not be
        # what the user is shown.
        assert "did not respond within" in str(exc_info.value)

    async def test_http_error_status_is_reported_as_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch(monkeypatch, _Response("rate limited", status_code=429))
        with pytest.raises(LLMUnavailableError) as exc_info:
            await _generate()
        assert "429" in str(exc_info.value)

    async def test_reasoning_field_is_used_when_content_is_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch(
            monkeypatch,
            _Response(
                payload={
                    "choices": [
                        {"message": {"content": "", "reasoning": json_lib.dumps(VALID_PLAN)}}
                    ]
                }
            ),
        )
        assert (await _generate()).icp.industries == ["Design agencies"]

    async def test_json_wrapped_in_markdown_fences_is_recovered(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fenced = f"Here is the plan:\n```json\n{json_lib.dumps(VALID_PLAN)}\n```\nHope that helps!"
        _patch(monkeypatch, _Response(fenced))
        assert (await _generate()).icp.locations == ["Dubai, UAE"]


class TestRepairRetry:
    async def test_invalid_output_is_repaired_on_a_second_attempt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Drafting has no shape-coercion layer, so a missing required field
        # is exactly the case the repair prompt exists for.
        calls: list[str] = []
        valid_draft = {
            "subject": "s",
            "observation": "o",
            "offer_line": "f",
            "cta": "c",
            "evidence_refs": [],
        }

        async def fake_post(self: httpx.AsyncClient, url: str, json: dict | None = None, **_kw):
            calls.append(json["messages"][0]["content"])
            if len(calls) == 1:
                incomplete = {k: v for k, v in valid_draft.items() if k != "cta"}
                return _Response(json_lib.dumps(incomplete))
            return _Response(json_lib.dumps(valid_draft))

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        result = await _provider().draft_outreach(
            icp={},
            offer=None,
            company_name="Acme",
            domain="acme.example",
            evidence=[],
            channel="email",
            sender_name=None,
        )

        assert result.cta == "c"
        assert len(calls) == 2
        # The repair prompt shows the model its own output and the error.
        assert "could not be used" in calls[1]

    async def test_a_persistently_invalid_output_fails_clearly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch(monkeypatch, _Response(json_lib.dumps({"subject": "s"})))

        with pytest.raises(LLMOutputError) as exc_info:
            await _provider().draft_outreach(
                icp={},
                offer=None,
                company_name="Acme",
                domain="acme.example",
                evidence=[],
                channel="email",
                sender_name=None,
            )
        assert "repair attempt" in str(exc_info.value)

    async def test_a_provider_failure_is_not_repaired(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[int] = []

        async def fake_post(self: httpx.AsyncClient, url: str, json: dict | None = None, **_kw):
            calls.append(1)
            return _Response(payload={"error": {"message": "rate limited", "code": 429}})

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

        with pytest.raises(LLMUnavailableError):
            await _generate()
        # There is no output to repair, so no second call is wasted.
        assert len(calls) == 1


class TestPlanPayloadCoercion:
    """Shape drift that used to fail `extra="forbid"` validation outright."""

    def test_unknown_keys_are_dropped_rather_than_failing_validation(self) -> None:
        coerced = _coerce_plan_payload(
            {
                "icp": {
                    "industries": ["Animation studios"],
                    "locations": ["Dubai, UAE"],
                    "reasoning": "because the brief said so",
                    "confidence": 0.9,
                },
                "search_plan": [],
                "notes": "extra commentary",
            }
        )
        assert PlanExtraction.model_validate(coerced).icp.industries == ["Animation studios"]

    def test_scalars_are_widened_to_lists(self) -> None:
        coerced = _coerce_plan_payload(
            {"icp": {"industry": "Animation studios", "location": "Dubai, UAE"}}
        )
        plan = PlanExtraction.model_validate(coerced)
        assert plan.icp.industries == ["Animation studios"]
        assert plan.icp.locations == ["Dubai, UAE"]

    def test_a_scalar_string_is_kept_whole_not_split_on_commas(self) -> None:
        # "Dubai, UAE" is ONE location. Splitting scalars on commas would
        # turn one correct value into two wrong ones.
        coerced = _coerce_plan_payload({"icp": {"locations": "Dubai, UAE"}})
        assert PlanExtraction.model_validate(coerced).icp.locations == ["Dubai, UAE"]

    def test_a_list_is_preserved_entry_by_entry(self) -> None:
        coerced = _coerce_plan_payload(
            {"icp": {"industries": ["Animation studios", "Design agencies"]}}
        )
        assert PlanExtraction.model_validate(coerced).icp.industries == [
            "Animation studios",
            "Design agencies",
        ]

    def test_company_size_expressed_as_a_range_string(self) -> None:
        coerced = _coerce_plan_payload(
            {"icp": {"industries": ["x"], "locations": ["y"], "company_size": "5-50 employees"}}
        )
        plan = PlanExtraction.model_validate(coerced)
        assert (plan.icp.company_size_min, plan.icp.company_size_max) == (5, 50)

    def test_company_size_expressed_as_an_object(self) -> None:
        coerced = _coerce_plan_payload(
            {"icp": {"industries": ["x"], "company_size": {"min": 5, "max": 50}}}
        )
        plan = PlanExtraction.model_validate(coerced)
        assert (plan.icp.company_size_min, plan.icp.company_size_max) == (5, 50)

    def test_a_reversed_size_range_is_swapped_not_rejected(self) -> None:
        coerced = _coerce_plan_payload(
            {"icp": {"company_size_min": 50, "company_size_max": 5, "industries": ["x"]}}
        )
        plan = PlanExtraction.model_validate(coerced)
        assert (plan.icp.company_size_min, plan.icp.company_size_max) == (5, 50)

    def test_icp_fields_returned_at_the_top_level_are_still_found(self) -> None:
        coerced = _coerce_plan_payload(
            {"industries": ["Animation studios"], "locations": ["Dubai, UAE"], "search_plan": []}
        )
        assert PlanExtraction.model_validate(coerced).icp.locations == ["Dubai, UAE"]

    def test_search_plan_as_plain_strings_gets_a_default_rationale(self) -> None:
        coerced = _coerce_plan_payload(
            {"icp": {"industries": ["x"]}, "search_plan": ["animation studios in Dubai"]}
        )
        plan = PlanExtraction.model_validate(coerced)
        assert plan.search_plan[0].query == "animation studios in Dubai"
        assert plan.search_plan[0].rationale

    def test_missing_fields_stay_empty_rather_than_being_invented(self) -> None:
        coerced = _coerce_plan_payload({"icp": {"industries": ["Animation studios"]}})
        plan = PlanExtraction.model_validate(coerced)
        assert plan.icp.locations == []
        assert plan.icp.company_size_min is None


class TestLatencyAndShapeGuards:
    """Guards for the two things that made planning slow, then wrong.

    Reasoning tokens dominated latency (3,613 of 3,634 completion tokens on
    a measured call, ~105s vs ~17s), and once reasoning was switched off the
    model started echoing the JSON Schema it was shown instead of an
    instance of it.
    """

    async def test_reasoning_is_disabled_in_the_request_by_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict = {}

        async def fake_post(self: httpx.AsyncClient, url: str, json: dict | None = None, **_kw):
            captured["body"] = json
            return _Response(json_lib.dumps(VALID_PLAN))

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
        await _generate()

        assert captured["body"]["reasoning"] == {"enabled": False}

    async def test_reasoning_can_be_re_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict = {}

        async def fake_post(self: httpx.AsyncClient, url: str, json: dict | None = None, **_kw):
            captured["body"] = json
            return _Response(json_lib.dumps(VALID_PLAN))

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
        provider = OpenRouterLanguageModelProvider(api_key="k", model="m", disable_reasoning=False)
        await provider.generate_campaign_plan(brief="b", offer=None, target_lead_count=1)

        assert "reasoning" not in captured["body"]

    async def test_the_prompt_shows_a_value_skeleton_not_a_json_schema(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict = {}

        async def fake_post(self: httpx.AsyncClient, url: str, json: dict | None = None, **_kw):
            captured["prompt"] = json["messages"][0]["content"]
            return _Response(json_lib.dumps(VALID_PLAN))

        monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
        await _generate()

        prompt = captured["prompt"]
        # Showing `{"type": "object", "properties": ...}` is what taught the
        # model to answer with a schema-shaped envelope.
        assert '"properties"' not in prompt
        assert '"industries": []' in prompt

    async def test_a_schema_shaped_answer_is_unwrapped_not_read_as_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The real observed failure: the model extracted everything
        correctly but nested it under a JSON-Schema envelope, which used to
        validate as a totally empty ICP and told the user their brief lacked
        detail.
        """
        enveloped = {
            "type": "object",
            "properties": {
                "icp": {
                    "type": "object",
                    "properties": {
                        "industries": ["Animation", "Design"],
                        "locations": ["Dubai"],
                        "company_size_min": 5,
                        "company_size_max": 50,
                    },
                    "required": ["industries", "locations"],
                },
                "search_plan": [{"query": "animation agencies in Dubai", "rationale": "r"}],
            },
            "required": ["icp", "search_plan"],
        }
        _patch(monkeypatch, _Response(json_lib.dumps(enveloped)))

        result = await _generate()

        assert result.icp.industries == ["Animation", "Design"]
        assert result.icp.locations == ["Dubai"]
        assert (result.icp.company_size_min, result.icp.company_size_max) == (5, 50)
        assert result.search_plan[0].query == "animation agencies in Dubai"
