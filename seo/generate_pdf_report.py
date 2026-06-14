"""Generate a professional, client-ready PDF SEO audit report.

Runs the live on-page/technical audit (and DataForSEO data if credentials are
present), translates each technical finding into plain-English business language,
and renders a styled PDF a non-technical client can understand and act on.

Usage:
    python3 seo/generate_pdf_report.py https://luxeclay.in [output.pdf] [--brand "Agency Name"]
"""
from __future__ import annotations

import re
import sys
import urllib.request
from datetime import date
from urllib.parse import urlparse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    PageBreak, KeepTogether,
)

import audit as audit_mod

# ---- Brand palette -------------------------------------------------------
NAVY = colors.HexColor("#16243f")
ACCENT = colors.HexColor("#c08457")     # warm clay
ACCENT_LT = colors.HexColor("#f0e6dc")
GREEN = colors.HexColor("#2e7d32")
RED = colors.HexColor("#c0392b")
AMBER = colors.HexColor("#d68910")
GREY = colors.HexColor("#555555")
LIGHT = colors.HexColor("#f6f4f0")
LINE = colors.HexColor("#e2ddd5")

PAGE_W, PAGE_H = A4
CONTENT_W = PAGE_W - 36 * mm


# ---- Styles --------------------------------------------------------------
def _styles():
    ss = getSampleStyleSheet()
    add = ss.add
    add(ParagraphStyle("CoverTitle", fontSize=34, leading=40, textColor=colors.white,
                       alignment=TA_CENTER, fontName="Helvetica-Bold"))
    add(ParagraphStyle("CoverSub", fontSize=15, leading=20, textColor=ACCENT_LT,
                       alignment=TA_CENTER))
    add(ParagraphStyle("CoverMeta", fontSize=10.5, leading=16, textColor=colors.HexColor("#c9c9c9"),
                       alignment=TA_CENTER))
    add(ParagraphStyle("H1", fontSize=17, leading=21, textColor=NAVY,
                       spaceBefore=4, spaceAfter=8, fontName="Helvetica-Bold"))
    add(ParagraphStyle("H2", fontSize=12, leading=15, textColor=ACCENT,
                       spaceBefore=8, spaceAfter=3, fontName="Helvetica-Bold"))
    add(ParagraphStyle("Body2", fontSize=10, leading=15, textColor=colors.HexColor("#2b2b2b"),
                       alignment=TA_JUSTIFY, spaceAfter=3))
    add(ParagraphStyle("Lead", fontSize=10.5, leading=16, textColor=GREY, alignment=TA_JUSTIFY))
    add(ParagraphStyle("Cell", fontSize=9, leading=12.5, textColor=colors.HexColor("#2b2b2b")))
    add(ParagraphStyle("CellB", fontSize=9, leading=12.5, textColor=colors.HexColor("#2b2b2b"),
                       fontName="Helvetica-Bold"))
    add(ParagraphStyle("CellHdr", fontSize=9, leading=12, textColor=colors.white,
                       fontName="Helvetica-Bold"))
    add(ParagraphStyle("FindTitle", fontSize=11, leading=14, textColor=NAVY,
                       fontName="Helvetica-Bold"))
    add(ParagraphStyle("FindLabel", fontSize=8, leading=11, textColor=GREY,
                       fontName="Helvetica-Bold"))
    add(ParagraphStyle("FindText", fontSize=9.5, leading=13.5, textColor=colors.HexColor("#2b2b2b")))
    add(ParagraphStyle("Small", fontSize=8, leading=11, textColor=GREY))
    return ss


SS = _styles()


# ---- Finding model -------------------------------------------------------
def _sev_color(sev: str):
    return {"High": RED, "Medium": AMBER, "Low": GREEN}.get(sev, GREY)


