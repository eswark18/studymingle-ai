import json

import httpx
import pytest

from app.core.tutor import OllamaTutorProvider, TutorContext, TutorProviderError, _system_prompt


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


@pytest.mark.asyncio
async def test_ollama_provider_validates_structured_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["stream"] is False
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
async def test_ollama_provider_hides_invalid_model_output() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "not-json"}})

    provider = OllamaTutorProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(TutorProviderError, match="temporarily unavailable"):
        await provider.generate(context(), "start")
