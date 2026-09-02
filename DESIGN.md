# Design

Recorded from the built world, September 2026. Ground truth is `assets/style.css`,
`assets/app.js`, and `scripts/build_site.py`. Product truth lives in PRODUCT.md;
this file owns visual and interaction decisions only.

## World

Roadside signage pulled most of the way toward the category standard, laid out
map-first. The map is the canvas and listings float over it.

The lineage is Alabama roadside produce signage: painted colour at region scale,
condensed caps for wayfinding, square-cornered plates for controls. What it
deliberately does not take from that lineage is the costume. **No wood grain, no
distressed paint, no hand-lettering, no chalkboard, no wheat or tractor, no cream
ground, no serif display.** The discipline is in the geometry and the colour
blocking, not in pretending to be a physical object.

The category standard supplies the rest: a familiar list of cards, a normal search
field, a map anyone can operate without instruction.

Visitor mode: **Operate**. Someone is deciding where to drive on Saturday.
Scanability and familiar controls outrank expression.

This direction was pinned by the user over the concept roll, after two earlier
builds (a split-flap departures board, then a scrolling list-and-map page) were
rejected as too technical and too static respectively.

## Colour

Strategy: **Functional.** Colour is not decoration here; it carries the listing
taxonomy. Every value below clears 4.5:1 on white.

| Token | Value | Contrast | Role |
|---|---|---|---|
| `--paper` | `#f1f2ee` | — | Page ground, cool not cream |
| `--card` | `#fff` | — | Cards, panels, form fields |
| `--ink` | `#14171a` | 15.9:1 | Primary text, plate borders |
| `--muted` | `#5a6169` | 5.9:1 | Secondary text |
| `--rule` | `#dde0da` | — | Hairlines |
| `--head` | `#14603e` | 8.0:1 | Highway guide green. Sign band, primary buttons |
| `--head-deep` | `#0d4b30` | 10.3:1 | Links, hover |
| `--ready` | `#d93a14` | 4.6:1 | **Ready this month, and nothing else** |
| `--ready-deep` | `#a82c0d` | 7.2:1 | The same signal as text |
| `--t-farm` | `#2f7d4e` | 5.0:1 | Farm |
| `--t-market` | `#8e3a6b` | 7.1:1 | Farmers market |
| `--t-seafood` | `#1c6e8c` | 5.7:1 | Seafood dock |
| `--t-store` | `#3c4650` | 9.6:1 | Farm store |
| `--mark` | `#e8a317` | — | U-pick badge border only, never text |

**Red discipline.** `--ready` means one thing: this place has something in season
right now. The month heading, the season plates, the product tags, and the ring
around in-season pins. Giving red a second meaning would destroy the only
act-now signal on the page.

**Why market is plum and not amber.** Amber measured 3.04:1 on white, below the
floor for an 11px label. Every ochre alternative also sat within ~27° of
`--ready`, muddying the act-now signal. Plum measures 7.1:1 and sits 47° away.
Muscadines being purple is a happy accident, not the reason.

**Why type also has a shape.** Simulating deuteranopia and protanopia, no
five-colour scheme held up: amber landed 11 units from red, plum 10 from green.
On cards the word label carries the meaning and colour reinforces it. On map pins
there is no label, so shape carries it instead: **circle farm, square market,
diamond seafood dock, pill farm store**, with a red ring for ready-this-month.
That system works in greyscale. Do not remove the shapes and leave only colour.

## Type

Two families, each with one job.

- **Big Shoulders Display** (600/700/800) — a real wayfinding face. Wordmark,
  month, section labels, buttons, "Directions". Condensed caps, tracked
  0.07–0.13em. **Never body copy.** The moment it sets a sentence, the whole
  thing tips into costume.
- **Public Sans** (400–700) — the US government's public-interface face. Every
  word the visitor actually reads: names, descriptions, hours, towns, forms.

Fixed scale, never fluid: wordmark 33/26px, month 26/20px, detail h2 23px, page
h1 31/25px, card h3 16.5/16px, body 16px, secondary 13px, labels 10.5px.

## Composition

The map is the page. Everything else floats on it.

- **Sign band** — slim, guide green, 4px ink rule beneath, wordmark left and one
  action right. Kept short so the map gets the room.
- **Stage** — the map fills all remaining viewport, absolutely positioned.
- **Panel** — floats at left, `clamp(340px, 27vw, 440px)`, holding the season
  strip, search, filters, count and cards. Translucent with a backdrop blur.
- **Legend** — floats bottom right, keyed to the pin shapes.

**Blur is load-bearing, not decorative.** The panel sits on a live map and has to
stay readable over arbitrary tile content. This is the one case where blur is the
right tool rather than an effect.

**`fitTo()` pads the map fit by the panel's own width** (`offsetWidth + 32`) on
desktop and by the sheet height on phones. Without that padding, every pin in
western Mobile County hides underneath the panel and the map looks half empty.
If the panel geometry ever changes, this changes with it.

### Ranking

Rows are ranked by whether you can actually go:

1. Distance ascending, when the visitor shares a location.
2. Otherwise: places with something ready this month, then confirmed listings,
   then alphabetical.

Plain alphabetical is what two redesigns ago did, and it made the first screen a
phone book.

### Phone

