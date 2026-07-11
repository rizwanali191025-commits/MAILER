"""On-page / technical SEO checks that need no paid API.

Fetches a URL plus its robots.txt and sitemap, then reports title/meta/heading
quality, tag-duplication conflicts, indexability contradictions, and catalog
size. Pure standard library so it runs anywhere Python 3.8+ does.
"""
from __future__ import annotations

import re
import sys
import urllib.request
import urllib.error
from html import unescape
from urllib.parse import urljoin, urlparse

UA = "Mozilla/5.0 (compatible; LuxeClaySEOAudit/1.0)"


def _fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def _find_all(pattern: str, html: str) -> list[str]:
    return re.findall(pattern, html, re.IGNORECASE | re.DOTALL)


def _text(html_fragment: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", html_fragment)).strip()


def audit_page(url: str) -> dict:
    status, html = _fetch(url)
    report: dict = {"url": url, "http_status": status, "issues": [], "ok": []}
    if not html:
        report["issues"].append(f"Could not fetch page (HTTP {status}).")
        return report

    # Title
    titles = _find_all(r"<title[^>]*>(.*?)</title>", html)
    if titles:
        t = _text(titles[0])
        report["title"] = t
        report["title_length"] = len(t)
        if len(t) < 30:
            report["issues"].append(
                f"Title too short ({len(t)} chars): '{t}'. Aim for 50-60 keyword-rich chars."
            )
        elif len(t) > 60:
            report["issues"].append(f"Title too long ({len(t)} chars) — may truncate in SERPs.")
        else:
            report["ok"].append(f"Title length OK ({len(t)} chars).")
    else:
        report["issues"].append("No <title> tag found.")

    # Meta description
    descs = _find_all(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html)
    if not descs:
        report["issues"].append("No meta description found.")
    else:
        d = unescape(descs[0])
        report["meta_description"] = d
        report["meta_description_length"] = len(d)
        if len(descs) > 1:
            report["issues"].append(
                f"Duplicate meta description tags ({len(descs)}×) — likely SEO-plugin/theme conflict."
            )
        if len(d) > 160:
            report["issues"].append(f"Meta description too long ({len(d)} chars).")
        else:
            report["ok"].append(f"Meta description present ({len(d)} chars).")

    # Duplicate OpenGraph / Twitter tag detection (plugin conflict signal)
    og_titles = _find_all(r'property=["\']og:title["\']', html)
    if len(og_titles) > 1:
        report["issues"].append(
            f"Duplicate og:title tags ({len(og_titles)}×) — two plugins/theme emitting social tags."
        )
    report["has_og"] = len(og_titles) >= 1
    report["has_twitter_card"] = bool(_find_all(r'name=["\']twitter:card["\']', html))
    og_url = _find_all(r'property=["\']og:url["\']\s+content=["\'](.*?)["\']', html)
    report["og_url"] = og_url[0] if og_url else ""

    # Canonical
    canon = _find_all(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']', html)
    if canon:
        report["canonical"] = canon[0]
        report["ok"].append(f"Canonical tag present: {canon[0]}")
    else:
        report["issues"].append("No canonical tag found.")

    # Viewport
    if _find_all(r'name=["\']viewport["\']', html):
        report["ok"].append("Viewport meta present (mobile-friendly signal).")
    else:
        report["issues"].append("No viewport meta — mobile rendering at risk.")

    # Robots meta
    robots_meta = _find_all(r'<meta\s+name=["\']robots["\']\s+content=["\'](.*?)["\']', html)
    if robots_meta:
        report["robots_meta"] = robots_meta[0]
        if "noindex" in robots_meta[0].lower():
            report["issues"].append("Page has robots 'noindex' — it will be excluded from Google.")

    # Headings
    h1s = [_text(h) for h in _find_all(r"<h1[^>]*>(.*?)</h1>", html)]
    report["h1"] = h1s
    if len(h1s) == 0:
        report["issues"].append("No H1 heading found.")
    elif len(h1s) > 1:
        report["issues"].append(f"Multiple H1 tags ({len(h1s)}): {h1s} — use one keyword-focused H1.")
    else:
        report["ok"].append(f"Single H1: '{h1s[0]}'")

    # Images / alt
    imgs = _find_all(r"<img\b[^>]*>", html)
    no_alt = [i for i in imgs if not re.search(r'\balt=', i, re.IGNORECASE)]
    report["image_count"] = len(imgs)
    report["images_missing_alt"] = len(no_alt)
    if no_alt:
        report["issues"].append(f"{len(no_alt)}/{len(imgs)} images missing alt text.")
    else:
        report["ok"].append(f"All {len(imgs)} images have alt attributes.")

    # Structured data
    ld = _find_all(r'application/ld\+json', html)
    report["json_ld_blocks"] = len(ld)
    if ld:
        report["ok"].append(f"{len(ld)} JSON-LD structured-data block(s) present.")
    else:
        report["issues"].append("No JSON-LD structured data found.")

    # Page weight
    report["html_bytes"] = len(html.encode("utf-8"))
    if report["html_bytes"] > 500_000:
        report["issues"].append(
            f"Large HTML payload ({report['html_bytes'] // 1024} KB) — review page-speed impact."
        )

    return report


def audit_robots_and_sitemap(base_url: str) -> dict:
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    out: dict = {"issues": [], "ok": [], "disallow": [], "sitemaps": []}

    status, robots = _fetch(urljoin(root, "/robots.txt"))
    if status == 200:
        out["disallow"] = re.findall(r"(?im)^\s*Disallow:\s*(\S+)", robots)
        out["sitemaps"] = re.findall(r"(?im)^\s*Sitemap:\s*(\S+)", robots)
        out["ok"].append("robots.txt found.")
    else:
        out["issues"].append("No robots.txt found.")

    # Pull sitemap index and count child URLs
    for sm in out["sitemaps"]:
        s, body = _fetch(sm)
        children = re.findall(r"<loc>(.*?)</loc>", body)
        out.setdefault("sitemap_children", {})[sm] = children
        for child in children:
            cs, cbody = _fetch(child)
            count = len(re.findall(r"<loc>", cbody))
            out.setdefault("sitemap_counts", {})[child] = count

    return out


def _status(url: str) -> tuple[int, str]:
    """Return (status_code, final_url) without following redirects."""
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=20) as resp:
            return resp.status, resp.headers.get("Location", "")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", "") if e.headers else ""
    except Exception:
        return 0, ""


