# SEO Audit Tool

A small, self-contained SEO audit tool. The on-page/technical checks run with
zero dependencies and no API key. Keyword, traffic, competitor, and backlink
data are layered in via the [DataForSEO](https://dataforseo.com) API when
credentials are provided.

## Files

| File                   | Purpose                                              |
|------------------------|------------------------------------------------------|
| `onpage_audit.py`      | Free on-page + robots/sitemap checks (stdlib only)   |
| `dataforseo_client.py` | Thin DataForSEO API wrapper                          |
| `audit.py`             | Orchestrator: on-page + DataForSEO into one report   |
| `generate_pdf_report.py` | Renders a styled, client-ready PDF report          |
| `.env.example`         | Credential template (copy to `.env`, never commit)   |

## Usage

Free on-page / technical audit (no credentials needed):

```bash
python3 seo/onpage_audit.py https://yourdomain.com
```

Full audit (requires DataForSEO credentials):

```bash
cp seo/.env.example seo/.env      # then edit seo/.env with your real values
python3 seo/audit.py https://yourdomain.com
```

Skip the API and run only the free checks:

```bash
python3 seo/audit.py https://yourdomain.com --no-api
```

Generate a client-ready PDF report (requires `reportlab`):

```bash
pip install reportlab
python3 seo/generate_pdf_report.py https://yourdomain.com
# -> seo/reports/<domain>-audit.pdf
```

## Credentials

`seo/.env` is git-ignored. Put your DataForSEO **API Login** (email) and **API
Password** there — get them from <https://app.dataforseo.com/api-access>. Never
commit real credentials.

## What it checks

**On-page (free):** title length, meta description, duplicate meta/OG tags
(plugin-conflict signal), canonical, viewport, robots meta, H1 usage, image alt
coverage, JSON-LD structured data, HTML payload size.

**Robots/sitemap (free):** robots.txt disallow rules, sitemap discovery and URL
counts, and indexability contradictions (URLs listed in a sitemap but blocked by
robots.txt).

**DataForSEO (paid):** organic traffic/keyword estimate, keywords the domain
ranks for, top organic competitors, and a backlink-profile summary.
