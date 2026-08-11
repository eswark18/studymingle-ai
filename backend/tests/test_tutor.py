import json

import httpx
import pytest

from app.core.tutor import (
    OllamaTutorProvider,
    TutorContext,
    TutorProviderError,
    _repeats_prior_hint,
    _system_prompt,
)


def context() -> TutorContext:
    return TutorContext(
        source_text="OCR source must stay unchanged.",
        learning_text="Find the resultant of perpendicular forces 6 N and 8 N.",
        education_track="school",
        grade_or_year="Grade 10",
        subject="Physics",
    )


def test_prompt_is_age_aware_and_protects_source_text() -> None:
    prompt = _system_prompt(context(), "start")
    assert "Grade 10" in prompt
    assert "Physics" in prompt
    assert "Original immutable OCR text" in prompt
    assert "Never provide a complete solution" in prompt
    assert "Help the learner restate" in prompt


def test_attempt_prompt_requires_feedback_on_exact_attempt() -> None:
    attempt_context = TutorContext(
        **{**context().__dict__, "latest_attempt": "10 N"},
    )
    prompt = _system_prompt(attempt_context, "check_attempt")
    assert "Evaluate the learner's Latest attempt directly" in prompt
    assert "Latest attempt: 10 N" in prompt


def test_repeat_detection_catches_duplicate_and_paraphrased_hint() -> None:
    prior = ("Break the force into horizontal and vertical components.",)
    assert _repeats_prior_hint(prior[0], prior)
    assert _repeats_prior_hint(
        "We need to break the force into its vertical and horizontal components.", prior
    )
    assert not _repeats_prior_hint(
        "Which trigonometric function relates the adjacent side to the hypotenuse?", prior
    )


@pytest.mark.asyncio
async def test_ollama_provider_validates_structured_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["stream"] is False
        assert payload["think"] is False
        assert payload["format"]["type"] == "object"
        content = {
            "message": "Which relationship connects the sides of a right triangle?",
            "hint_type": "question",
            "is_correct": None,
            "misconception": None,
            "next_action": "attempt",
        }
        return httpx.Response(200, json={"message": {"content": json.dumps(content)}})

    provider = OllamaTutorProvider(transport=httpx.MockTransport(handler))
    result = await provider.generate(context(), "start")
    assert result.hint_type == "question"
    assert result.next_action == "attempt"


@pytest.mark.asyncio
async def test_ollama_provider_retries_a_repeated_next_hint() -> None:
    calls = 0
    prior = "Break the force into horizontal and vertical components."

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        payload = json.loads(request.content)
        if calls == 2:
            assert len(payload["messages"]) == 2
        message = prior if calls == 1 else "Which ratio uses the side adjacent to the angle?"
        content = {
            "message": message,
            "hint_type": "concept",
            "is_correct": None,
            "misconception": None,
            "next_action": "attempt",
        }
        return httpx.Response(200, json={"message": {"content": json.dumps(content)}})

    next_context = TutorContext(**{**context().__dict__, "prior_hints": (prior,)})
    result = await OllamaTutorProvider(transport=httpx.MockTransport(handler)).generate(
        next_context, "next_hint"
    )
    assert calls == 2
    assert result.message.startswith("Which ratio")


@pytest.mark.asyncio
async def test_ollama_provider_hides_invalid_model_output() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "not-json"}})

    provider = OllamaTutorProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(TutorProviderError, match="temporarily unavailable"):
        await provider.generate(context(), "start")
