# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: a Gulf Coast resident in the covered Alabama, Florida, or Mississippi counties who sources food locally on a
recurring basis. Not a one-time tourist and not a weekend-outing planner. They are
re-deciding, most weeks, where to get eggs, beef, shrimp, honey, satsumas, or produce, and
they already know some of the answers. They arrive on a phone, often the night before or the
morning of a drive.

Because the visit repeats, the surface is judged on how fast it answers a question the
visitor has asked before, and on whether anything has changed since last time.

Secondary (confirmed from the codebase, not the interview): farm, market, dock, and farm
store operators who submit, correct, or remove their own listing through `submit.html`.

## Product Purpose

Put every farm, farmers market, seafood dock, and farm store in the eight covered Gulf Coast counties on
one map, free, so a local can find and reach one without searching Facebook groups and stale
directories. Success is the visitor leaving with a specific place, its hours or season, and a
way to get there or call ahead.

## Positioning

Comprehensiveness within named counties, plus disclosed provenance. Every listing carries
its `source`, `source_url`, and `last_verified` date, and unverified entries are labeled
rather than hidden. A national directory cannot truthfully claim either the coverage or the
per-listing honesty at this geographic scale.

Seafood is a first-class category, not an afterthought. Docks, boats, seafood markets, and
oyster farms are covered alongside land-based producers. This is a Gulf product, not a generic farm directory.

## Operating Context

- Phone, outdoors or in a vehicle, Gulf Coast daylight. Bright ambient light is the norm.
- The decision is usually "is it worth the drive, and are they open." Hours, season, and
  phone number are the deciding facts.
- Availability is seasonal and perishable. The app already models a Gulf Coast harvest
  calendar (`SEASON` in `assets/app.js`) and surfaces what is in season this month.
- Some operators withhold their exact address (`pin_precision: "town"`); the product must not
  imply precision it does not have.
- Data is refreshed by re-running `scripts/build_data.py` / `sync_airtable.py` and then
  `scripts/build_site.py`, which regenerates `/l/` pages, `sitemap.xml`, `robots.txt`, and the
  manifest.

## Capabilities and Constraints

Confirmed functionality:
- Search across name, city, description, products, categories, and type.
- Filters: type (farm, market, seafood, store), 18 product
  categories, in-season product, "near me" geolocation with distance sort.
- Leaflet map over OpenStreetMap tiles, pins typed and styled by listing type, with a
  distinct treatment for unverified entries and for town-only pins.
- List view, detail view, deep link by `?id=`.
- Static per-listing pages at `/l/<id>/` with schema.org JSON-LD, plus `sitemap.xml`.
- Submission form supporting add, update, and remove, with a honeypot field.

Technical constraints:
- Static hosting. GitHub Pages, custom domain `gulfcoastfarm.com` via `CNAME`. No backend.
- No build step for the app itself. Plain ES5-compatible JS in one IIFE, no framework, no
  bundler. Leaflet 1.9.4 from cdnjs.
- One data file: `data/listings.json`, fetched at runtime.
- The submit form has no server. `SUBMIT_URL` is empty, so it falls back to a `mailto:`
  compose to `barcus@high-shot.com`. Cloudflare Worker files exist in the repo but are unused.
- `/l/<id>/` URL structure and the SEO/JSON-LD output of `scripts/build_site.py` are fixed by
  the user and must survive any redesign.

Current data is maintained in `data/listings.json`. Coverage spans Mobile, Baldwin, and
Escambia counties in Alabama; Escambia and Santa Rosa counties in Florida; and Hancock,
Harrison, and Jackson counties in Mississippi.

## Brand Commitments

- Name: Gulf Coast Farm. Scope is stated as the eight named counties on the About page.
- Voice: plain, second person, unhedged, and willing to say what it does not know. Existing
  copy: "We have not confirmed this listing is current. Call or check their page before you
  drive out." Preserve that register.
- Free and community built. This is stated on the surface and in the footer.
- The user's binding negative constraint from the interview: the result must not read as slick
  or corporate.

## Evidence on Hand

- `data/listings.json`: real listings with names, addresses, coordinates, phone
  numbers, products, hours, and source attribution.
- Sourced substantially from the Sweet Grown Alabama member directory and other public
  directories, with `source_url` retained per listing.
- No photography of any kind. No logo file beyond `assets/icon.svg`. No testimonials, traffic
  numbers, or usage data. None of these may be invented.

## Product Principles

1. Answer "where do I drive, and are they open" before anything else. The visitor came with a
   question, not to browse a database.
2. Disclose confidence. Source, last-checked date, unverified status, and withheld addresses
   stay visible; the product's credibility is built on not overstating.
3. Season is the organizing fact. What is available changes monthly, and the surface should
   reflect the current month without the visitor asking.
4. Stay reachable on a bad connection and an old phone. Static, small, no framework.
5. Community-maintained means corrections are easy and visibly welcome, not buried.

## Accessibility & Inclusion

No formal standard was established. The implementation ships `:focus-visible` outlines, a
`prefers-reduced-motion` guard, `aria-pressed` on filter controls, `aria-live` on the result
tally, and labeled map regions. Preserve at least this level. Bright outdoor daylight is the
expected viewing condition, which raises the practical contrast bar above the 4.5:1 minimum.

## How this project renders

Static files, no build step for the app. Serve the repo root and open the served URL:

```
python3 -m http.server 8000
```

Rebuild the generated `/l/` pages, sitemap, robots, and manifest after any data change:

```
SITE_DOMAIN=gulfcoastfarm.com SITE_PATH= python3 scripts/build_site.py
```
