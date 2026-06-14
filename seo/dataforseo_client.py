"""Minimal DataForSEO API client.

Loads credentials from seo/.env (or environment variables) and exposes a thin
wrapper over the handful of DataForSEO endpoints used by the audit.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
import urllib.error
from pathlib import Path

API_BASE = "https://api.dataforseo.com"


def _load_env() -> None:
    """Load KEY=VALUE pairs from seo/.env into os.environ if not already set."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.split("#", 1)[0].strip()
        if key and key not in os.environ:
            os.environ[key] = value


class DataForSEOClient:
    def __init__(self, login: str | None = None, password: str | None = None):
        _load_env()
        self.login = login or os.environ.get("DATAFORSEO_LOGIN", "")
        self.password = password or os.environ.get("DATAFORSEO_PASSWORD", "")
        self.location_code = int(os.environ.get("DATAFORSEO_LOCATION_CODE", "2356"))
        self.language_code = os.environ.get("DATAFORSEO_LANGUAGE_CODE", "en")
        if not self.login or "your_login" in self.login:
            raise RuntimeError(
                "DataForSEO credentials missing. Copy seo/.env.example to seo/.env "
                "and fill in DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD."
            )

    def _auth_header(self) -> str:
        token = base64.b64encode(f"{self.login}:{self.password}".encode()).decode()
        return f"Basic {token}"

    def _post(self, path: str, payload: list[dict]) -> dict:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            API_BASE + path,
            data=data,
            headers={
                "Authorization": self._auth_header(),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.code, "message": e.read().decode(errors="replace")}

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(
            API_BASE + path,
            headers={"Authorization": self._auth_header()},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())

    # --- endpoints -------------------------------------------------------

    def check_balance(self) -> dict:
        """Return account info incl. remaining balance (verifies credentials)."""
        return self._get("/v3/appendix/user_data")

    def keywords_for_site(self, target: str) -> dict:
        """Keywords a domain ranks for (Google Ads volume data)."""
        return self._post(
            "/v3/keywords_data/google_ads/keywords_for_site/live",
            [{
                "target": target,
                "location_code": self.location_code,
                "language_code": self.language_code,
            }],
        )

    def domain_rank_overview(self, target: str) -> dict:
        """Organic traffic / keyword count estimate for a domain."""
        return self._post(
            "/v3/dataforseo_labs/google/domain_rank_overview/live",
            [{
                "target": target,
                "location_code": self.location_code,
                "language_code": self.language_code,
            }],
        )

    def competitors(self, target: str) -> dict:
        """Organic competitors for a domain."""
        return self._post(
            "/v3/dataforseo_labs/google/competitors_domain/live",
            [{
                "target": target,
                "location_code": self.location_code,
                "language_code": self.language_code,
                "limit": 10,
            }],
        )

    def backlinks_summary(self, target: str) -> dict:
        """Backlink profile summary (referring domains, total backlinks)."""
        return self._post(
            "/v3/backlinks/summary/live",
            [{"target": target, "internal_list_limit": 10}],
        )
