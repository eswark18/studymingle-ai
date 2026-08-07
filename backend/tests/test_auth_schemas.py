import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest


def test_registration_requires_strong_password() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="student@example.com",
            password="onlyletters",
            display_name="Student",
        )


def test_registration_accepts_expected_profile() -> None:
    payload = RegisterRequest(
        email="student@example.com",
        password="Learning1234",
        display_name="Student",
        education_track="school",
        grade_or_year="8",
    )

    assert str(payload.email) == "student@example.com"
