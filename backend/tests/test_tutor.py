import json

import httpx
import pytest

from app.core.tutor import (
    OllamaTutorProvider,
    TutorContext,
    TutorProviderError,
    _has_complete_solution_structure,
    _repeats_prior_hint,
    _system_prompt,
    requests_complete_solution,
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


def test_solution_request_detection_handles_give_up_and_direct_requests() -> None:
    solution_requests = (
        "solve it",
        "Please solve this problem",
        "show me the answer",
        "give me the solution",
        "explain the solution",
        "I give up",
        "I don't know",
    )
    for request in solution_requests:
        assert requests_complete_solution(request)

    assert not requests_complete_solution("My solution is 10 N.")
    assert not requests_complete_solution("I don't know whether to use sine or cosine.")


def test_solution_prompt_requires_a_complete_worked_explanation() -> None:
    solution_context = TutorContext(
        **{**context().__dict__, "latest_attempt": "solve it"},
    )
    prompt = _system_prompt(solution_context, "explain_solution")
    assert '"Step 1: ..."' in prompt
    assert '"Step 2: ..."' in prompt
    assert '"Step 3: ..."' in prompt
    assert '"Final answer: ..."' in prompt
    assert "Do not write a long unstructured paragraph" in prompt
    assert "Never use LaTeX" in prompt
    assert "Fx = 10 × cos(30°) = 8.66 N" in prompt
    assert "next_action to complete" in prompt


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


def test_complete_solution_structure_requires_all_sections() -> None:
    complete = (
        "Step 1: Identify the known values.\n"
        "Step 2: Choose the formula and explain why.\n"
        "Step 3: Substitute and calculate.\n"
        "Final answer: 10 N.\n"
        "This result has the expected units and magnitude."
    )
    assert _has_complete_solution_structure(complete)
    markdown_variant = (
        "**Step 1.** Identify all known quantities and draw the force direction clearly.\n"
        "**Step 2.** Choose the component formulas and explain why cosine applies horizontally.\n"
        "**Step 3.** Substitute every value, calculate both components, and retain their units.\n"
        "**Final answer:** The horizontal component is 8.66 N and vertical component is 5 N."
    )
    assert _has_complete_solution_structure(markdown_variant)
    latex_solution = (
        "Step 1: Identify the magnitude and angle in the problem statement.\n"
        "Step 2: Calculate the horizontal component using $ F_x = F \\cos \\theta $.\n"
        "Step 3: Calculate the vertical component using $ F_y = F \\sin \\theta $.\n"
        "Final answer: $ F_x = 8.66 \\text{N} $ and $ F_y = 5 \\text{N} $."
    )
    assert not _has_complete_solution_structure(latex_solution)
    assert not _has_complete_solution_structure("Step 1: Identify the known values.")


@pytest.mark.asyncio
async def test_ollama_provider_retries_an_incomplete_worked_solution() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        payload = json.loads(request.content)
        assert payload["options"]["num_predict"] == 900
        if calls == 2:
            assert "worked solution was incomplete" in payload["messages"][1]["content"]
        message = (
            "Step 1: Identify the values."
            if calls == 1
            else (
                "Step 1: Identify the known values.\n"
                "Step 2: Select and explain the formula.\n"
                "Step 3: Substitute the values and calculate.\n"
                "Final answer: The resultant is 10 N.\n"
                "Quick check: Why are the units newtons?"
            )
        )
        content = {
            "message": message,
            "hint_type": "feedback",
            "is_correct": None,
            "misconception": None,
            "next_action": "complete",
        }
        return httpx.Response(200, json={"message": {"content": json.dumps(content)}})

    result = await OllamaTutorProvider(transport=httpx.MockTransport(handler)).generate(
        context(), "explain_solution"
    )
    assert calls == 2
    assert "Final answer:" in result.message


@pytest.mark.asyncio
async def test_ollama_provider_hides_invalid_model_output() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "not-json"}})

    provider = OllamaTutorProvider(transport=httpx.MockTransport(handler))
    with pytest.raises(TutorProviderError, match="temporarily unavailable"):
        await provider.generate(context(), "start")
