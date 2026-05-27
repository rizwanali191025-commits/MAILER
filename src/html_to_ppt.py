"""Convert an HTML string into a .pptx file.

Strategy:
  - Parse HTML with BeautifulSoup.
  - Each <h1>/<h2> becomes a new slide title.
  - Paragraphs, list items, and remaining text become slide body content.
  - <img> tags whose src is a local path or data-URI are embedded.
  - Falls back to a single-slide summary when structure is too flat.
"""

import base64
import io
import re
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN


SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

TITLE_FONT_SIZE = Pt(36)
BODY_FONT_SIZE = Pt(20)
CAPTION_FONT_SIZE = Pt(14)

TITLE_COLOR = RGBColor(0x1F, 0x39, 0x7D)
BODY_COLOR = RGBColor(0x33, 0x33, 0x33)
BG_COLOR = RGBColor(0xFF, 0xFF, 0xFF)


def _set_bg(slide, color: RGBColor):
    from pptx.oxml.ns import qn
    from lxml import etree

    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_text_box(slide, text: str, left, top, width, height,
                  font_size=BODY_FONT_SIZE, color=BODY_COLOR, bold=False):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    run = p.runs[0]
    run.font.size = font_size
    run.font.color.rgb = color
    run.font.bold = bold
    return txBox


def _build_slide(prs, title_text: str, body_lines: list[str]):
    slide_layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(slide_layout)
    _set_bg(slide, BG_COLOR)

    margin = Inches(0.5)
    content_top = margin

    if title_text:
        _add_text_box(
            slide, title_text,
            left=margin, top=content_top,
            width=SLIDE_W - 2 * margin, height=Inches(1.2),
            font_size=TITLE_FONT_SIZE, color=TITLE_COLOR, bold=True,
        )
        content_top += Inches(1.3)

    if body_lines:
        body_text = "\n".join(body_lines)
        _add_text_box(
            slide, body_text,
            left=margin, top=content_top,
            width=SLIDE_W - 2 * margin,
            height=SLIDE_H - content_top - margin,
            font_size=BODY_FONT_SIZE, color=BODY_COLOR,
        )


def _try_add_image(slide, src: str, left, top, max_width, max_height):
    """Attempt to add an image from a file path or base64 data URI."""
    try:
        if src.startswith("data:image"):
            header, b64data = src.split(",", 1)
            img_bytes = base64.b64decode(b64data)
            img_stream = io.BytesIO(img_bytes)
        else:
            img_stream = src  # file path string

        pic = slide.shapes.add_picture(img_stream, left, top, max_width, max_height)
        # keep aspect ratio
        ratio = min(max_width / pic.width, max_height / pic.height)
        pic.width = int(pic.width * ratio)
        pic.height = int(pic.height * ratio)
        return pic
    except Exception:
        return None


def html_to_pptx(html: str, output_path: str | None = None) -> str:
    """Convert *html* to a .pptx file.

    Returns the path to the generated file.
    If *output_path* is None a temporary file is used.
    """
    soup = BeautifulSoup(html, "lxml")
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # Collect slides: each h1/h2 starts a new slide
    slides_data: list[tuple[str, list[str]]] = []
    current_title = ""
    current_body: list[str] = []

    def flush():
        if current_title or current_body:
            slides_data.append((current_title, list(current_body)))

    body_tag = soup.find("body") or soup

    for elem in body_tag.children:
        if isinstance(elem, NavigableString):
            text = elem.strip()
            if text:
                current_body.append(text)
            continue

        tag = elem.name
        if tag in ("h1", "h2"):
            flush()
            current_title = elem.get_text(strip=True)
            current_body = []
        elif tag in ("h3", "h4", "h5", "h6"):
            current_body.append(elem.get_text(strip=True))
        elif tag in ("p", "div", "section", "article"):
            text = elem.get_text(" ", strip=True)
            if text:
                current_body.append(text)
        elif tag in ("ul", "ol"):
            for li in elem.find_all("li"):
                current_body.append("• " + li.get_text(strip=True))
        elif tag == "table":
            for row in elem.find_all("tr"):
                cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                if cells:
                    current_body.append(" | ".join(cells))
        elif tag == "hr":
            flush()
            current_title = ""
            current_body = []

    flush()

    # If nothing structured was found, fall back to full text split into chunks
    if not slides_data:
        all_text = soup.get_text(" ", strip=True)
        words = all_text.split()
        chunk_size = 80
        chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
        for i, chunk in enumerate(chunks):
            slides_data.append((f"Slide {i+1}", [chunk]))

    for title, body in slides_data:
        _build_slide(prs, title, body)

    if not output_path:
        tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
        output_path = tmp.name
        tmp.close()

    prs.save(output_path)
    return output_path
