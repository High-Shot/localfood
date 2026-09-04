# Gulf Coast Farm

Static site. No framework, no build step for the app itself, no map API key. Leaflet + OpenStreetMap tiles, one JSON file of listings.

Hosted on GitHub Pages: https://gulfcoastfarm.com/

The vendor form has no backend on GitHub Pages. With `SUBMIT_URL` empty in `submit.html` it opens the visitor's email app with the submission prefilled and addressed to `CONTACT_EMAIL`. Set `SUBMIT_URL` to a Formspree endpoint or a Cloudflare Worker running `functions/api/submit.js` (Airtable) when you want submissions to land somewhere automatically.

## What's in here

```
index.html            map app (search, filters, near me, detail sheet)
submit.html           vendor form: add / update / remove a listing
assets/               style.css, app.js, icon.svg
data/listings.json    the directory (161 listings across eight counties)
l/<id>/index.html     one static page per listing for Google (generated)
functions/api/submit.js   Cloudflare Pages Function -> Airtable "Submissions"
scripts/build_data.py     rebuilds the seed JSON from public sources (one-time)
scripts/build_site.py     regenerates l/ pages, sitemap.xml, robots.txt, manifest
scripts/sync_airtable.py  pulls approved Airtable rows into data/listings.json
```

## Launch checklist

1. Airtable: create a base with two tables, `Listings` and `Submissions`. Run `AIRTABLE_TOKEN=... AIRTABLE_BASE=app... python3 scripts/sync_airtable.py --push` once to upload the seed data into `Listings` (creates the columns via typecast). `Submissions` fills itself from the form; add these columns first: Mode, Listing ID, Name, Type, Description, Categories, Products, How to buy, Sells at, Hours, Address, City, County, Pin precision, Phone, Email, Website, Facebook, Instagram, TikTok, Contact name, Contact email, Notes, Consent (checkbox), Status, Submitted at, IP.
2. GitHub Pages (current): Settings > Pages > Deploy from branch `main`, folder `/`. Generated pages are committed, so there is no build step on GitHub. After changing data or templates run `SITE_DOMAIN=high-shot.github.io SITE_PATH=/localfood python3 scripts/build_site.py` and push. When you add a custom domain, rerun with `SITE_DOMAIN=yourdomain.com SITE_PATH=` (empty) and add a `CNAME` file.
   Cloudflare (optional, only if you want the Airtable form): create a Pages project from the repo, build command `SITE_DOMAIN=yourdomain.com python3 scripts/build_site.py`, output `/`, env vars `AIRTABLE_TOKEN`, `AIRTABLE_BASE`, optionally `AIRTABLE_TABLE`, `NOTIFY_EMAIL`, `RESEND_API_KEY`. Then set `SUBMIT_URL` in `submit.html` to that Worker's `/api/submit`.
3. Check `CONTACT_EMAIL` in `submit.html` (where email submissions go, and the fallback shown if `SUBMIT_URL` fails).
4. Point your domain at Pages. Submit `https://yourdomain.com/sitemap.xml` in Google Search Console.
5. Post the link in the county Facebook groups and send it to the market managers listed in the data.

## Weekly loop (10 minutes)

1. Open `Submissions` in Airtable. For each pending row: check the business has a live web or Facebook presence, then either create or update the matching row in `Listings` (set `id` to a slug like `oak-hill-produce`, `status` to `live`, `last_verified` to today) or leave it.
2. Edit `data/listings.json` (or run `python3 scripts/sync_airtable.py` if you use Airtable), then `SITE_DOMAIN=high-shot.github.io SITE_PATH=/localfood python3 scripts/build_site.py` and push. GitHub Pages redeploys in about a minute.

Every quarter: filter `Listings` where `last_verified` is older than 6 months, email each vendor with an email on file, flip non-responders to `pending`.

## Data notes

- Sources: Sweet Grown Alabama directory (with their coordinates and socials), the Alabama Dept. of Agriculture 2026 farmers market and farm stand list, PickYourOwn.org, city sites. Every listing carries `source` and `source_url`.
- `status: pending` means the source was old or unconfirmed. The map shows these faded with an "unverified" badge and a warning; the "hide unverified" checkbox removes them.
- `pin_precision: town` puts a dashed pin at the town center and hides the street address. Use it for home-based farms that have not opted in to an exact pin.
- Season windows (the "In season this month" chips) are estimates in one table at the top of `assets/app.js`. Adjust from local knowledge.
- Product categories are mapped in `scripts/build_data.py` (`CAT` and `VEG`). The form uses the same category list.

## Swapping pieces

- Tiles: OpenStreetMap's public tiles are fine for a community site at this scale. If traffic grows, swap the tile URL in `app.js` and `build_site.py` for Protomaps or a Stadia/MapTiler free tier.
- No Airtable: the function is 60 lines; point it at a Google Sheet via Apps Script or at Formspree, or just email yourself the JSON.
- Local preview: `python3 -m http.server 8765` from this folder. Listing pages under `l/` link with the `/localfood/` prefix, so open them via the map rather than directly when previewing locally.
