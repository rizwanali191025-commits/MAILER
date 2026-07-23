"""Tests for the {{tag}} template engine."""

from src import template_engine


def test_renders_csv_columns():
    data = {"first_name": "Alice", "company": "Acme"}
    out = template_engine.render("Hi {{first_name}} from {{company}}", data)
    assert out == "Hi Alice from Acme"


def test_tags_are_case_insensitive():
    out = template_engine.render("{{First_Name}}", {"first_name": "Bob"})
    assert out == "Bob"


def test_unknown_tags_are_left_untouched():
    out = template_engine.render("Hello {{missing}}", {"first_name": "Bob"})
    assert out == "Hello {{missing}}"


def test_builtin_index_tag():
    out = template_engine.render("row {{index}}", {}, index=7)
    assert out == "row 7"


def test_builtin_date_and_time_are_populated():
    out = template_engine.render("{{date}} {{time}}", {})
    assert "{{" not in out  # both were substituted
    assert len(out.strip()) > 0


def test_random_id_is_eight_hex_chars():
    out = template_engine.render("{{random_id}}", {})
    assert len(out) == 8
    int(out, 16)  # raises if not valid hex


def test_list_tags_returns_unique_ordered():
    tags = template_engine.list_tags("{{a}} {{b}} {{a}} {{c}}")
    assert tags == ["a", "b", "c"]