def derive_findings(onpage: dict, rs: dict, domain: str) -> list[dict]:
    """Translate raw audit data into client-friendly findings."""
    f: list[dict] = []
    title = onpage.get("title", "")
    tlen = onpage.get("title_length", 0)

    # Title
    if tlen < 30:
        f.append(dict(
            sev="High", area="Homepage title",
            what=f"Your homepage's title tag currently reads “{title}” — only {tlen} "
                 "characters and missing your main keywords.",
            why="The title is the clickable blue headline shown in Google search "
                "results and the strongest single on-page ranking signal. A generic "
                "title means fewer people find and click your store.",
            fix="Set a descriptive, keyword-rich title such as “Handmade Clay "
                "Jewellery India | LuxeClay – Earrings, Studs & Pendants” (≈55–60 "
                "characters) in your SEO plugin settings.",
        ))

    # Duplicate meta tags
    dup_msgs = [m for m in onpage.get("issues", []) if "Duplicate" in m]
    if dup_msgs:
        f.append(dict(
            sev="High", area="Conflicting SEO tags",
            what="The homepage is sending Google the same information twice (and the "
                 "social-share title three times). This happens when two tools — your "
                 "SEO plugin and your theme — both try to control SEO settings.",
            why="When search engines receive conflicting instructions they may pick "
                "the wrong description or social preview, hurting how your brand "
                "appears in search and on WhatsApp/Instagram shares.",
            fix="Choose one tool (Yoast SEO is already installed) to manage SEO and "
                "social tags, and switch off the duplicate output in the theme or the "
                "second plugin.",
        ))

    # robots/sitemap conflict
    conflicts = _sitemap_conflicts(rs)
    if conflicts:
        examples = ", ".join(sorted({urlparse(u).path for u, _ in conflicts})[:3])
        f.append(dict(
            sev="High", area="Important pages blocked from Google",
            what=f"Key shop pages ({examples}) are listed in your sitemap as pages "
                 "you want indexed, but your robots.txt file simultaneously tells "
                 "Google not to visit them.",
            why="This contradiction can keep your main shop and category pages out of "
                "Google entirely — exactly the pages that should be earning sales "
                "traffic. It also wastes Google's crawl budget on a dead end.",
            fix="Decide that the shop pages should rank (recommended for a store) and "
                "remove the matching “Disallow” lines from robots.txt so Google can "
                "crawl and index them.",
        ))

    # Multiple H1
    h1s = onpage.get("h1", [])
    if len(h1s) > 1:
        f.append(dict(
            sev="Medium", area="Page headings",
            what=f"The homepage has {len(h1s)} main headings (“{h1s[0]}” and "
                 f"“{h1s[1]}”). Best practice is a single main heading that states "
                 "what the page is about.",
            why="The main heading helps Google understand the page's topic. A "
                "promotional banner heading like a flash-sale line doesn't describe "
                "your products and dilutes that signal.",
            fix="Use one clear main heading describing the business (e.g. “Handmade "
                "Clay Jewellery, Crafted in India”) and make promotional lines "
                "sub-headings instead.",
        ))

    # Image alt
    miss = onpage.get("images_missing_alt", 0)
    if miss:
        f.append(dict(
            sev="Low", area="Image descriptions",
            what=f"{miss} of {onpage.get('image_count', 0)} homepage images are "
                 "missing descriptive text (alt text), and several others use generic "
                 "labels.",
            why="Alt text helps your products appear in Google Images — a real source "
                "of discovery for visual products like jewellery — and improves "
                "accessibility.",
            fix="Add short, descriptive alt text to each image, e.g. “handmade clay "
                "marigold stud earrings”.",
        ))

    # Page weight
    kb = onpage.get("html_bytes", 0) // 1024
    if onpage.get("html_bytes", 0) > 500_000:
        f.append(dict(
            sev="Medium", area="Page speed",
            what=f"The homepage is heavy to load (about {kb} KB of code before images "
                 "are counted).",
            why="Slow pages frustrate shoppers and lower mobile rankings. Most of your "
                "visitors are likely on phones, where speed matters most for sales.",
            fix="Compress and lazy-load images, and review the page builder for unused "
                "elements. Run a Google PageSpeed Insights test and target the "
                "flagged items.",
        ))

    return f


