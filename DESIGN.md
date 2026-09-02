# Design

Recorded from the built world after the Departures Board redesign, September 2026.
Ground truth is `assets/style.css`, `assets/app.js`, and `scripts/build_site.py`.
Product truth lives in PRODUCT.md; this file owns visual and interaction decisions only.

## World

A rail concourse split-flap departures board. Matte black flap faces in a brushed
steel frame, one condensed sans in caps for destinations and column labels, and a
single amber that carries exactly one meaning: this changes your plans.

The board was chosen over the roll's assigned direction by the user. It won on
product clarity: a ruled table with fixed columns is the clearest way to compare
places on hours, distance, and what is ready. Its known weakness is audience
identification, since nobody in Baldwin County reads a concourse board. That
weakness is managed by keeping the *structure* borrowed and the *language* native:
column labels and codes are board vocabulary, every sentence of prose is Gulf Coast
Farm's own plain voice. No airport metaphor appears in copy.

Visitor mode: **Operate**. The visitor is completing a task, so scanability,
consistent affordances, and familiar controls outrank expression. Brand lives in
the precision of the cells, not in decoration.

## Color

Strategy: **Restrained**, which is the Operate floor. One accent, one alarm,
everything else steel and flap black.

| Token | Value | Role |
|---|---|---|
| `--flap` | `#0b0b0d` | Row face, page ground |
| `--board` | `#131417` | Field behind rows, panel ground |
| `--rule` | `#23262a` | Hairline between rows, columns, cells |
| `--steel-edge` | `#3d4147` | Frame highlight |
| `--letter` | `#f2f2f2` | Primary text. 17.6:1 on flap |
| `--steel-light` | `#a7aaaf` | Secondary text. 8.4:1 on flap |
| `--steel-mid` | `#5b5e63` | **Rules and borders only.** 3.0:1, never text |
| `--amber` | `#ffb000` | Selected, active, and "needs your attention". 10.7:1 |
| `--amber-deep` | `#c98a0a` | Amber borders on dark |
| `--alarm` | `#ff5c4d` | Error text only. 6.4:1 |

Dark ground is chosen from the use scene, not from category habit. The visitor is
on a phone in Gulf Coast daylight; white-on-black at 17.6:1 is the highest contrast
available, and the board's own tradition is built for reading across a bright room.

**Amber discipline.** Amber means one thing. It marks the selected filter, the
active row and pin, an unconfirmed listing, and the absence of published hours. It
is never used for emphasis, decoration, or hierarchy. Adding a second meaning to
amber breaks the system.

Listing types are **not** encoded in color. Four types plus a verified state exceeds
what one accent can carry honestly, so type is a four-letter code in a fixed cell:
`FARM`, `MKT`, `SEA`, `STOR`. The same codes appear on rows and on map pins.

## Type

One family: **Archivo** variable (`wdth` 62–125, `wght` 400–800), loaded from Google
Fonts. Fallback `'Archivo Narrow', 'Helvetica Neue', Arial, sans-serif`. Operate
surfaces do not need display and body pairing; a well-tuned grotesque carries
headings, labels, buttons, data, and prose.

Two lettering roles, both in the same family:

- `.dest` — destinations and place names. `wdth` 78, weight 650, uppercase,
  `letter-spacing: 0.055em`. This is how a flap is cut: condensed enough for fixed
  cells, tracked open enough to read at distance.
- `.lbl` — column labels and field names. `wdth` 88, weight 600, uppercase,
  `letter-spacing: 0.15em`, 10.5px.

**Caps discipline.** Caps are for destinations, codes, labels, and controls. All
descriptive content, listing descriptions, hours, towns, product lists, footnotes,
runs in sentence case. Setting body prose in caps would trade the board's legibility
for its costume.

Fixed rem-anchored scale, never fluid: month 30/23px, detail h2 28/23px, page
heading 34/27px, row name 15.5/15px, body 15px, secondary 13px, labels 10.5px.
Prose measure capped at 68–72ch.

## Composition

The board is the page. The map is a companion, not a peer.

- **Masthead** — brushed steel gradient with an inset top highlight, the wordmark
  left, one amber-outlined action right.
- **Season strip** — the month set large, one line of orientation, and the products
  actually ready this month as flap chips. This strip is the product's most
  distinctive fact and it sits above everything except the wordmark.
- **Control rail** — steel gradient. Search, Near me, and (below 1040px) the
  Board/Map switch on one row; county and type filters on the next. The eighteen
  product categories live behind a `What they sell` disclosure with a live count,
  so they never occupy the first viewport.
- **Deck** — `minmax(0, 1fr)` board plus a 460px sticky map rail at ≥1040px, single
  column below.

### Columns

Fixed, and they never move; only their contents change.

`TYPE (46px) · PLACE (1.55fr) · TOWN (0.8fr) · READY NOW (1.4fr) · HOURS (1fr) · MILES (62px)`

The MILES column persists as an em-dash before the visitor shares a location. A
column that appears and disappears is not a board.

### Row ranking

Rows are ranked by whether you can actually go:

1. Distance ascending, when the visitor has shared a location.
2. Otherwise: places with something ready this month, then confirmed listings, then
   alphabetical.

