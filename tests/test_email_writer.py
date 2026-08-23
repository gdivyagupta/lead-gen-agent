import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from leadgen.email_writer import _extract_json  # noqa: E402


def test_extract_json_plain():
    text = '{"subject": "Hi", "body": "Hello there."}'
    assert _extract_json(text) == {"subject": "Hi", "body": "Hello there."}


def test_extract_json_strips_markdown_fences():
    text = '```json\n{"subject": "Hi", "body": "Hello there."}\n```'
    assert _extract_json(text) == {"subject": "Hi", "body": "Hello there."}


def test_extract_json_with_surrounding_prose():
    text = 'Sure, here you go:\n{"subject": "Hi", "body": "Hello."}\nLet me know!'
    assert _extract_json(text) == {"subject": "Hi", "body": "Hello."}
