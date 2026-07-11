# azimkhan.in — Fixed Files

Corrected versions of every page, pulled live from https://azimkhan.in and
patched for the issues found in the audit. Content, styling and images are
untouched — only the changes below were made.

## Deploy

1. Upload `index.html`, `services.html`, `about.html`, `portfolio.html`,
   `contact.html`, and `sitemap.xml` to your site root, overwriting the
   existing files.
2. Merge `.htaccess` into your site root (see the comment inside the file —
   don't overwrite an existing `.htaccess`, just add the two rewrite blocks).
3. Verify: `http://azimkhan.in`, `https://www.azimkhan.in`, and
   `https://azimkhan.in/index.html` should all 301-redirect to
   `https://azimkhan.in/`.

## What changed, per file

**index.html**
- Title shortened: 94 → 41 characters
- Meta description shortened to 154 characters
- Canonical + `og:url` now point to `https://azimkhan.in/` (was `/index.html`)
- Added Twitter Card tags (was missing)
- Nav links point to `/` instead of `index.html`

**services.html**
- Title shortened: 70 → 45 characters
- Added Twitter Card tags
- Added `BreadcrumbList` schema
- Added `Service` schema listing all 6 service lines
- Nav links point to `/` instead of `index.html`

**about.html / portfolio.html / contact.html**
- Added Twitter Card tags
- Added `BreadcrumbList` schema
- Nav links point to `/` instead of `index.html`

**sitemap.xml**
- Homepage entry changed from `/index.html` to `/`

**.htaccess**
- 301 redirect: `www.azimkhan.in` → `azimkhan.in`
- 301 redirect: `/index.html` → `/`