Alphabetical-only ordering is the thing this redesign replaced. It made the first
screen a phone book.

### Narrow layout

At ≤720px the cells stay but their priority changes, which is what a board does on
a narrow platform display. Three grid areas: code, place with miles, town with the
call-ahead flag, then ready-now on its own line. Free-text hours are dropped from
the row, since at that width they truncate to nothing useful; the actionable part
(that no hours are published) stays as `CALL AHEAD` in amber, and the full hours
appear in the detail.

## Components

Every interactive element ships default, hover, focus, active, and disabled.

- **`.flapchip`** — a physical tile with an `::after` hairline across its middle,
  the way a real flap is split. Selected fills amber with flap-black text.
- **`.btn-steel`** — 40px control with a `.lamp` indicator dot. Amber pulsing lamp
  means locating.
- **`.code`** — the type tile, split like a flap, amber when its row is active.
- **`.btn` / `.btn.primary`** — 2px radius, caps, tracked. Primary is amber.
- **`.cells`** — flex-wrap field cells with clipped 1px rules, so a short final row
  leaves no dead region.
- **States** — skeleton flap rows with a staggered sweep while loading; a
  `No services match` empty state with a working Clear filters button; a
  `The board did not load` alarm state when the fetch fails.

Radius is 2–3px throughout. This is sheet metal and card stock, not soft UI.

### Detail chrome on narrow viewports

Below 1040px, `openDetail` puts `.detail-open` on `#app`, which hides the season
strip and both filter rails. An open detail owns the viewport; those controls act
on a board the visitor is no longer looking at, and they cost roughly 185px that
the listing name, its ready-this-month notice, and Directions need. The search
field and Board/Map switch stay, because typing in search calls `update()`, which
returns to the board, making it the fastest way out. `backToBoard` removes the
class. Desktop keeps all its chrome; there is room for it.

## Motion

One authored moment, and nothing else.

**The flip.** When the visible set of rows changes, the first fourteen destinations
resolve character by character through a scrambled glyph set: 18ms per character,
20ms stagger per row, roughly 700ms at worst. Settling characters carry `.flipping`
in amber and drop it as they land. It is driven by a single shared
`requestAnimationFrame` loop, capped at fourteen rows, and it only fires when the
result ids actually differ from the last render.

Everything else is 120–160ms state feedback on `cubic-bezier(0.16, 1, 0.3, 1)`.
There is no page-load choreography; the visitor is in a task.

`prefers-reduced-motion` collapses the cascade to an instant text set and reduces
every transition and animation to 1ms.

## Map

- **Tiles.** Standard OpenStreetMap, darkened with
  `filter: invert(1) grayscale(1) brightness(1.15) contrast(0.95)` applied to
  `.leaflet-tile-pane` only. Markers, controls, and attribution live in other panes
  and stay untouched. This deliberately avoids a keyed provider: CARTO's `dark_all`
  now watermarks every tile with `API KEY REQUIRED`, and a static site with no
  backend should not depend on an account.
- **Pins** are flap tiles carrying the type code, 30×18px. Below zoom 11 a
  `.lowzoom` class on the map container reduces them to 11px lamps: filled white for
  confirmed, hollow amber-bordered for unconfirmed. Eighty-one code tiles fuse into
  one mass at county scale otherwise.
- **Hidden-map guard.** Below 1040px the map is `display: none` behind the
  Board/Map switch, where Leaflet reports a zero-size container and `flyTo` /
  `fitBounds` produce NaN LatLngs that throw. Every map call goes through
  `mapReady()`. Removing that guard breaks row taps on phones.

## Honesty commitments

These are visual rules that exist to serve PRODUCT.md's disclosure principle. They
are not decoration and should not be traded away for tidiness.

- Unconfirmed listings show an amber `Unconfirmed` flap on the row and an amber
  notice block in the detail. They are never hidden by default; the visitor opts in.
- Missing hours read `Call ahead` in amber, never blank and never invented.
- Withheld addresses read `(exact location not published)`; their pins are dimmed.
- Source and last-checked date appear at the foot of every detail and listing page.

## Static pages

`/l/<id>/` pages and `submit.html` share this stylesheet and the same masthead,
`.page`, `.big`, `.lede`, `.detail`, `.cells`, and `footer.site` vocabulary. The
listing name is the sole `h1`; the masthead is a `p.wordmark`.

`scripts/build_site.py` emits them. Its URL structure, canonical tags, schema.org
JSON-LD, sitemap, and robots output are fixed by the user and were not changed by
this redesign. Rebuild with:

```
SITE_DOMAIN=gulfcoastfarm.com SITE_PATH= python3 scripts/build_site.py
```

## Constraints this world must respect

Static hosting, no backend, no build step for the app, no framework, one runtime
JSON file, Leaflet from CDN. Anything added here has to survive those.

## Known open items

- The steel frame is a CSS gradient, not a real brushed-metal material. The
  quality-bar reference renders actual metal; this is the one fidelity gap.
- Free-text `hours` values are unparsed. An open/closed-now signal would be the
  single biggest improvement to the board's ranking, and needs structured hours in
  the data before it is possible.