def site_checks(base_url: str) -> dict:
    """Domain-level technical checks: HTTPS, www canonicalisation, duplicate
    homepage URL, and 404 handling."""
    parsed = urlparse(base_url if "://" in base_url else "https://" + base_url)
    host = parsed.netloc
    bare = host[4:] if host.startswith("www.") else host
    out: dict = {"issues": [], "ok": []}

    # HTTP -> HTTPS
    code, loc = _status(f"http://{bare}/")
    if code in (301, 308) and loc.startswith("https"):
        out["ok"].append("HTTP redirects to HTTPS (301).")
    else:
        out["issues"].append("HTTP does not 301-redirect to HTTPS.")

    # www canonicalisation
    www_code, www_loc = _status(f"https://www.{bare}/")
    nonwww_code, _ = _status(f"https://{bare}/")
    if www_code in (301, 308):
        out["ok"].append("www redirects to the canonical host.")
    elif www_code == 200 and nonwww_code == 200:
        out["www_conflict"] = True
        out["issues"].append(
            "Both www and non-www serve the site (200) with no redirect — duplicate content."
        )

    # Duplicate homepage URL: / vs /index.html
    root_code, _ = _status(f"https://{bare}/")
    idx_code, _ = _status(f"https://{bare}/index.html")
    if root_code == 200 and idx_code == 200:
        out["index_dupe"] = True
        out["issues"].append(
            "Homepage is reachable at both / and /index.html (200) — duplicate URL."
        )

    # 404 handling
    nf_code, _ = _status(f"https://{bare}/this-page-does-not-exist-{hash(bare) % 9999}")
    if nf_code == 404:
        out["ok"].append("Missing pages correctly return 404.")
    elif nf_code == 200:
        out["issues"].append("Missing pages return 200 (soft 404) instead of 404.")

    return out


def main(url: str) -> None:
    print(f"\n=== ON-PAGE AUDIT: {url} ===")
    page = audit_page(url)
    for k, v in page.items():
        if k not in ("issues", "ok"):
            print(f"  {k}: {v}")
    print("\n  ISSUES:")
    for i in page["issues"]:
        print(f"   - {i}")
    print("\n  PASSED:")
    for i in page["ok"]:
        print(f"   + {i}")

    rs = audit_robots_and_sitemap(url)
    print("\n=== ROBOTS / SITEMAP ===")
    print(f"  Disallow rules: {rs['disallow']}")
    print(f"  Sitemaps: {rs['sitemaps']}")
    for child, count in rs.get("sitemap_counts", {}).items():
        print(f"   {child}: {count} URLs")
    # Indexability contradiction check
    for child, urls in rs.get("sitemap_children", {}).items():
        for u in urls:
            path = urlparse(u).path
            for dis in rs["disallow"]:
                d = dis.rstrip("*")
                if d and path.startswith(d):
                    print(f"   ! CONFLICT: {u} is in a sitemap but blocked by 'Disallow: {dis}'")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://luxeclay.in"
    main(target)
