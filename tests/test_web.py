"""Smoke tests for the Flask web UI routes."""

import pytest

from app import flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_index_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Bulk Gmail Mailer" in resp.data


def test_status_is_json(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    assert "running" in resp.get_json()


def test_preview_renders_tags(client):
    resp = client.post(
        "/preview",
        data={
            "index": "1",
            "subject_tmpl": "Hi {{first_name}}",
            "body_tmpl": "<h1>Hello {{first_name}}</h1>",
            "recipients_csv": "email,first_name\nz@x.com,Zoe\n",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["subject"] == "Hi Zoe"
    assert "Hello Zoe" in data["body"]


def test_preview_rejects_out_of_range_index(client):
    resp = client.post(
        "/preview",
        data={
            "index": "99",
            "subject_tmpl": "Hi",
            "body_tmpl": "<h1>Hi</h1>",
            "recipients_csv": "email,first_name\nz@x.com,Zoe\n",
        },
    )
    assert resp.status_code == 400


def test_send_requires_saved_config(client, tmp_path, monkeypatch):
    # With the default placeholder config, sender_email is present, so we
    # instead verify the empty-config guard by pointing at a blank config.
    import app as app_module

    monkeypatch.setattr(app_module, "_load_config", lambda: {
        "sender_email": "", "sender_names": [], "delay_seconds": 1.5, "max_per_run": 0,
    })
    resp = client.post("/send", data={"dry_run": "1", "attach_pptx": "0"})
    assert resp.status_code == 400
