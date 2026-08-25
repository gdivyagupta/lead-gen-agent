import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from leadgen.email_writer import _extract_json, _titlecase_subject, render_body  # noqa: E402


def test_extract_json_plain():
    text = '{"subject": "Hi", "body": "Hello there."}'
    assert _extract_json(text) == {"subject": "Hi", "body": "Hello there."}


def test_extract_json_strips_markdown_fences():
    text = '```json\n{"subject": "Hi", "body": "Hello there."}\n```'
    assert _extract_json(text) == {"subject": "Hi", "body": "Hello there."}


def test_extract_json_with_surrounding_prose():
    text = 'Sure, here you go:\n{"subject": "Hi", "body": "Hello."}\nLet me know!'
    assert _extract_json(text) == {"subject": "Hi", "body": "Hello."}


def test_titlecase_subject_capitalizes_each_word():
    assert _titlecase_subject("quick question about leads") == "Quick Question About Leads"


def test_titlecase_subject_preserves_acronyms_and_apostrophes():
    assert _titlecase_subject("hvac leads, it's worth a look") == \
        "Hvac Leads, It's Worth A Look"


def test_render_body_matches_requested_template():
    plain, body_html = render_body(
        "Kendra",
        [
            "Most trades companies at Alder lose money because leads go cold.",
            "I set up systems that handle lead gen automatically.",
        ],
        "Divya",
        "https://calendar.app.google/6V5eMjXF9m578AFXA",
    )
    assert plain == (
        "Kendra,\n"
        "\n"
        "Most trades companies at Alder lose money because leads go cold.\n"
        "\n"
        "I set up systems that handle lead gen automatically.\n"
        "\n"
        "Book a Slot: My Calendar (https://calendar.app.google/6V5eMjXF9m578AFXA)\n"
        "\n"
        "Best,\n"
        "Divya"
    )
    assert '<a href="https://calendar.app.google/6V5eMjXF9m578AFXA">My Calendar</a>' in body_html
