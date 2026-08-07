from app.core.ocr import parse_questions


def test_parse_numbered_worksheet_questions() -> None:
    text = """
    STUDYMINGLE ENGINEERING MECHANICS
    1
    Resolve a force into horizontal and vertical components.
    VECTORS
    2
    Find the resultant of two perpendicular forces of 6 N and 8 N.
    Original StudyMingle worksheet fixture
    """

    assert parse_questions(text) == [
        (1, "Resolve a force into horizontal and vertical components."),
        (2, "Find the resultant of two perpendicular forces of 6 N and 8 N."),
    ]


def test_parse_inline_numbered_questions() -> None:
    text = """
    1. Explain why equilibrium requires the net force to equal zero.
    2) Calculate the moment produced by a 20 N force acting 3 m from a pivot.
    """

    assert parse_questions(text) == [
        (1, "Explain why equilibrium requires the net force to equal zero."),
        (2, "Calculate the moment produced by a 20 N force acting 3 m from a pivot."),
    ]


def test_parse_falls_back_to_sentence_questions() -> None:
    text = "Which theorem connects the three side lengths? Explain your reasoning clearly."

    assert parse_questions(text) == [
        (1, "Which theorem connects the three side lengths?"),
        (2, "Explain your reasoning clearly."),
    ]


def test_parse_ocr_paragraphs_without_number_markers() -> None:
    text = """
    STUDYMINGLE ENGINEERING MECHANICS

    LEARNING MODE Show your method and use units.

    Resolve a 10 N force into horizontal and vertical components.

    Two perpendicular forces act at one point. Find their resultant.

    Explain why equilibrium requires the vector sum to equal zero.
    """

    assert parse_questions(text) == [
        (1, "Resolve a 10 N force into horizontal and vertical components."),
        (2, "Two perpendicular forces act at one point. Find their resultant."),
        (3, "Explain why equilibrium requires the vector sum to equal zero."),
    ]
