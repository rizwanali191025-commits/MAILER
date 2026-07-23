"""Tests for the bulk-send orchestration (dry-run, no Gmail needed)."""

from src import mailer


def _write_csv(tmp_path, text):
    p = tmp_path / "recipients.csv"
    p.write_text(text, encoding="utf-8")
    return str(p)


CONFIG = {
    "sender_email": "me@example.com",
    "sender_names": ["Name A", "Name B"],
    "delay_seconds": 0,
    "max_per_run": 0,
}


def test_dry_run_returns_one_result_per_recipient(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        "email,first_name\nalice@example.com,Alice\nbob@example.com,Bob\n",
    )
    results = mailer.send_bulk(
        service=None,
        config=CONFIG,
        recipients_csv=csv_path,
        subject_template="Hi {{first_name}}",
        body_html_template="<h1>Hello {{first_name}}</h1>",
        attach_as_pptx=False,
        dry_run=True,
    )
    assert len(results) == 2
    assert all(r["status"] == "dry_run" for r in results)
    assert {r["to"] for r in results} == {"alice@example.com", "bob@example.com"}


def test_rows_missing_email_are_skipped(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        "email,first_name\n,NoEmail\ncarol@example.com,Carol\n",
    )
    results = mailer.send_bulk(
        service=None,
        config=CONFIG,
        recipients_csv=csv_path,
        subject_template="Hi",
        body_html_template="<h1>Hi</h1>",
        attach_as_pptx=False,
        dry_run=True,
    )
    assert len(results) == 1
    assert results[0]["to"] == "carol@example.com"


def test_max_per_run_caps_recipients(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        "email,first_name\na@x.com,A\nb@x.com,B\nc@x.com,C\n",
    )
    config = {**CONFIG, "max_per_run": 2}
    results = mailer.send_bulk(
        service=None,
        config=config,
        recipients_csv=csv_path,
        subject_template="Hi",
        body_html_template="<h1>Hi</h1>",
        attach_as_pptx=False,
        dry_run=True,
    )
    assert len(results) == 2


def test_dry_run_with_pptx_attachment(tmp_path):
    """Dry run should still exercise (and clean up) PPTX generation."""
    csv_path = _write_csv(tmp_path, "email,first_name\na@x.com,A\n")
    results = mailer.send_bulk(
        service=None,
        config=CONFIG,
        recipients_csv=csv_path,
        subject_template="Hi {{first_name}}",
        body_html_template="<h1>Hello {{first_name}}</h1><p>body</p>",
        attach_as_pptx=True,
        dry_run=True,
    )
    assert len(results) == 1
    assert results[0]["status"] == "dry_run"
