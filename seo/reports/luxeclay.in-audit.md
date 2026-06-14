# SEO Audit — luxeclay.in

**Date:** 2026-06-14
**Site:** https://luxeclay.in — LuxeClay, handmade polymer-clay jewellery (earrings, hair clips, pendants, studs, co-ord sets), based in India.
**Platform:** WordPress + WooCommerce (Hostinger/LiteSpeed), Yoast SEO.

> Scope note: This report covers the **on-page and technical** audit, which uses
> live data fetched directly from the site (no API key needed). The
> keyword-volume, traffic-estimate, competitor, and backlink sections require
> DataForSEO credentials — add them to `seo/.env` and re-run
> `python3 seo/audit.py https://luxeclay.in` to fill those in.

---

## Technical health snapshot

| Check | Status | Detail |
|-------|--------|--------|
| HTTPS | ✅ | `http://` 301-redirects to `https://` |
| www canonicalisation | ✅ | `www.` 301-redirects to non-www |
| Canonical tag | ✅ | `https://luxeclay.in/` |
| Viewport / mobile meta | ✅ | Present |
| Robots meta | ✅ | `index, follow` |
| XML sitemap | ✅ | `sitemap_index.xml` (Yoast) — 32 products, 11 pages, 3 posts, 5 categories |
| Structured data | ✅ | 4 JSON-LD blocks |
| Page `<title>` | ❌ | `"Home - luxeclay"` — only 15 chars, not keyword-relevant |
| Duplicate meta tags | ❌ | 2× meta description, 3× og:title — plugin/theme conflict |
| Multiple H1 | ⚠️ | Two H1s, one is "FLASH SALE !!" |
| robots.txt vs sitemap | ❌ | `/shop/` is in the product sitemap **and** blocked in robots.txt |
| Image alt text | ⚠️ | 1 of 23 homepage images missing alt |
| Page weight | ⚠️ | Homepage HTML ≈ 697 KB (heavy) |

---

## Priority issues (fix these first)

### 1. Homepage title tag is wasted — **highest impact**
The `<title>` is `Home - luxeclay` (15 chars). The title tag is one of the
strongest on-page ranking signals and it's the clickable headline in Google.
Interestingly, the site's own Open Graph title is already good —
*"Handmade Clay Jewelry India | Cute & Unique Earrings"* — so the SEO title just
isn't being applied to the `<title>` tag.

**Fix:** In Yoast → Search Appearance (or the homepage's Yoast meta box), set the
SEO title to something like
**`Handmade Clay Jewellery India | LuxeClay – Earrings, Studs & Pendants`**
(~55–60 chars). Make sure no theme setting is overriding it.

### 2. Duplicate meta description / Open Graph tags — plugin conflict
The homepage emits the meta description **twice** and `og:title` **three times**.
This is the classic signature of two systems generating SEO tags at once (e.g.
Yoast plus the theme's built-in SEO/social options, or a second SEO plugin).
Search engines may pick the wrong one, and it bloats the page.

**Fix:** Pick **one** source of SEO tags (Yoast) and disable the theme's/other
plugin's meta + Open Graph output. After the change, re-run the audit — og:title
and description counts should drop to 1 each.

### 3. `/shop/` is blocked in robots.txt but listed in the sitemap
`robots.txt` contains `Disallow: /shop/` and `Disallow: /product-category/all-products/`,
yet `/shop/` is included in `product-sitemap.xml`. You're telling Google to crawl
a page you've also told it not to crawl — a direct contradiction that wastes
crawl budget and can suppress your main category/shop landing page.

**Fix:** Decide whether `/shop/` should rank. If yes (usually yes for an
e-commerce store), remove the `Disallow: /shop/` line. If no, remove `/shop/`
from the sitemap instead. Don't keep both.

### 4. Two H1s on the homepage
H1s are `"FLASH SALE !!"` and `"HANDCRAFTED, JUST FOR YOU."`. Neither contains the
core keyword, and there should generally be one H1 per page.

**Fix:** Make a single, keyword-aware H1 (e.g. *"Handmade Clay Jewellery, Crafted
in India"*) and demote the promo/marketing lines to H2.

---

## Quick wins

- **Image alt text:** 1 homepage image is missing `alt`; several others use weak
  alt like "Home" / "auto draft". Rewrite product image alts to describe the item
  (e.g. *"handmade clay marigold stud earrings"*) — helps image search.
- **Page weight (~697 KB HTML):** large for a homepage. Check for unoptimised
  inline content and large images; LiteSpeed Cache is active, so enable image
  optimisation / lazy-load and run a PageSpeed test.
- **Meta description length (137 chars):** fine, but you can extend toward
  ~155 chars to use the full SERP snippet and add a call to action.

---

## What needs DataForSEO (not yet run)

These require credentials in `seo/.env`:

- **Keyword rankings & volumes** — which terms the site ranks for and their
  monthly search volume in India.
- **Organic traffic estimate** — modelled monthly organic visits.
- **Competitor mapping** — other handmade/clay jewellery sites competing for the
  same keywords.
- **Backlink profile** — referring domains and total backlinks.

Once you add credentials, run:

```bash
python3 seo/audit.py https://luxeclay.in > seo/reports/luxeclay.in-full.json
```

and these sections can be filled in.