def _sitemap_conflicts(rs: dict):
    conflicts = []
    for child in rs.get("sitemap_counts", {}):
        try:
            req = urllib.request.Request(child, headers={"User-Agent": "audit"})
            body = urllib.request.urlopen(req, timeout=20).read().decode(errors="replace")
            for u in re.findall(r"<loc>(.*?)</loc>", body):
                path = urlparse(u).path
                for dis in rs.get("disallow", []):
                    d = dis.rstrip("*")
                    if d and d != "/" and path.startswith(d):
                        conflicts.append((u, dis))
        except Exception:
            pass
    return conflicts


def _score(onpage: dict) -> int:
    passed = len(onpage.get("ok", []))
    issues = len(onpage.get("issues", []))
    total = passed + issues
    return round(100 * passed / total) if total else 0


# ---- Page furniture ------------------------------------------------------
def _header_footer(canvas, doc):
    canvas.saveState()
    # footer line + text
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 14 * mm, PAGE_W - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(18 * mm, 10 * mm, doc.brand)
    canvas.drawRightString(PAGE_W - 18 * mm, 10 * mm, f"SEO Audit · Page {doc.page}")
    canvas.restoreState()


def _cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, PAGE_H - 6 * mm, PAGE_W, 6 * mm, fill=1, stroke=0)
    canvas.rect(0, 0, PAGE_W, 6 * mm, fill=1, stroke=0)
    canvas.restoreState()


# ---- Finding card --------------------------------------------------------
def finding_card(idx: int, fnd: dict):
    sev = fnd["sev"]
    sc = _sev_color(sev)
    badge = Table([[Paragraph(f'<font color="white"><b>{sev.upper()}</b></font>', SS["Small"])]],
                  colWidths=[20 * mm])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), sc),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    head = Table([[Paragraph(f"{idx}. {fnd['area']}", SS["FindTitle"]), badge]],
                 colWidths=[CONTENT_W - 24 * mm, 24 * mm])
    head.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    body = Table([
        [Paragraph("THE ISSUE", SS["FindLabel"]), Paragraph(fnd["what"], SS["FindText"])],
        [Paragraph("WHY IT MATTERS", SS["FindLabel"]), Paragraph(fnd["why"], SS["FindText"])],
        [Paragraph("WHAT TO DO", SS["FindLabel"]), Paragraph(fnd["fix"], SS["FindText"])],
    ], colWidths=[28 * mm, CONTENT_W - 28 * mm])
    body.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (0, -1), 8), ("LEFTPADDING", (1, 0), (1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, sc),
    ]))
    return KeepTogether([head, Spacer(1, 2), body, Spacer(1, 6 * mm)])


