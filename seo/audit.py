"""SEO audit orchestrator for a single domain.

Runs the free on-page/technical checks always, then layers in DataForSEO data
(keywords, traffic estimate, competitors, backlinks) when credentials exist.

Usage:
    python seo/audit.py https://example.com
    python seo/audit.py https://example.com --no-api   # skip DataForSEO
"""
from __future__ import annotations

import json
import sys
from urllib.parse import urlparse

import onpage_audit


def _domain(url: str) -> str:
    netloc = urlparse(url if "://" in url else "https://" + url).netloc
    return netloc or url


def run(url: str, use_api: bool = True) -> dict:
    result: dict = {"target": url}

    # 1. Free on-page + technical checks
    result["onpage"] = onpage_audit.audit_page(url)
    result["robots_sitemap"] = onpage_audit.audit_robots_and_sitemap(url)
    result["site_checks"] = onpage_audit.site_checks(url)

    if not use_api:
        return result

    # 2. DataForSEO-backed metrics (need credentials)
    try:
        from dataforseo_client import DataForSEOClient
        client = DataForSEOClient()
        domain = _domain(url)
        result["balance"] = client.check_balance()
        result["domain_overview"] = client.domain_rank_overview(domain)
        result["keywords"] = client.keywords_for_site(domain)
        result["competitors"] = client.competitors(domain)
        result["backlinks"] = client.backlinks_summary(domain)
    except RuntimeError as e:
        result["api_skipped"] = str(e)
    except Exception as e:  # network / API failure
        result["api_error"] = repr(e)

    return result


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    url = args[0] if args else "https://luxeclay.in"
    use_api = "--no-api" not in sys.argv
    report = run(url, use_api=use_api)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