The panel becomes a bottom sheet at ≤860px, with three detents (16 / 54 / 88 dvh)
driven by `--sheet`. Drag the handle or tap to cycle; the map invalidates size and
re-fits on each change. Opening a detail from the collapsed detent raises the
sheet automatically.

Two things on that breakpoint are not cosmetic:

- The zoom control owns the top right, so **the legend moves to the top left**.
- The sheet covers the map's bottom-right corner, where Leaflet puts its
  attribution. **OSM attribution is a licence requirement**, so
  `.leaflet-bottom.leaflet-right` is lifted to `calc(var(--sheet) - 4px)` and
  animates with the sheet. Do not remove this.

## Components

Every interactive element ships default, hover, focus, active and disabled.

- **`.plate`** — square-cornered filter control, ink border, fills ink when
  pressed. Season plates use the red border and fill instead.
- **`.card`** — white, borders in its type colour on hover and when active. Used
  as a `<button>` in the app and as an `<a>` on static pages; both styled here.
- **`.cardgrid`** — two columns on document pages, one in the panel.
- **`.btn` / `.btn.primary`** — primary is guide green.
- **`.cells`** — flex-wrap field cells with clipped 1px rules, so a short final
  row leaves no dead region.
- **States** — skeleton cards while loading, a "Nothing matches" empty state with
  a working Clear filters button, and a "The listings did not load" error state.

Radius is 3–4px throughout. Plates and buttons are 3px, cards 4px.

## Motion

There is no page-load choreography. The visitor is in a task.

- Map flies to a listing on select, 0.6s, skipped under reduced motion.
- Sheet detents animate height over 280ms on `cubic-bezier(.16,1,.3,1)`.
- Everything else is 130–150ms state feedback.
- `prefers-reduced-motion` reduces every transition and animation to 1ms.

## Map

- **Tiles** are standard OpenStreetMap with
  `filter: saturate(0.28) brightness(1.05) contrast(0.92)` on `.leaflet-tile-pane`
  only. Markers, controls and attribution live in other panes and stay untouched.
  Full greyscale was tested and rejected: it flattens Mobile Bay into the land,
  and the water line matters when ten listings are docks.
- **No keyed tile provider.** CARTO's Positron and dark_all both watermark
  `API KEY REQUIRED` now, and Stadia needs a key plus a domain allowlist. A static
  site with no backend should not depend on an account. If traffic ever justifies
  it, the upgrade is self-hosted Protomaps.
- **`mapReady()` guards every Leaflet call.** Below 860px the map can be
  zero-sized, where `flyTo` and `fitBounds` produce NaN LatLngs that throw and
  abort their caller. Removing that guard breaks card taps on phones.
- **Pages with a map must load Leaflet's own stylesheet.** `head(leaflet=True)`
  in the generator does this. It was once omitted, and the mini map on all 81
  listing pages rendered its tiles absolutely against the page body.

## Honesty commitments

Visual rules that exist to serve PRODUCT.md's disclosure principle. They are not
decoration and should not be traded away for tidiness.

- Unconfirmed listings show an `Unconfirmed` badge on the card and a bordered
  notice in the detail. They are never hidden by default; the visitor opts in.
- Missing hours read "Hours not posted — call first" in `--ready-deep`, never
  blank and never invented.
- Withheld addresses read "(exact location not published)" and their pins are
  dashed.
- Source and last-checked date appear at the foot of every detail and listing page.

## The static surface

`scripts/build_site.py` generates everything a crawler or an AI assistant sees:

| Path | What it is |
|---|---|
| `/l/<id>/` | one page per listing. **URL structure is fixed** |
| `/in/<town>/` | every listing in one town |
| `/what/<product>/` | every listing offering one product category |
| `/in-season/` | what is ready this month |
| `index.html` | a crawlable copy of the card list, injected between `<!--STATIC-->` markers |

These pages use `body.doc`, which releases the fixed-height shell and lets the
page scroll. They share the sign band, `.page`, `.big`, `.lede`, `.cells`,
`.cardgrid` and `footer.site`. The listing name is the sole `h1`.

**The homepage injection is progressive enhancement, not cloaking.** The static
cards are the same content, in the same order, with the same words the app
renders; `renderList()` simply replaces them with interactive versions on boot.
If you ever change what the app shows, change `card()` in the generator to match.

Rebuild with:

```
SITE_DOMAIN=gulfcoastfarm.com SITE_PATH= python3 scripts/build_site.py
```

That script also hashes `style.css` and `app.js` and stamps `?v=<hash>` onto every
asset link. GitHub Pages serves everything with `max-age=600`, so without the
stamp a visitor who loaded the site shortly before a deploy gets new HTML with
cached CSS and renders an unstyled page. This actually happened. Do not remove it.

## Constraints this world must respect

Static hosting, no backend, no build step for the app, no framework, one runtime
JSON file, Leaflet from CDN. Anything added here has to survive those.

## Known open items

- Free-text `hours` are unparsed, so there is no open-now signal, and the listing
  schema cannot publish `openingHours` without emitting invalid data. Fixing it
  needs structured hours in `listings.json`, not a design change. Highest-value
  work remaining, and it now unblocks SEO as well as ranking.
- No Open Graph image, so social and AI previews are text only.
- Clicking a card flies the map and opens the detail, but the reverse discovery
  path — hovering a pin to highlight its card — does not exist.
- The panel has no resize handle on desktop; width is fixed by `clamp()`.