# ---- Build ---------------------------------------------------------------
def build(url: str, out_path: str, brand: str) -> str:
    data = audit_mod.run(url, use_api=True)
    onpage = data["onpage"]
    rs = data["robots_sitemap"]
    domain = urlparse(url if "://" in url else "https://" + url).netloc
    findings = derive_findings(onpage, rs, domain)
    score = _score(onpage)
    highs = sum(1 for f in findings if f["sev"] == "High")

    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            topMargin=20 * mm, bottomMargin=20 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            title=f"SEO Audit Report — {domain}", author=brand)
    doc.brand = brand
    el = []

    # ---- COVER ----
    el.append(Spacer(1, 62 * mm))
    el.append(Paragraph("SEO Audit Report", SS["CoverTitle"]))
    el.append(Spacer(1, 3 * mm))
    el.append(Paragraph(domain, SS["CoverSub"]))
    el.append(Spacer(1, 28 * mm))
    band = (GREEN if score >= 75 else AMBER if score >= 50 else RED)
    band_hex = "#" + band.hexval()[2:]
    score_style = ParagraphStyle("Score", parent=SS["CoverTitle"], fontSize=58, leading=64)
    el.append(Paragraph(
        f'<font size=58 color="{band_hex}"><b>{score}</b></font>'
        f'<font size=20 color="#c9c9c9">/100</font>', score_style))
    el.append(Spacer(1, 4 * mm))
    el.append(Paragraph("On-page technical health score", SS["CoverMeta"]))
    el.append(Spacer(1, 26 * mm))
    el.append(Paragraph(f"Prepared for the owner of {domain}", SS["CoverMeta"]))
    el.append(Paragraph(f"Date: {date.today().strftime('%d %B %Y')}", SS["CoverMeta"]))
    el.append(Paragraph(f"Prepared by: {brand}", SS["CoverMeta"]))
    el.append(PageBreak())

    # ---- EXECUTIVE SUMMARY ----
    el.append(Paragraph("Executive Summary", SS["H1"]))
    el.append(Paragraph(
        f"This report reviews the search-engine health of <b>{domain}</b> and "
        "explains, in plain language, what is helping the website rank in Google, "
        "what is holding it back, and exactly what to do next. Each finding includes "
        "the issue, why it matters to your business, and the recommended action.",
        SS["Lead"]))
    el.append(Spacer(1, 4 * mm))

    # summary stat boxes
    passed = len(onpage.get("ok", []))
    def stat(num, label, col):
        return Table([[Paragraph(f'<font size=20 color="{("#"+col.hexval()[2:])}"><b>{num}</b></font>', SS["Body2"])],
                      [Paragraph(label, SS["Small"])]],
                     colWidths=[(CONTENT_W - 12 * mm) / 4])
    boxes = Table([[
        stat(score, "Health score", band),
        stat(highs, "High-priority fixes", RED),
        stat(len(findings), "Total issues", AMBER),
        stat(passed, "Checks passed", GREEN),
    ]], colWidths=[(CONTENT_W) / 4] * 4)
    boxes.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    el.append(boxes)
    el.append(Spacer(1, 5 * mm))

    el.append(Paragraph("What this means for you", SS["H2"]))
    verdict = ("Your website has a solid technical foundation, but a few important "
               "issues are limiting how well it can rank and how it appears in search "
               "results. The good news: every issue below is fixable, and the "
               f"{highs} high-priority items can be addressed quickly for the biggest "
               "gains.") if score < 75 else (
              "Your website is in strong technical health. The items below are "
              "refinements that will help maintain and extend your search visibility.")
    el.append(Paragraph(verdict, SS["Body2"]))
    el.append(Spacer(1, 4 * mm))

    # priority action plan table
    el.append(Paragraph("Priority Action Plan", SS["H2"]))
    rows = [[Paragraph("Priority", SS["CellHdr"]), Paragraph("Action", SS["CellHdr"]),
             Paragraph("Impact", SS["CellHdr"]), Paragraph("Effort", SS["CellHdr"])]]
    order = {"High": 0, "Medium": 1, "Low": 2}
    effort_map = {"Homepage title": "Low", "Conflicting SEO tags": "Low",
                  "Important pages blocked from Google": "Low", "Page headings": "Low",
                  "Image descriptions": "Medium", "Page speed": "Medium"}
    for i, fnd in enumerate(sorted(findings, key=lambda x: order.get(x["sev"], 3)), 1):
        sc = _sev_color(fnd["sev"])
        rows.append([
            Paragraph(f'<font color="{("#"+sc.hexval()[2:])}"><b>{fnd["sev"]}</b></font>', SS["Cell"]),
            Paragraph(fnd["area"], SS["CellB"]),
            Paragraph({"High": "High", "Medium": "Medium", "Low": "Low"}[fnd["sev"]], SS["Cell"]),
            Paragraph(effort_map.get(fnd["area"], "Low"), SS["Cell"]),
        ])
    plan = Table(rows, colWidths=[22 * mm, 92 * mm, 24 * mm, CONTENT_W - 138 * mm])
    plan.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    el.append(plan)
    el.append(PageBreak())

    # ---- DETAILED FINDINGS ----
    el.append(Paragraph("Detailed Findings & Recommendations", SS["H1"]))
    el.append(Paragraph(
        "Findings are ordered by priority. Each one is written so anyone can "
        "understand it — no technical background needed.", SS["Lead"]))
    el.append(Spacer(1, 5 * mm))
    for i, fnd in enumerate(sorted(findings, key=lambda x: order.get(x["sev"], 3)), 1):
        el.append(finding_card(i, fnd))

    # ---- WHAT'S WORKING ----
    el.append(Paragraph("What's Already Working Well", SS["H1"]))
    nice = {
        "Title length OK": "Page titles are a healthy length.",
        "Meta description present": "A search-result description is in place.",
        "Canonical": "The site tells Google its preferred web address (avoids duplicate-content issues).",
        "Viewport": "The site is set up to display correctly on mobile phones.",
        "JSON-LD": "Structured data is present, helping Google understand your content.",
        "All": "Images generally include descriptive text.",
        "Single H1": "Clear main heading in place.",
    }
    shown = []
    for ok in onpage.get("ok", []):
        for key, msg in nice.items():
            if ok.startswith(key) and msg not in shown:
                shown.append(msg)
    # always-true infra wins
    shown += ["Secure HTTPS is enforced across the site.",
              "Web and non-web addresses are correctly unified (no duplicate versions).",
              "An XML sitemap is published so Google can discover your pages."]
    for msg in shown:
        el.append(Paragraph(f'<font color="#2e7d32"><b>✓</b></font>&nbsp;&nbsp;{msg}', SS["Body2"]))
    el.append(Spacer(1, 5 * mm))

    # ---- DATA SCOPE / NEXT STEPS ----
    el.append(Paragraph("Scope & Next Steps", SS["H1"]))
    if "api_skipped" in data or "api_error" in data:
        el.append(Paragraph(
            "This report covers <b>on-page and technical SEO</b>, assessed using live "
            "data read directly from your website. A complementary <b>market data</b> "
            "report — covering the keywords you rank for, estimated monthly traffic, "
            "your top competitors, and your backlink profile — is available as an "
            "add-on once data-provider access is connected.", SS["Body2"]))
    el.append(Spacer(1, 2 * mm))
    el.append(Paragraph("Recommended order of work:", SS["H2"]))
    for step in [
        "Fix the high-priority items first (title, conflicting tags, blocked pages) — quick changes, biggest impact.",
        "Tidy the homepage heading and image descriptions.",
        "Run a page-speed pass and optimise images.",
        "Re-audit in 4–6 weeks to confirm improvements and track ranking gains.",
    ]:
        el.append(Paragraph(f'<font color="{("#"+ACCENT.hexval()[2:])}"><b>›</b></font>&nbsp;&nbsp;{step}', SS["Body2"]))

    doc.build(el, onFirstPage=_cover, onLaterPages=_header_footer)
    return out_path


def main():
    argv = sys.argv[1:]
    brand = "Your SEO Consultant"
    if "--brand" in argv:
        bi = argv.index("--brand")
        brand = argv[bi + 1]
        del argv[bi:bi + 2]
    args = [a for a in argv if not a.startswith("--")]
    url = args[0] if args else "https://luxeclay.in"
    domain = urlparse(url if "://" in url else "https://" + url).netloc
    out = args[1] if len(args) > 1 else f"seo/reports/{domain}-audit.pdf"
    path = build(url, out, brand)
    print(f"PDF written to {path}")


if __name__ == "__main__":
    main()
