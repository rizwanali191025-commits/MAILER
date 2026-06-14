"""Generate a client-ready PDF SEO audit report.

Runs the live on-page/technical audit (and DataForSEO data if credentials are
present) and renders a styled PDF with reportlab.

Usage:
    python3 seo/generate_pdf_report.py https://luxeclay.in [output.pdf]
"""
from __future__ import annotations

import sys
from datetime import date
from urllib.parse import urlparse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

import audit as audit_mod

# Brand palette
NAVY = colors.HexColor("#1a2238")
ACCENT = colors.HexColor("#c08457")   # warm clay tone
GREEN = colors.HexColor("#2e7d32")
RED = colors.HexColor("#c62828")
AMBER = colors.HexColor("#e08e0b")
LIGHT = colors.HexColor("#f4f1ec")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("Cover", fontSize=30, leading=36, textColor=NAVY,
                          alignment=TA_CENTER, spaceAfter=6, fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle("CoverSub", fontSize=13, leading=18, textColor=ACCENT,
                          alignment=TA_CENTER, spaceAfter=4))
    ss.add(ParagraphStyle("H1", fontSize=16, leading=20, textColor=NAVY,
                          spaceBefore=14, spaceAfter=8, fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle("H2", fontSize=12.5, leading=16, textColor=ACCENT,
                          spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle("Body2", fontSize=10, leading=15, textColor=colors.HexColor("#222")))
    ss.add(ParagraphStyle("Cell", fontSize=9, leading=12, textColor=colors.HexColor("#222")))
    ss.add(ParagraphStyle("CellHdr", fontSize=9.5, leading=12, textColor=colors.white,
                          fontName="Helvetica-Bold"))
    return ss


def _scored(onpage: dict) -> int:
    """Crude 0-100 health score from on-page issues."""
    passed = len(onpage.get("ok", []))
    issues = len(onpage.get("issues", []))
    total = passed + issues
    if total == 0:
        return 0
    return round(100 * passed / total)


def build(url: str, out_path: str) -> str:
    data = audit_mod.run(url, use_api=True)
    onpage = data["onpage"]
    rs = data["robots_sitemap"]
    ss = _styles()
    domain = urlparse(url if "://" in url else "https://" + url).netloc

    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            topMargin=20 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            title=f"SEO Audit — {domain}")
    el = []

    # ---- Cover ----
    el.append(Spacer(1, 60 * mm))
    el.append(Paragraph("SEO Audit Report", ss["Cover"]))
    el.append(Paragraph(domain, ss["CoverSub"]))
    el.append(Spacer(1, 4 * mm))
    el.append(HRFlowable(width="40%", thickness=2, color=ACCENT, hAlign="CENTER"))
    el.append(Spacer(1, 6 * mm))
    el.append(Paragraph(f"Prepared {date.today().isoformat()}", ss["CoverSub"]))

    score = _scored(onpage)
    score_color = GREEN if score >= 75 else (AMBER if score >= 50 else RED)
    score_hex = "#" + score_color.hexval()[2:]
    el.append(Spacer(1, 30 * mm))
    el.append(Paragraph(
        f'<font size=46 color="{score_hex}"><b>{score}</b></font>'
        f'<font size=18 color="#888">/100</font>', ss["Cover"]))
    el.append(Paragraph("On-page technical health", ss["CoverSub"]))
    el.append(Spacer(1, 1))
    from reportlab.platypus import PageBreak
    el.append(PageBreak())

    # ---- Executive summary ----
    el.append(Paragraph("Executive Summary", ss["H1"]))
    issues = onpage.get("issues", [])
    passed = onpage.get("ok", [])
    el.append(Paragraph(
        f"This audit reviews the on-page and technical SEO health of "
        f"<b>{domain}</b>. We checked {len(passed) + len(issues)} on-page signals "
        f"and reviewed the site's robots.txt and XML sitemaps. The site passed "
        f"<b>{len(passed)}</b> checks and has <b>{len(issues)}</b> issues to "
        f"address. The most impactful fixes are detailed below.", ss["Body2"]))
    el.append(Spacer(1, 4 * mm))

    # ---- Technical snapshot table ----
    el.append(Paragraph("Technical Snapshot", ss["H1"]))
    rows = [[Paragraph("Check", ss["CellHdr"]),
             Paragraph("Result", ss["CellHdr"]),
             Paragraph("Detail", ss["CellHdr"])]]

    def add_row(check, ok, detail):
        mark = ('<font color="#2e7d32"><b>PASS</b></font>' if ok
                else '<font color="#c62828"><b>FIX</b></font>')
        rows.append([Paragraph(check, ss["Cell"]),
                     Paragraph(mark, ss["Cell"]),
                     Paragraph(detail, ss["Cell"])])

    title = onpage.get("title", "(none)")
    add_row("Page title", onpage.get("title_length", 0) >= 30,
            f"{onpage.get('title_length', 0)} chars: “{title}”")
    add_row("Meta description", "meta_description" in onpage,
            f"{onpage.get('meta_description_length', 0)} chars")
    add_row("Canonical tag", "canonical" in onpage, onpage.get("canonical", "missing"))
    add_row("Structured data", onpage.get("json_ld_blocks", 0) > 0,
            f"{onpage.get('json_ld_blocks', 0)} JSON-LD block(s)")
    add_row("H1 headings", len(onpage.get("h1", [])) == 1,
            f"{len(onpage.get('h1', []))} found")
    add_row("Image alt text", onpage.get("images_missing_alt", 1) == 0,
            f"{onpage.get('images_missing_alt', 0)}/{onpage.get('image_count', 0)} missing alt")
    add_row("HTML payload", onpage.get("html_bytes", 0) <= 500_000,
            f"{onpage.get('html_bytes', 0) // 1024} KB")
    counts = rs.get("sitemap_counts", {})
    add_row("XML sitemap", len(counts) > 0, f"{sum(counts.values())} URLs across {len(counts)} sitemaps")

    tbl = Table(rows, colWidths=[40 * mm, 20 * mm, 114 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ddd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    el.append(tbl)
    el.append(Spacer(1, 5 * mm))

    # ---- Issues to fix ----
    el.append(Paragraph("Issues to Fix", ss["H1"]))
    if not issues:
        el.append(Paragraph("No on-page issues detected.", ss["Body2"]))
    for i, issue in enumerate(issues, 1):
        el.append(Paragraph(f'<font color="#c62828"><b>{i}.</b></font> {issue}', ss["Body2"]))
        el.append(Spacer(1, 1.5 * mm))

    # ---- Passed checks ----
    el.append(Paragraph("What's Working", ss["H1"]))
    for p in passed:
        el.append(Paragraph(f'<font color="#2e7d32"><b>✓</b></font> {p}', ss["Body2"]))
        el.append(Spacer(1, 1 * mm))

    # ---- robots / sitemap ----
    el.append(Paragraph("Crawlability", ss["H1"]))
    el.append(Paragraph("<b>Disallow rules:</b> " +
                        ", ".join(d for d in rs.get("disallow", []) if d != "Sitemap:"),
                        ss["Body2"]))
    # contradiction check
    conflicts = []
    children = rs.get("sitemap_children", {})
    # children maps index->child sitemaps; counts maps child->n. Re-scan child URLs.
    for child in counts:
        try:
            import urllib.request
            req = urllib.request.Request(child, headers={"User-Agent": "audit"})
            body = urllib.request.urlopen(req, timeout=20).read().decode(errors="replace")
            import re
            for u in re.findall(r"<loc>(.*?)</loc>", body):
                path = urlparse(u).path
                for dis in rs.get("disallow", []):
                    d = dis.rstrip("*")
                    if d and d != "/" and path.startswith(d):
                        conflicts.append((u, dis))
        except Exception:
            pass
    if conflicts:
        el.append(Paragraph(
            "<b><font color='#c62828'>Conflict:</font></b> URLs listed in the "
            "sitemap but blocked by robots.txt (Google is told to both crawl and "
            "not crawl them):", ss["Body2"]))
        seen = set()
        for u, dis in conflicts:
            if u in seen:
                continue
            seen.add(u)
            el.append(Paragraph(f"&bull; {u} &mdash; blocked by <i>Disallow: {dis}</i>", ss["Cell"]))
    else:
        el.append(Paragraph("No sitemap/robots.txt contradictions detected.", ss["Body2"]))

    # ---- DataForSEO section ----
    el.append(Paragraph("Keyword, Traffic & Backlink Data", ss["H1"]))
    if "api_skipped" in data or "api_error" in data:
        el.append(Paragraph(
            "<i>Not included in this report.</i> Keyword rankings, organic traffic "
            "estimates, competitor mapping, and backlink profile require DataForSEO "
            "API credentials. Add them to <font face='Courier'>seo/.env</font> and "
            "re-run to include this section.", ss["Body2"]))
    else:
        el.append(Paragraph("Live DataForSEO metrics included in the JSON export.", ss["Body2"]))

    el.append(Spacer(1, 8 * mm))
    el.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#ccc")))
    el.append(Paragraph(
        '<font size=8 color="#999">Generated by the MAILER SEO audit tool. '
        'On-page data fetched live from the target site.</font>', ss["Body2"]))

    doc.build(el)
    return out_path


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    url = args[0] if args else "https://luxeclay.in"
    domain = urlparse(url if "://" in url else "https://" + url).netloc
    out = args[1] if len(args) > 1 else f"seo/reports/{domain}-audit.pdf"
    path = build(url, out)
    print(f"PDF written to {path}")


if __name__ == "__main__":
    main()
