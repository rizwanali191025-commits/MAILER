#!/usr/bin/env python3
"""
Generate Canva Micro Assignment – all 5 questions as a single PDF.
Run:  python assignment/generate.py
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
import math, os, sys

# ── constants ─────────────────────────────────────────────────────────────────
W, H     = 1240, 1754          # A4 @ 150 DPI
SANS     = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_B   = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
SANS_I   = "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"
SERIF    = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
SERIF_B  = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"

def F(path, size):
    return ImageFont.truetype(path, size)

# ── colour palette ────────────────────────────────────────────────────────────
TEAL        = (0,   150, 136)
DEEP_TEAL   = (0,    77,  64)
CYAN_LIGHT  = (100, 210, 200)
CORAL       = (231,  76,  60)
GOLD        = (212, 175,  55)
GOLD_LIGHT  = (255, 215,   0)
CREAM       = (255, 252, 235)
OFF_WHITE   = (245, 245, 245)
DARK_NAVY   = ( 15,  25,  50)
MID_NAVY    = ( 28,  48,  90)
PURPLE      = (103,  58, 183)
PURPLE_DARK = ( 49,  27, 146)
ROSE        = (233,  30,  99)
ROSE_LIGHT  = (255, 100, 150)
SAGE        = ( 88, 129,  87)
SAGE_LIGHT  = (163, 196, 163)
WARM_WHITE  = (255, 253, 248)
CHARCOAL    = ( 44,  62,  80)
SILVER      = (189, 195, 199)
ORANGE      = (243, 156,  18)
WHITE       = (255, 255, 255)
BLACK       = ( 20,  20,  20)

PAGES = []

# ── helpers ───────────────────────────────────────────────────────────────────
def new_page(bg=WHITE):
    return Image.new("RGB", (W, H), bg)

def grad(c1, c2, vertical=True):
    img = new_page()
    draw = ImageDraw.Draw(img)
    n = H if vertical else W
    for i in range(n):
        t = i / n
        col = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
        if vertical:
            draw.line([(0, i), (W, i)], fill=col)
        else:
            draw.line([(i, 0), (i, H)], fill=col)
    return img

def diag_grad(c1, c2):
    img = new_page()
    draw = ImageDraw.Draw(img)
    for i in range(W + H):
        t = i / (W + H)
        col = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
        draw.line([(max(0, i - H), min(i, H)), (min(i, W), max(0, i - W))], fill=col)
    return img

def paste_alpha(base, layer, pos=(0, 0)):
    base.paste(layer, pos, layer if layer.mode == 'RGBA' else None)

def tcx(draw, y, text, font, color, w=W, stroke=0, sc=None):
    """Draw text centred horizontally."""
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    x  = (w - tw) // 2
    if stroke and sc:
        draw.text((x, y), text, font=font, fill=sc, stroke_width=stroke, stroke_fill=sc)
    draw.text((x, y), text, font=font, fill=color)
    return bb[3] - bb[1]

def save(img):
    PAGES.append(img.copy())

def draw_circle(draw, cx, cy, r, fill, outline=None, ow=2):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline, width=ow)

def rr(draw, x0, y0, x1, y1, r, fill, outline=None, ow=2):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill, outline=outline, width=ow)

def wave(draw, y, color, amplitude=40, frequency=2, fill_to_bottom=False):
    pts = []
    for x in range(W + 1):
        wy = int(y + amplitude * math.sin(2 * math.pi * frequency * x / W))
        pts.append((x, wy))
    if fill_to_bottom:
        pts = [(0, H)] + pts + [(W, H)]
        draw.polygon(pts, fill=color)
    else:
        draw.line(pts, fill=color, width=3)

def label_badge(draw, x, y, text, font, bg, fg=WHITE, pad_x=24, pad_y=10, r=20):
    bb  = draw.textbbox((0, 0), text, font=font)
    tw  = bb[2] - bb[0]
    th  = bb[3] - bb[1]
    x1  = x + tw + pad_x * 2
    y1  = y + th + pad_y * 2
    rr(draw, x, y, x1, y1, r, fill=bg)
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=fg)
    return x1, y1

def section_card(draw, x, y, w, h, title, lines, title_bg, body_bg=WARM_WHITE, r=18):
    rr(draw, x, y, x + w, y + h, r, fill=body_bg, outline=title_bg, ow=3)
    rr(draw, x, y, x + w, y + 64, r, fill=title_bg)
    draw.rectangle([x, y + 40, x + w, y + 64], fill=title_bg)
    tf = F(SANS_B, 26)
    bb = draw.textbbox((0,0), title, font=tf)
    tx = x + (w - (bb[2] - bb[0])) // 2
    draw.text((tx, y + 14), title, font=tf, fill=WHITE)
    lf = F(SANS, 22)
    ly = y + 78
    for line in lines:
        draw.text((x + 24, ly), line, font=lf, fill=CHARCOAL)
        ly += 34

# ══════════════════════════════════════════════════════════════════════════════
#  Q1 — TRAVEL BROCHURE: BALI  (2 pages)
# ══════════════════════════════════════════════════════════════════════════════

def q1_cover():
    img  = grad(DEEP_TEAL, (0, 128, 128))
    draw = ImageDraw.Draw(img)

    # ── decorative circles (sun/water) ────────────────────────────────────────
    for cx, cy, r, alpha in [
        (W // 2, 380, 300, (255,215,0, 18)),
        (W // 2, 380, 220, (255,215,0, 30)),
        (W // 2, 380, 130, (255,215,0, 55)),
    ]:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([cx-r, cy-r, cx+r, cy+r], fill=alpha)
        img = img.convert("RGBA")
        img.alpha_composite(overlay)
        img = img.convert("RGB")

    draw = ImageDraw.Draw(img)

    # ── sun glow ──────────────────────────────────────────────────────────────
    draw_circle(draw, W // 2, 370, 90, GOLD_LIGHT)
    draw_circle(draw, W // 2, 370, 60, (255, 240, 100))

    # ── palm tree (left) ──────────────────────────────────────────────────────
    # trunk
    for i in range(80):
        t = i / 80
        x_shift = int(20 * t)
        draw.line([(120 + x_shift, H - 80 - i * 8), (130 + x_shift, H - 80 - i * 8 + 8)],
                  fill=(101, 67, 33), width=14)
    # leaves
    leaf_pts = [
        [(200, H - 700), (100, H - 780), (20, H - 740)],
        [(200, H - 700), (260, H - 800), (320, H - 770)],
        [(200, H - 700), (180, H - 820), (140, H - 860)],
        [(200, H - 700), (240, H - 840), (300, H - 820)],
        [(200, H - 700), (100, H - 840), (50, H - 810)],
    ]
    for lp in leaf_pts:
        draw.polygon(lp, fill=SAGE)

    # ── wave at bottom ────────────────────────────────────────────────────────
    wave(draw, H - 220, (0, 100, 100, 200), amplitude=50, frequency=2.5, fill_to_bottom=True)
    wave(draw, H - 160, (0, 128, 128), amplitude=35, frequency=3, fill_to_bottom=True)

    # ── main text ─────────────────────────────────────────────────────────────
    tcx(draw, 100, "DISCOVER", F(SANS_B, 56), GOLD_LIGHT)
    tcx(draw, 175, "BALI", F(SANS_B, 200), WHITE, stroke=4, sc=(0,50,50))
    tcx(draw, 390, "I N D O N E S I A", F(SANS_B, 42), GOLD_LIGHT)
    tcx(draw, 460, "Where Dreams Come Alive", F(SANS_I, 34), (200, 255, 230))

    # ── info strip ────────────────────────────────────────────────────────────
    rr(draw, 80, 560, W - 80, 700, 22, fill=(0, 60, 55, 200))
    icons = [("✈", "Best Flights"), ("🌴", "Tropical Paradise"), ("🏄", "Surf & Adventure")]
    for i, (icon, label) in enumerate(icons):
        cx = 180 + i * 370
        draw.text((cx - 30, 575), icon, font=F(SANS_B, 42), fill=GOLD_LIGHT)
        draw.text((cx - 40, 630), label, font=F(SANS, 26), fill=WHITE)

    # ── highlight band ────────────────────────────────────────────────────────
    rr(draw, 80, 750, W - 80, 830, 16, fill=CORAL)
    tcx(draw, 770, "✦  Best time to visit: April – October  ✦", F(SANS_B, 30), WHITE)

    # ── quick facts ───────────────────────────────────────────────────────────
    facts = [
        "🌏  Location: Indonesia, Southeast Asia",
        "🌡  Temperature: 26–32 °C year-round",
        "💱  Currency: Indonesian Rupiah (IDR)",
        "🗣  Language: Balinese & Indonesian",
        "🕌  Famous for: Temples, Rice terraces, Beaches",
    ]
    y = 870
    for fact in facts:
        draw.text((160, y), fact, font=F(SANS, 28), fill=(200, 255, 240))
        y += 52

    # ── footer ────────────────────────────────────────────────────────────────
    draw.rectangle([0, H - 90, W, H], fill=(0, 50, 50))
    tcx(draw, H - 72, "Page 1  ·  Travel Destination Brochure  ·  Q1", F(SANS, 22), SILVER)
    save(img)


def q1_info():
    img  = new_page(CREAM)
    draw = ImageDraw.Draw(img)

    # ── header ────────────────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 120], fill=DEEP_TEAL)
    tcx(draw, 35, "BALI TRAVEL GUIDE", F(SANS_B, 52), WHITE)

    # ── 3 info cards ──────────────────────────────────────────────────────────
    cards = [
        ("GETTING THERE", TEAL, [
            "✈  Direct flights from Dubai ~7 hrs",
            "✈  Ngurah Rai Intl Airport (DPS)",
            "🚌  Taxi / Grab from airport",
            "🛳  Ferries to Gili Islands nearby",
            "💰  Avg flights: $350–$600 return",
        ]),
        ("MUST-SEE SPOTS", CORAL, [
            "🏛  Tanah Lot – Cliff sea temple",
            "🌾  Tegallalang Rice Terraces",
            "🌊  Seminyak & Kuta Beaches",
            "🐒  Sacred Monkey Forest",
            "🎨  Ubud Art Market",
        ]),
        ("EAT, STAY & TIPS", (180, 120, 0), [
            "🍜  Try: Nasi Goreng, Satay, Babi Guling",
            "🏨  Budget hotels from $25/night",
            "🌺  Luxury villas from $120/night",
            "📷  Dress modestly at temples",
            "💳  Carry cash – IDR accepted widely",
        ]),
    ]

    y_start = 160
    for i, (title, color, lines) in enumerate(cards):
        section_card(draw, 60, y_start + i * 480, W - 120, 450,
                     title, lines, color)

    # ── bottom highlight ──────────────────────────────────────────────────────
    rr(draw, 60, H - 210, W - 60, H - 100, 18, fill=DEEP_TEAL)
    tcx(draw, H - 195, "\"Bali is not just a destination — it is a feeling.\"",
        F(SANS_I, 30), WHITE)

    draw.rectangle([0, H - 90, W, H], fill=DEEP_TEAL)
    tcx(draw, H - 72, "Page 2  ·  Travel Destination Brochure  ·  Q1", F(SANS, 22), SILVER)
    save(img)


# ══════════════════════════════════════════════════════════════════════════════
#  Q2 — PRODUCT PACKAGING: "LUMÉE" Vitamin C Serum  (2 pages)
# ══════════════════════════════════════════════════════════════════════════════

def q2_box():
    img  = grad((255, 245, 220), (255, 210, 160))
    draw = ImageDraw.Draw(img)

    # ── outer box outline ─────────────────────────────────────────────────────
    box_x, box_y, box_w, box_h = 120, 80, W - 240, H - 200
    rr(draw, box_x, box_y, box_x + box_w, box_y + box_h, 30,
       fill=WHITE, outline=GOLD, ow=6)

    # ── top colour band ───────────────────────────────────────────────────────
    rr(draw, box_x, box_y, box_x + box_w, box_y + 300, 30, fill=GOLD)
    draw.rectangle([box_x, box_y + 270, box_x + box_w, box_y + 300], fill=GOLD)

    # ── brand name ────────────────────────────────────────────────────────────
    tcx(draw, box_y + 60, "L U M É E", F(SERIF_B, 90), WHITE)
    tcx(draw, box_y + 175, "SKINCARE", F(SANS_B, 34), (255, 240, 180))
    rr(draw, 320, box_y + 230, W - 320, box_y + 270, 12, fill=WHITE)
    tcx(draw, box_y + 237, "ADVANCED FORMULA", F(SANS_B, 24), GOLD)

    # ── product circle emblem ─────────────────────────────────────────────────
    cx, cy = W // 2, box_y + 530
    draw_circle(draw, cx, cy, 180, GOLD)
    draw_circle(draw, cx, cy, 165, (255, 248, 200))
    draw_circle(draw, cx, cy, 150, WHITE)
    tcx(draw, cy - 80, "VITAMIN C", F(SANS_B, 38), CHARCOAL)
    tcx(draw, cy - 20, "BRIGHTENING", F(SANS_B, 30), CHARCOAL)
    tcx(draw, cy + 20, "SERUM", F(SANS_B, 30), CORAL)
    tcx(draw, cy + 70, "20% L-ASCORBIC ACID", F(SANS, 20), CHARCOAL)

    # ── feature badges ────────────────────────────────────────────────────────
    features = ["Cruelty-Free", "Vegan", "Dermatologist Tested", "Fragrance-Free"]
    badge_y = cy + 230
    total_w = sum(draw.textbbox((0,0), f, font=F(SANS_B, 22))[2] for f in features) + len(features) * 60
    bx = (W - total_w) // 2
    for feat in features:
        x1, y1 = label_badge(draw, bx, badge_y, feat, F(SANS_B, 22), SAGE)
        bx = x1 + 20

    # ── product details ───────────────────────────────────────────────────────
    details = [
        ("KEY INGREDIENTS", ["Vitamin C 20%", "Hyaluronic Acid", "Vitamin E", "Ferulic Acid"]),
        ("HOW TO USE",       ["Apply 3–5 drops on clean skin", "Gently pat until absorbed", "Follow with SPF in morning"]),
    ]
    dy = cy + 350
    for col_i, (title, items) in enumerate(details):
        dx = 160 + col_i * 480
        draw.text((dx, dy), title, font=F(SANS_B, 26), fill=GOLD)
        for it in items:
            dy2 = dy + 44 + items.index(it) * 36
            draw.text((dx, dy2), f"· {it}", font=F(SANS, 24), fill=CHARCOAL)

    # ── volume + barcode stub ─────────────────────────────────────────────────
    rr(draw, box_x + 40, box_y + box_h - 160, box_x + box_w - 40, box_y + box_h - 60,
       12, fill=OFF_WHITE, outline=SILVER, ow=2)
    draw.text((box_x + 80, box_y + box_h - 148), "30 mL / 1.0 FL OZ",
              font=F(SANS_B, 28), fill=CHARCOAL)
    draw.text((box_x + box_w - 340, box_y + box_h - 148), "Lot: LM2026-VC",
              font=F(SANS, 24), fill=CHARCOAL)

    draw.rectangle([0, H - 90, W, H], fill=CHARCOAL)
    tcx(draw, H - 72, "Page 3  ·  Product Packaging Design  ·  Q2", F(SANS, 22), SILVER)
    save(img)


def q2_label_promo():
    img  = new_page(WARM_WHITE)
    draw = ImageDraw.Draw(img)

    # ── header ────────────────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 90], fill=CHARCOAL)
    tcx(draw, 22, "LUMÉE  ·  Label & Promotional Material", F(SANS_B, 36), WHITE)

    # ── circular label ────────────────────────────────────────────────────────
    cx, cy = W // 2, 450
    for r, col in [(300, GOLD), (285, WHITE), (270, (255, 248, 210))]:
        draw_circle(draw, cx, cy, r, col)
    draw_circle(draw, cx, cy, 200, WHITE)
    draw_circle(draw, cx, cy, 198, GOLD, outline=GOLD, ow=4)

    tcx(draw, cy - 115, "L U M É E", F(SERIF_B, 60), CHARCOAL)
    tcx(draw, cy - 35,  "Vitamin C", F(SANS_I, 38), CORAL)
    tcx(draw, cy + 20,  "Brightening Serum", F(SANS, 28), CHARCOAL)
    # inner divider line
    draw.line([(cx - 140, cy + 65), (cx + 140, cy + 65)], fill=GOLD, width=2)
    tcx(draw, cy + 78,  "30 mL  ·  1.0 FL OZ", F(SANS, 22), CHARCOAL)

    # outer ring text (arced approximation — linear is fine for this)
    arc_text = "ADVANCED BRIGHTENING FORMULA  ·  DERMATOLOGIST TESTED  ·"
    at_font  = F(SANS, 18)
    bb       = draw.textbbox((0,0), arc_text, font=at_font)
    atw      = bb[2] - bb[0]
    draw.text(((W - atw) // 2, cy + 240), arc_text, font=at_font, fill=GOLD)

    # ── promo card ────────────────────────────────────────────────────────────
    px, py, pw, ph = 60, cy + 320, W - 120, 530
    rr(draw, px, py, px + pw, py + ph, 24, fill=CHARCOAL)
    # gold accent bar
    rr(draw, px, py, px + pw, py + 8, 24, fill=GOLD)
    draw.rectangle([px, py + 4, px + pw, py + 8], fill=GOLD)

    tcx(draw, py + 30, "INTRODUCING LUMÉE", F(SANS_B, 38), GOLD)
    tcx(draw, py + 85, "Vitamin C Brightening Serum", F(SANS_I, 32), WHITE)

    # divider
    draw.line([(px + 80, py + 140), (px + pw - 80, py + 140)], fill=GOLD, width=2)

    benefits = [
        ("✦", "Fades dark spots & hyperpigmentation"),
        ("✦", "Boosts collagen for firm, youthful skin"),
        ("✦", "Shields against environmental damage"),
        ("✦", "Delivers visible glow in just 2 weeks"),
    ]
    by = py + 160
    for icon, text in benefits:
        draw.text((px + 80, by),  icon, font=F(SANS_B, 26), fill=GOLD)
        draw.text((px + 130, by), text, font=F(SANS, 26),   fill=(220, 220, 220))
        by += 52

    rr(draw, px + 200, py + ph - 110, px + pw - 200, py + ph - 50, 24, fill=CORAL)
    tcx(draw, py + ph - 100, "SHOP NOW  →  lumee-skincare.com", F(SANS_B, 26), WHITE)

    draw.rectangle([0, H - 90, W, H], fill=CHARCOAL)
    tcx(draw, H - 72, "Page 4  ·  Product Packaging Design  ·  Q2", F(SANS, 22), SILVER)
    save(img)


# ══════════════════════════════════════════════════════════════════════════════
#  Q3 — BOOK COVER REDESIGN: "Rich Dad Poor Dad"  (1 page)
# ══════════════════════════════════════════════════════════════════════════════

def q3_book_cover():
    img  = grad(DARK_NAVY, (30, 30, 80))
    draw = ImageDraw.Draw(img)

    # ── top accent line ───────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 14], fill=GOLD)

    # ── large "$" symbol background watermark ─────────────────────────────────
    wm_font = F(SERIF_B, 700)
    bb  = draw.textbbox((0,0), "$", font=wm_font)
    wmx = (W - (bb[2]-bb[0])) // 2 - 30
    draw.text((wmx, 200), "$", font=wm_font, fill=(30, 30, 80))

    # ── two house silhouettes ─────────────────────────────────────────────────
    # Small house (poor dad)
    house_pts = [(180, 860), (300, 720), (420, 860), (420, 1000), (180, 1000)]
    draw.polygon(house_pts, fill=(60, 60, 100))
    draw.rectangle([240, 900, 290, 1000], fill=DARK_NAVY)   # door

    # Large house (rich dad)
    big_pts = [(660, 820), (870, 580), (1080, 820), (1080, 1040), (660, 1040)]
    draw.polygon(big_pts, fill=GOLD)
    draw.polygon([(660,820),(870,580),(1080,820)], fill=(180,140,20))   # roof
    draw.rectangle([840, 900, 900, 1040], fill=DARK_NAVY)   # door
    # windows
    for wx in [700, 980]:
        draw.rectangle([wx, 860, wx+70, 930], fill=(255, 240, 100))

    # ground line
    draw.rectangle([60, 1040, W-60, 1055], fill=GOLD)

    # ── title ─────────────────────────────────────────────────────────────────
    tcx(draw, 100, "RICH DAD", F(SANS_B, 110), GOLD, stroke=3, sc=(10,10,40))
    tcx(draw, 225, "POOR DAD", F(SANS_B, 110), WHITE, stroke=3, sc=(10,10,40))

    # ── subtitle banner ───────────────────────────────────────────────────────
    rr(draw, 80, 360, W-80, 430, 12, fill=CORAL)
    tcx(draw, 372, "What the Rich Teach Their Kids About Money", F(SANS_I, 28), WHITE)

    # ── author ────────────────────────────────────────────────────────────────
    tcx(draw, 1100, "ROBERT T. KIYOSAKI", F(SANS_B, 40), GOLD)
    tcx(draw, 1160, "with Sharon Lechter, C.P.A.", F(SANS_I, 28), SILVER)

    # ── tagline ───────────────────────────────────────────────────────────────
    tcx(draw, 1240, "#1 Personal Finance Book of All Time", F(SANS, 28), (180, 200, 255))

    # ── "20th Anniversary Edition" badge ─────────────────────────────────────
    draw_circle(draw, W - 160, 160, 100, CORAL)
    draw_circle(draw, W - 160, 160,  93, (200, 50, 20))
    tcx(draw, 90,  "20th",     F(SANS_B, 28), WHITE, w=W - 20)
    tcx(draw, 130, "ANNIVER-", F(SANS_B, 20), WHITE, w=W - 20)
    tcx(draw, 158, "SARY",     F(SANS_B, 20), WHITE, w=W - 20)
    tcx(draw, 186, "EDITION",  F(SANS_B, 18), GOLD,  w=W - 20)

    # ── bottom strip ─────────────────────────────────────────────────────────
    draw.rectangle([0, H - 90, W, H], fill=GOLD)
    tcx(draw, H - 72, "Page 5  ·  Book Cover Redesign  ·  Q3", F(SANS_B, 22), DARK_NAVY)
    save(img)


# ══════════════════════════════════════════════════════════════════════════════
#  Q4 — EVENT INVITATION & PROMOTION: "TechPulse Summit 2026"  (2 pages)
# ══════════════════════════════════════════════════════════════════════════════

def q4_invitation():
    img  = grad(PURPLE_DARK, (20, 20, 80))
    draw = ImageDraw.Draw(img)

    # ── geometric circuit-board lines ─────────────────────────────────────────
    line_col = (80, 60, 150)
    for y in range(0, H, 80):
        draw.line([(0, y), (W, y)], fill=line_col, width=1)
    for x in range(0, W, 80):
        draw.line([(x, 0), (x, H)], fill=line_col, width=1)
    for cx, cy, r in [(100,200,30),(400,500,20),(900,300,25),(1100,700,18),(300,1200,22),(800,1400,28)]:
        draw_circle(draw, cx, cy, r, (100, 80, 180))
        draw_circle(draw, cx, cy, r - 8, PURPLE_DARK)

    # ── YOU'RE INVITED badge ──────────────────────────────────────────────────
    rr(draw, 340, 90, W - 340, 165, 30, fill=ROSE)
    tcx(draw, 105, "✦  YOU'RE INVITED  ✦", F(SANS_B, 36), WHITE)

    # ── event name ────────────────────────────────────────────────────────────
    tcx(draw, 210, "TECHPULSE", F(SANS_B, 130), WHITE, stroke=4, sc=(60,30,120))
    tcx(draw, 360, "SUMMIT 2026", F(SANS_B, 70), (200, 170, 255))

    # ── glowing orb ───────────────────────────────────────────────────────────
    for r, a in [(160, 15), (120, 30), (80, 60), (50, 120)]:
        overlay = Image.new("RGBA", (W, H), (0,0,0,0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([W//2 - r, 510 - r, W//2 + r, 510 + r], fill=(150, 100, 255, a))
        img = img.convert("RGBA"); img.alpha_composite(overlay); img = img.convert("RGB")
    draw = ImageDraw.Draw(img)
    draw_circle(draw, W//2, 510, 40, (200, 170, 255))

    # ── details box ───────────────────────────────────────────────────────────
    rr(draw, 100, 640, W - 100, 1080, 24, fill=(40, 20, 90), outline=(150, 100, 255), ow=3)

    details = [
        ("📅", "Date",     "Saturday, 15 August 2026"),
        ("🕗", "Time",     "9:00 AM – 6:00 PM"),
        ("📍", "Venue",    "Dubai World Trade Centre, Hall 4"),
        ("🎤", "Speakers", "20+ Industry Leaders"),
        ("🎟", "Tickets",  "Free — Register at techpulse.io"),
    ]
    dy = 670
    for emoji, label, value in details:
        draw.text((140, dy), emoji,            font=F(SANS, 36), fill=WHITE)
        draw.text((220, dy), f"{label}:",      font=F(SANS_B, 30), fill=(200, 170, 255))
        draw.text((220, dy + 40), value,       font=F(SANS, 30), fill=WHITE)
        dy += 88

    # ── topic tags ────────────────────────────────────────────────────────────
    tcx(draw, 1120, "TOPICS COVERED", F(SANS_B, 30), (200, 170, 255))
    tags = ["AI & Machine Learning", "Cybersecurity", "Cloud Computing",
            "Web3 & Blockchain", "Product Design", "Startup Funding"]
    tx = 100
    ty = 1165
    for tag in tags:
        tf = F(SANS_B, 22)
        bb = draw.textbbox((0,0), tag, font=tf)
        tw = bb[2] - bb[0]
        if tx + tw + 60 > W - 80:
            tx = 100; ty += 56
        rr(draw, tx, ty, tx + tw + 40, ty + 44, 22, fill=PURPLE)
        draw.text((tx + 20, ty + 8), tag, font=tf, fill=WHITE)
        tx += tw + 60

    # ── footer ────────────────────────────────────────────────────────────────
    rr(draw, 80, H - 200, W - 80, H - 110, 20, fill=ROSE)
    tcx(draw, H - 190, "Register now: techpulse.io  |  info@techpulse.io",
        F(SANS_B, 28), WHITE)
    draw.rectangle([0, H - 90, W, H], fill=(30, 10, 70))
    tcx(draw, H - 72, "Page 6  ·  Event Invitation & Promotion  ·  Q4", F(SANS, 22), SILVER)
    save(img)


def q4_promo():
    img  = diag_grad((20, 20, 80), (150, 30, 100))
    draw = ImageDraw.Draw(img)

    # ── top flash bar ─────────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 18], fill=GOLD_LIGHT)

    # ── starburst ─────────────────────────────────────────────────────────────
    for angle in range(0, 360, 15):
        rad = math.radians(angle)
        x1  = W // 2 + int(250 * math.cos(rad))
        y1  = 400     + int(250 * math.sin(rad))
        x2  = W // 2 + int(370 * math.cos(rad))
        y2  = 400     + int(370 * math.sin(rad))
        draw.line([(x1, y1), (x2, y2)], fill=(255, 200, 0, 80), width=3)

    draw_circle(draw, W//2, 400, 230, (100, 50, 180))
    draw_circle(draw, W//2, 400, 210, (130, 70, 210))

    tcx(draw, 290, "TECH", F(SANS_B, 120), WHITE, stroke=3, sc=(50,20,100))
    tcx(draw, 415, "PULSE", F(SANS_B, 120), GOLD_LIGHT, stroke=3, sc=(100,80,0))

    # ── sub headline ──────────────────────────────────────────────────────────
    tcx(draw, 710, "The Future of Technology  ·  Today", F(SANS_I, 36), (220, 200, 255))

    # ── 3 highlight cards ─────────────────────────────────────────────────────
    highlights = [
        (ROSE,   "20+",  "Expert\nSpeakers"),
        (TEAL,   "500+", "Attendees\nExpected"),
        (ORANGE, "12+",  "Interactive\nWorkshops"),
    ]
    card_w = 280
    gap    = (W - 3 * card_w - 120) // 2
    for i, (col, num, label) in enumerate(highlights):
        cx = 60 + i * (card_w + gap)
        rr(draw, cx, 810, cx + card_w, 1020, 20, fill=col)
        tcx(draw, 840, num,   F(SANS_B, 62), WHITE, w=cx + card_w + (cx if i == 0 else 0))
        # simple two-line label:
        lines = label.split("\n")
        for j, ln in enumerate(lines):
            tcx(draw, 920 + j * 36, ln, F(SANS, 26), WHITE,
                w=2 * cx + card_w)

    # ── date & venue strip ────────────────────────────────────────────────────
    rr(draw, 80, 1080, W - 80, 1190, 18, fill=(255,255,255,40))
    tcx(draw, 1100, "📅  15 August 2026   |   📍  Dubai World Trade Centre",
        F(SANS_B, 32), WHITE)

    # ── CTA button ────────────────────────────────────────────────────────────
    rr(draw, 300, 1230, W - 300, 1340, 30, fill=GOLD_LIGHT)
    tcx(draw, 1255, "REGISTER FREE  →  techpulse.io", F(SANS_B, 36), DARK_NAVY)

    # ── social line ───────────────────────────────────────────────────────────
    tcx(draw, 1380, "@TechPulseSummit  ·  #TechPulse2026", F(SANS, 28), (200, 200, 255))

    # ── hashtag wall ──────────────────────────────────────────────────────────
    htags = ["#AI", "#Web3", "#Cloud", "#Cyber", "#Innovation", "#StartupLife"]
    htx = 120
    for ht in htags:
        tf = F(SANS_B, 24)
        bb = draw.textbbox((0,0), ht, font=tf)
        draw.text((htx, 1450), ht, font=tf, fill=(180, 150, 255))
        htx += bb[2] - bb[0] + 30

    draw.rectangle([0, H - 90, W, H], fill=(20, 10, 60))
    tcx(draw, H - 72, "Page 7  ·  Event Invitation & Promotion  ·  Q4", F(SANS, 22), SILVER)
    save(img)


# ══════════════════════════════════════════════════════════════════════════════
#  Q5 — PRESENTATION: "Mastering Email Marketing" (5 slides)
# ══════════════════════════════════════════════════════════════════════════════

SLIDE_BG   = (245, 247, 252)
SLIDE_HEAD = (26, 54, 110)
ACCENT     = (41, 128, 185)
ACCENT2    = (231, 76, 60)
TEXT_DARK  = (44, 62, 80)

def slide_shell(title, page_n):
    img  = new_page(SLIDE_BG)
    draw = ImageDraw.Draw(img)
    # top header bar
    draw.rectangle([0, 0, W, 110], fill=SLIDE_HEAD)
    draw.rectangle([0, 108, W, 120], fill=GOLD_LIGHT)
    # title text
    draw.text((60, 25), title, font=F(SANS_B, 46), fill=WHITE)
    # footer
    draw.rectangle([0, H - 80, W, H], fill=SLIDE_HEAD)
    tcx(draw, H - 64, f"Mastering Email Marketing  ·  Slide {page_n}/5", F(SANS, 22), SILVER)
    return img, draw

def q5_slide1():
    img  = grad(SLIDE_HEAD, ACCENT)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, H - 80, W, H], fill=(15, 30, 70))

    tcx(draw, 80, "MASTERING", F(SANS_B, 70), GOLD_LIGHT)
    tcx(draw, 165, "EMAIL MARKETING", F(SANS_B, 90), WHITE)
    draw.line([(200, 285), (W - 200, 285)], fill=GOLD_LIGHT, width=4)
    tcx(draw, 310, "Strategies, Tools & Best Practices for 2026", F(SANS_I, 38), (200, 220, 255))

    # stats preview
    stats = [("4200%", "Average ROI"), ("4B+", "Email users worldwide"), ("347B", "Emails sent daily")]
    sy = 460
    for i, (num, label) in enumerate(stats):
        bx = 100 + i * 380
        rr(draw, bx, sy, bx + 300, sy + 180, 18, fill=(255,255,255,30))
        tcx(draw, sy + 20,  num,   F(SANS_B, 62), GOLD_LIGHT,  w=2 * bx + 300)
        tcx(draw, sy + 100, label, F(SANS, 26),   WHITE,        w=2 * bx + 300)

    tcx(draw, 700, "Prepared by: Rizwan Ali", F(SANS_I, 30), (200, 220, 255))
    tcx(draw, 750, "Graphic Designing Micro Assignment  ·  Q5", F(SANS, 24), SILVER)

    draw.rectangle([0, H - 80, W, H], fill=(15, 30, 70))
    tcx(draw, H - 64, "Mastering Email Marketing  ·  Slide 1/5", F(SANS, 22), SILVER)
    save(img)


def q5_slide2():
    img, draw = slide_shell("What is Email Marketing?", 2)

    tcx(draw, 150, "Definition & Overview", F(SANS_B, 44), SLIDE_HEAD)
    draw.line([(80, 208), (W - 80, 208)], fill=ACCENT, width=3)

    defn = (
        "Email marketing is a form of digital marketing that uses emails\n"
        "to promote products or services, build relationships with potential\n"
        "customers, and keep current customers informed and engaged."
    )
    y = 230
    for line in defn.split("\n"):
        tcx(draw, y, line, F(SANS_I, 30), TEXT_DARK)
        y += 48

    points = [
        ("📧", "Direct Channel",    "Reaches customers directly in their inbox."),
        ("🎯", "Highly Targeted",   "Segment audiences for personalised messages."),
        ("📊", "Measurable",        "Track open rates, clicks, and conversions."),
        ("💰", "Cost-Effective",    "$36 return for every $1 spent on average."),
    ]
    py = 420
    for emoji, title, desc in points:
        rr(draw, 80, py, W - 80, py + 90, 14, fill=WHITE, outline=ACCENT, ow=2)
        draw.text((110, py + 20), emoji, font=F(SANS, 40), fill=ACCENT)
        draw.text((180, py + 20), title, font=F(SANS_B, 30), fill=SLIDE_HEAD)
        draw.text((180, py + 54), desc,  font=F(SANS, 26),   fill=TEXT_DARK)
        py += 110

    # Types strip
    rr(draw, 80, H - 280, W - 80, H - 140, 16, fill=ACCENT)
    tcx(draw, H - 268, "Types:  Newsletter  ·  Promotional  ·  Transactional  ·  Re-engagement",
        F(SANS_B, 28), WHITE)
    save(img)


def q5_slide3():
    img, draw = slide_shell("Key Statistics & Why It Matters", 3)

    tcx(draw, 148, "Email Marketing in Numbers — 2026", F(SANS_B, 40), SLIDE_HEAD)
    draw.line([(80, 202), (W - 80, 202)], fill=ACCENT, width=3)

    stats_cards = [
        (ACCENT,   "4,200%",  "Average ROI",         "($42 for every $1 spent)"),
        (ACCENT2,  "81%",     "SMBs use email",       "as primary channel"),
        (SAGE,     "47%",     "Open rate boost",      "from personalised subject"),
        (PURPLE,   "60%",     "Consumers prefer",     "email for promotions"),
        (ORANGE,   "3.9B",    "Daily email users",    "by end of 2026"),
        (GOLD,     "26%",     "Higher open rates",    "with segmented campaigns"),
    ]
    col_w = (W - 160) // 3
    for i, (col, num, label, sub) in enumerate(stats_cards):
        row = i // 3; c = i % 3
        bx  = 80 + c * (col_w + 20)
        by  = 240 + row * 240
        rr(draw, bx, by, bx + col_w, by + 210, 16, fill=col)
        tcx(draw, by + 16,  num,   F(SANS_B, 58), WHITE, w=2 * bx + col_w)
        tcx(draw, by + 90,  label, F(SANS_B, 24), WHITE, w=2 * bx + col_w)
        tcx(draw, by + 126, sub,   F(SANS_I, 22), (220,230,255) if col != GOLD else DARK_NAVY, w=2 * bx + col_w)

    tcx(draw, H - 200, "Source: HubSpot, Statista, Mailchimp 2026 Email Marketing Report",
        F(SANS_I, 24), (120, 130, 150))
    save(img)


def q5_slide4():
    img, draw = slide_shell("Best Practices for 2026", 4)

    tcx(draw, 148, "Proven Strategies That Drive Results", F(SANS_B, 40), SLIDE_HEAD)
    draw.line([(80, 202), (W - 80, 202)], fill=ACCENT2, width=3)

    practices = [
        ("1", ACCENT,   "Personalise Everything",
         "Use recipient names, behaviour data, and dynamic content blocks\n"
         "with {{tags}} to tailor each message uniquely."),
        ("2", ACCENT2,  "Optimise Subject Lines",
         "Keep subject lines under 50 characters. Use numbers, questions,\n"
         "and emojis to boost open rates by up to 47%."),
        ("3", SAGE,     "Mobile-First Design",
         "Over 60% of emails are opened on mobile. Use single-column\n"
         "layouts, large fonts (min 14px), and CTA buttons ≥ 44px."),
        ("4", PURPLE,   "A/B Test Continuously",
         "Test subject lines, send times, CTAs, and visuals. Even a 5%\n"
         "improvement in CTR compounds significantly over 1000 sends."),
    ]
    py = 240
    for num, col, title, desc in practices:
        rr(draw, 80, py, W - 80, py + 145, 16, fill=WHITE, outline=col, ow=3)
        draw_circle(draw, 130, py + 72, 36, col)
        draw.text((118, py + 52), num, font=F(SANS_B, 36), fill=WHITE)
        draw.text((200, py + 20), title, font=F(SANS_B, 30), fill=col)
        for j, line in enumerate(desc.split("\n")):
            draw.text((200, py + 62 + j * 34), line, font=F(SANS, 24), fill=TEXT_DARK)
        py += 165

    save(img)


def q5_slide5():
    img, draw = slide_shell("Conclusion & Tools", 5)

    tcx(draw, 148, "Takeaways & Recommended Tools", F(SANS_B, 40), SLIDE_HEAD)
    draw.line([(80, 202), (W - 80, 202)], fill=GOLD_LIGHT, width=3)

    takeaways = [
        "Email marketing remains the highest-ROI digital channel in 2026.",
        "Personalisation and segmentation are no longer optional — they're essential.",
        "Automation saves time; pair it with human-crafted, authentic copy.",
        "Always A/B test, analyse metrics, and iterate every campaign.",
    ]
    ty = 240
    for ta in takeaways:
        draw.text((120, ty), "✦", font=F(SANS_B, 30), fill=GOLD_LIGHT)
        draw.text((170, ty), ta,   font=F(SANS, 28),   fill=TEXT_DARK)
        ty += 58

    # Tools grid
    tcx(draw, ty + 20, "Top Tools", F(SANS_B, 38), SLIDE_HEAD)
    tools = [
        (ACCENT,  "Mailchimp"),
        (ACCENT2, "Klaviyo"),
        (SAGE,    "HubSpot"),
        (PURPLE,  "ActiveCampaign"),
        (ORANGE,  "ConvertKit"),
        (GOLD,    "Bulk Gmail Mailer ★"),
    ]
    col_w = (W - 160) // 3
    for i, (col, name) in enumerate(tools):
        r = i // 3; c = i % 3
        bx = 80 + c * (col_w + 20)
        by = ty + 80 + r * 100
        rr(draw, bx, by, bx + col_w, by + 70, 14, fill=col)
        tcx(draw, by + 18, name, F(SANS_B, 26), WHITE, w=2 * bx + col_w)

    rr(draw, 80, H - 260, W - 80, H - 140, 18, fill=SLIDE_HEAD)
    tcx(draw, H - 248, "Thank you!  ·  Questions?  ·  rizwanali191025@gmail.com",
        F(SANS_B, 30), WHITE)
    save(img)


# ══════════════════════════════════════════════════════════════════════════════
#  COVER PAGE
# ══════════════════════════════════════════════════════════════════════════════

def cover_page():
    img  = grad(DARK_NAVY, MID_NAVY)
    draw = ImageDraw.Draw(img)

    # accent dots
    for cx, cy, r in [(60,60,40),(W-60,60,40),(60,H-60,40),(W-60,H-60,40)]:
        draw_circle(draw, cx, cy, r, GOLD)
        draw_circle(draw, cx, cy, r-8, DARK_NAVY)

    draw.rectangle([0, 0, W, 16], fill=GOLD)
    draw.rectangle([0, H-16, W, H], fill=GOLD)

    tcx(draw, 100, "Micro Assignment", F(SANS_I, 46), SILVER)
    tcx(draw, 175, "Graphic Designing", F(SANS_B, 80), WHITE)
    tcx(draw, 280, "(Canva)", F(SANS_I, 56), GOLD_LIGHT)

    draw.line([(200, 370), (W-200, 370)], fill=GOLD, width=3)

    sections = [
        ("Q1", "Travel Destination Brochure",    "Bali, Indonesia"),
        ("Q2", "Product Packaging Design",        "LUMÉE Vitamin C Serum"),
        ("Q3", "Book Cover Redesign",             "Rich Dad Poor Dad"),
        ("Q4", "Event Invitation & Promotion",    "TechPulse Summit 2026"),
        ("Q5", "Presentation (5 Slides)",         "Mastering Email Marketing"),
    ]
    sy = 420
    for q, title, sub in sections:
        rr(draw, 120, sy, W-120, sy+100, 14, fill=(30,45,80), outline=GOLD, ow=2)
        rr(draw, 120, sy, 200,   sy+100, 14, fill=GOLD)
        draw.rectangle([170, sy, 200, sy+100], fill=GOLD)
        draw.text((134, sy+28), q, font=F(SANS_B, 38), fill=DARK_NAVY)
        draw.text((220, sy+16), title, font=F(SANS_B, 32), fill=WHITE)
        draw.text((220, sy+58), sub,   font=F(SANS_I, 26), fill=SILVER)
        sy += 124

    draw.line([(200, sy+20), (W-200, sy+20)], fill=GOLD, width=2)
    tcx(draw, sy+40, "Submitted by: Rizwan Ali", F(SANS_B, 34), WHITE)
    tcx(draw, sy+90, "rizwanali191025@gmail.com", F(SANS_I, 28), GOLD_LIGHT)
    save(img)


# ══════════════════════════════════════════════════════════════════════════════
#  ASSEMBLE PDF
# ══════════════════════════════════════════════════════════════════════════════

def build_pdf(output_path: str):
    print("Generating pages…")
    cover_page()
    print("  Cover page done")
    q1_cover(); print("  Q1 page 1 done")
    q1_info();  print("  Q1 page 2 done")
    q2_box();   print("  Q2 page 1 done")
    q2_label_promo(); print("  Q2 page 2 done")
    q3_book_cover();  print("  Q3 done")
    q4_invitation();  print("  Q4 page 1 done")
    q4_promo();       print("  Q4 page 2 done")
    q5_slide1(); print("  Q5 slide 1 done")
    q5_slide2(); print("  Q5 slide 2 done")
    q5_slide3(); print("  Q5 slide 3 done")
    q5_slide4(); print("  Q5 slide 4 done")
    q5_slide5(); print("  Q5 slide 5 done")

    print(f"\nSaving {len(PAGES)} pages → {output_path}")
    first = PAGES[0].convert("RGB")
    rest  = [p.convert("RGB") for p in PAGES[1:]]
    first.save(output_path, "PDF", resolution=150, save_all=True, append_images=rest)
    print("Done.")


if __name__ == "__main__":
    out = Path(__file__).parent / "Canva_Micro_Assignment_Rizwan_Ali.pdf"
    build_pdf(str(out))
