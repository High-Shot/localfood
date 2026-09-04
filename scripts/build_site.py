#!/usr/bin/env python3
"""Generate the static, crawlable surface of Gulf Coast Farm.

  /l/<id>/          one page per listing        (URL structure is fixed, do not change)
  /in/<town>/       every listing in one town
  /what/<product>/  every listing offering one product category
  /in-season/       what is ready this month
  index.html        gets a crawlable copy of the listing list injected into it

Run from the repo root:
  SITE_DOMAIN=gulfcoastfarm.com SITE_PATH= python3 scripts/build_site.py
"""
import json, os, re, shutil, html, hashlib
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = os.environ.get('SITE_DOMAIN', 'localfood.example.com')
PATH = os.environ.get('SITE_PATH', '').rstrip('/')
BASE = f'https://{DOMAIN}{PATH}'

TYPE_LABEL = {'farm': 'Farm', 'market': 'Farmers market', 'seafood': 'Seafood dock', 'store': 'Farm store'}
TYPE_PLURAL = {'farm': 'farms', 'market': 'farmers markets', 'seafood': 'seafood docks', 'store': 'farm stores'}
SCHEMA_TYPE = {'farm': 'LocalBusiness', 'market': 'LocalBusiness', 'seafood': 'FoodEstablishment', 'store': 'GroceryStore'}
TILES = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

CAT_LABEL = {
    'beef': 'Beef', 'pork': 'Pork', 'chicken': 'Chicken', 'lamb': 'Lamb', 'eggs': 'Eggs', 'dairy': 'Dairy',
    'honey': 'Honey', 'seafood': 'Seafood', 'vegetables': 'Vegetables', 'fruit': 'Fruit', 'berries': 'Berries',
    'citrus': 'Satsumas & citrus', 'nuts': 'Pecans & peanuts', 'upick': 'U-pick', 'flowers': 'Flowers',
    'baked': 'Baked goods', 'pantry': 'Jams, sauces & pantry', 'plants': 'Plants',
}
# How a person would actually phrase the search, used in hub titles and headings.
CAT_PHRASE = {
    'beef': 'local beef', 'pork': 'local pork', 'chicken': 'pasture-raised chicken', 'lamb': 'local lamb',
    'eggs': 'farm fresh eggs', 'dairy': 'local dairy', 'honey': 'local honey', 'seafood': 'fresh Gulf seafood',
    'vegetables': 'fresh local vegetables', 'fruit': 'local fruit', 'berries': 'local berries',
    'citrus': 'satsumas and citrus', 'nuts': 'pecans and peanuts', 'upick': 'u-pick fruit and vegetables',
    'flowers': 'fresh cut flowers', 'baked': 'local baked goods', 'pantry': 'local jams, sauces and pantry goods',
    'plants': 'plants and seedlings',
}
# Gulf Coast harvest windows. Mirrors SEASON in assets/app.js; keep the two in step.
SEASON = {
    'Strawberries': [3, 4, 5], 'Blueberries': [5, 6, 7], 'Blackberries': [5, 6], 'Peaches': [5, 6], 'Plums': [5, 6],
    'Satsumas': [10, 11, 12], 'Pecans': [10, 11, 12, 1], 'Muscadine Grapes': [8, 9], 'Sweet Corn': [6, 7],
    'Tomatoes': [5, 6, 7, 10, 11], 'Watermelon': [6, 7, 8], 'Cantaloupe': [6, 7], 'Pumpkins': [10], 'Pumpkin Patch': [10],
    'Peas': [6, 7, 8], 'Okra': [6, 7, 8, 9], 'Squash': [5, 6, 7, 10], 'Cucumbers': [5, 6, 7],
    'Greens': [10, 11, 12, 1, 2, 3], 'Sweet Potatoes': [9, 10, 11, 12], 'Peppers': [6, 7, 8, 9, 10],
    'Pears': [8, 9], 'Fresh Cut Flowers': [4, 5, 6, 7, 8, 9, 10], 'Saltwater Shrimp': [6, 7, 8, 9, 10, 11, 12],
    'Oysters': [10, 11, 12, 1, 2, 3], 'Lettuce': [10, 11, 12, 1, 2, 3, 4], 'Roasted/Boiled Peanuts': [7, 8, 9, 10],
}
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']

e = lambda s: html.escape(str(s if s is not None else ''), quote=True)
slug = lambda s: re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', str(s).lower())).strip('-')
STATE_NAME = {'AL': 'Alabama', 'FL': 'Florida', 'MS': 'Mississippi'}
st = lambda l: l.get('state', 'AL')
stn = lambda l: STATE_NAME.get(l.get('state', 'AL'), 'Alabama')

listings = [l for l in json.load(open(os.path.join(ROOT, 'data/listings.json')))
            if l['status'] != 'retired' and l.get('lat')]
MONTH_NUM = date.today().month
MONTH_NAME = MONTHS[MONTH_NUM - 1]
ready_now = lambda l: [p for p in l['products'] if p in SEASON and MONTH_NUM in SEASON[p]]

# GitHub Pages serves everything with max-age=600. Without a version stamp a
# visitor who loaded the site shortly before a deploy gets new HTML with cached
# CSS and JS, and renders an unstyled page. Content-hashed, so an unchanged
# deploy does not needlessly bust caches.
def asset_version():
    h = hashlib.sha256()
    for name in ('assets/style.css', 'assets/app.js', 'assets/icon.svg',
                 'assets/favicon-32.png', 'assets/apple-touch-icon.png',
                 'assets/icon-192.png', 'assets/icon-512.png', 'favicon.ico'):
        with open(os.path.join(ROOT, name), 'rb') as fh:
            h.update(fh.read())
    return h.hexdigest()[:8]
VER = asset_version()

urls = []


# --------------------------------------------------------------------- pieces

def head(title, desc, canon, extra_ld=None, noindex=False, leaflet=False):
    ld = f'<script type="application/ld+json">{json.dumps(extra_ld)}</script>' if extra_ld else ''
    leaf = ('<link rel="stylesheet" '
            'href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">') if leaflet else ''
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canon}">
{'<meta name="robots" content="noindex,follow">' if noindex else ''}
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{canon}">
<meta property="og:site_name" content="Gulf Coast Farm">
<meta property="og:image" content="{BASE}/assets/og-image.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Map of the Gulf Coast with every local farm, market and seafood dock pinned">
<meta name="twitter:card" content="summary_large_image">
<meta name="geo.placename" content="Gulf Coast, Alabama, Florida, and Mississippi">
<meta name="theme-color" content="#14603e">
<link rel="icon" href="{PATH}/assets/icon.svg?v={VER}" type="image/svg+xml">
<link rel="icon" href="{PATH}/assets/favicon-32.png?v={VER}" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{PATH}/assets/apple-touch-icon.png?v={VER}">
<link rel="manifest" href="{PATH}/manifest.webmanifest">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{leaf}
<link rel="stylesheet" href="{PATH}/assets/style.css?v={VER}">
{ld}
</head><body class="doc">
<div class="shell">
<header class="band"><div class="inner">
<div class="brand">
<img class="brand-mark" src="{PATH}/assets/icon.svg?v={VER}" width="42" height="42" alt="" aria-hidden="true">
<div class="brand-copy"><p class="wordmark"><a href="{PATH}/">Gulf Coast Farm</a></p>
<p class="tagline">Local farms, markets, and seafood, mapped.</p></div></div>
<a class="add" href="{PATH}/submit.html">Add a farm or market &rarr;</a>
</div></header>
<main class="page">'''


CONTACT_SCRIPT = ('<script>(function(){var a=document.getElementsByClassName("contactlink"),i;'
                  'for(i=0;i<a.length;i++){a[i].href="mailto:"+a[i].getAttribute("data-u")+"@"+'
                  'a[i].getAttribute("data-d")+"?subject=Gulf%20Coast%20Farm";}})();</script>')


def tail():
    return f'''</main>
<footer class="site"><div class="inner">Gulf Coast Farm is a free community project for the Gulf Coast.
<a href="{PATH}/">Map of every listing</a> &middot; <a href="{PATH}/in-season/">In season now</a> &middot;
<a href="{PATH}/about/">About</a> &middot; <a href="{PATH}/submit.html">Add a farm or market</a> &middot;
<a class="contactlink" data-u="barcus" data-d="high-shot.com" href="#">Contact</a></div></footer>
''' + CONTACT_SCRIPT + '''
</div>
</body></html>'''


def crumbs(trail):
    """trail: list of (name, url) ending with the current page."""
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList',
            'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': u}
                                for i, (n, u) in enumerate(trail)]}


def card(l, show_town=True):
    """The same card vocabulary the app renders, as static HTML.

    Built by concatenation rather than one large f-string: nested quotes and
    backslashes inside f-string expressions are a syntax error before Python
    3.12, and this script has to run on a stock macOS python3.
    """
    r = ready_now(l)
    if r:
        tags = ''.join('<span class="tag">%s</span>' % e(p) for p in r[:2])
    else:
        tags = ''.join('<span class="tag muted">%s</span>' % e(CAT_LABEL.get(c, c))
                       for c in l['categories'][:2])
    hours = e(l['hours']) if l['hours'] else 'Hours not posted &mdash; call first'
    hours_cls = '' if l['hours'] else ' callfirst'
    town = '%s, %s County, %s' % (e(l['city']), e(l['county']), st(l)) if show_town else e(l['county']) + ' County, ' + st(l)
    upick = '<span class="upick">U-pick</span>' if 'upick' in l['categories'] else ''
    unconf = '<span class="unconf">Unconfirmed</span>' if l['status'] != 'live' else ''
    return ('<a class="card t-%s" href="%s/l/%s/">'
            '<span class="kind"><i class="sw"></i>%s</span>'
            '<h3>%s</h3>'
            '<p class="where">%s%s%s</p>'
            '<div class="tags">%s</div>'
            '<p class="hours%s">%s</p></a>'
            % (l['type'], PATH, e(l['id']), e(TYPE_LABEL[l['type']]), e(l['name']),
               town, upick, unconf, tags, hours_cls, hours))


def item_list(rows, name):
    return {'@context': 'https://schema.org', '@type': 'ItemList', 'name': name,
            'numberOfItems': len(rows),
            'itemListElement': [{'@type': 'ListItem', 'position': i + 1,
                                 'url': f"{BASE}/l/{r['id']}/", 'name': r['name']}
                                for i, r in enumerate(rows)]}


def hub(path, title, desc, h1, intro, rows, trail, extra_html=''):
    """A town or product landing page: real content, real internal links."""
    canon = f'{BASE}/{path}/'
    ld = [crumbs(trail), item_list(rows, h1),
          {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': h1,
           'description': desc, 'url': canon,
           'about': {'@type': 'Place', 'name': 'Gulf Coast (Alabama, Northwest Florida, and coastal Mississippi)'}}]
    body = head(title, desc, canon, ld)
    body += f'<h1 class="big">{e(h1)}</h1>\n<p class="lede">{intro}</p>\n'
    body += '<div class="cardgrid">' + ''.join(card(r) for r in rows) + '</div>\n'
    body += extra_html + tail()
    d = os.path.join(ROOT, path)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w').write(body)
    urls.append(canon)


def a(label, href):
    return f'<a class="btn" href="{e(href)}" target="_blank" rel="noopener">{label}</a>' if href else ''


# ------------------------------------------------------------------ wipe old

for folder in ('l', 'in', 'what', 'in-season'):
    shutil.rmtree(os.path.join(ROOT, folder), ignore_errors=True)
urls.append(BASE + '/')

by_city, by_cat = {}, {}
for l in listings:
    by_city.setdefault(l['city'], []).append(l)
    for c in l['categories']:
        by_cat.setdefault(c, []).append(l)


# ------------------------------------------------------------- listing pages

for l in listings:
    exact = l['pin_precision'] == 'exact' and l['address']
    addr = f"{l['address']}, {l['city']}, {st(l)} {l['zip']}" if exact else f"{l['city']}, {st(l)}"
    title = f"{l['name']}: {TYPE_LABEL[l['type']]} in {l['city']}, {stn(l)}"
    offers = ', '.join(l['products']) if l['products'] else ''
    desc = (l['description'] or
            f"{l['name']} is a {TYPE_LABEL[l['type']].lower()} in {l['city']}, {l['county']} County, {stn(l)}.")[:155]
    canon = f"{BASE}/l/{l['id']}/"

    biz = {
        '@context': 'https://schema.org', '@type': SCHEMA_TYPE[l['type']], 'name': l['name'],
        'description': l['description'] or None, 'url': canon, 'telephone': l['phone'] or None,
        'email': l['email'] or None,
        'address': {'@type': 'PostalAddress',
                    'streetAddress': l['address'] if exact else None,
                    'addressLocality': l['city'], 'addressRegion': st(l),
                    'postalCode': l['zip'] or None, 'addressCountry': 'US'},
        'geo': {'@type': 'GeoCoordinates', 'latitude': l['lat'], 'longitude': l['lng']} if exact else None,
        'areaServed': [{'@type': 'AdministrativeArea', 'name': f"{l['county']} County, {stn(l)}"}],
        'sameAs': [u for u in [l['website'], l['facebook'], l['instagram'], l['tiktok']] if u] or None,
    }
    # Products the place actually sells, so an assistant can answer "who sells X".
    if l['products'] or l['categories']:
        items = l['products'] or [CAT_LABEL.get(c, c) for c in l['categories']]
        biz['hasOfferCatalog'] = {
            '@type': 'OfferCatalog', 'name': f"Sold at {l['name']}",
            'itemListElement': [{'@type': 'Offer', 'itemOffered': {'@type': 'Product', 'name': p}}
                                for p in items]}
    # Hours are free text in the data and will not parse to schema's format
    # reliably, so they are published as page content only, never as invalid
    # openingHours. Fix this when listings.json carries structured hours.
    biz = {k: v for k, v in biz.items() if v is not None}

    trail = [('Gulf Coast Farm', BASE + '/'),
             (f"{l['city']}, {st(l)}", f"{BASE}/in/{slug(l['city'])}/"),
             (l['name'], canon)]
    pending = ('' if l['status'] == 'live' else
               '<div class="notice warn"><b>Unconfirmed</b>We have not confirmed this listing is current. '
               'Call or check their page before you drive out.</div>')
    dirs = f"https://www.google.com/maps/dir/?api=1&destination={e(addr if exact else '')}" if exact else None
    r = ready_now(l)

    # Nearby: same town first, then the rest of the county, so no page is an orphan.
    same_town = [x for x in by_city.get(l['city'], []) if x['id'] != l['id']][:5]
    nearby = same_town or [x for x in listings
                           if x['county'] == l['county'] and st(x) == st(l) and x['id'] != l['id']][:5]
    cat_links = ' &middot; '.join(
        f'<a href="{PATH}/what/{c}/">{e(CAT_LABEL.get(c, c))}</a>' for c in l['categories'])

    page = head(title, desc, canon, [biz, crumbs(trail)], leaflet=True)
    page += f'''<nav class="crumb"><a href="{PATH}/">All listings</a> &rsaquo; <a href="{PATH}/in/{slug(l['city'])}/">{e(l['city'])}</a></nav>
<h1 class="big">{e(l['name'])}</h1>
<p class="lede"><span class="kind t-{e(l['type'])}"><i class="sw"></i>{e(TYPE_LABEL[l['type']])}</span> in {e(l['city'])}, {e(l['county'])} County, {st(l)}{' <span class="unconf">Unconfirmed</span>' if l['status'] != 'live' else ''}</p>
{pending}
{('<div class="notice ready"><b>Ready this month</b>' + e(', '.join(r)) + '</div>') if r else ''}
<div class="detail" style="padding:0">
{('<p>' + e(l['description']) + '</p>') if l['description'] else ''}
<div class="actions">{a('Directions', dirs)}{('<a class="btn" href="tel:' + e(''.join(ch for ch in l['phone'] if ch.isdigit() or ch == '+')) + '">Call</a>') if l['phone'] else ''}{a('Website', l['website'])}{a('Facebook', l['facebook'])}{a('Instagram', l['instagram'])}{a('TikTok', l['tiktok'])}{('<a class="btn" href="mailto:' + e(l['email']) + '">Email</a>') if l['email'] else ''}</div>
<div id="mini" class="miniMap"></div>
<dl class="cells">
<div><dt>Offers</dt><dd>{e(offers or 'Not listed')}</dd></div>
<div><dt>Hours</dt><dd{'' if l['hours'] else ' class="flag"'}>{e(l['hours']) if l['hours'] else 'Not published, call ahead'}</dd></div>
{('<div><dt>How to buy</dt><dd>' + e(', '.join(l['how_to_buy'])) + '</dd></div>') if l['how_to_buy'] else ''}
{('<div><dt>Sells at</dt><dd>' + e(l['sells_at']) + '</dd></div>') if l['sells_at'] else ''}
<div><dt>Address</dt><dd>{e(addr)}{'' if exact else ' (exact location not published)'}</dd></div>
{('<div><dt>Phone</dt><dd>' + e(l['phone']) + '</dd></div>') if l['phone'] else ''}
</dl>
{('<p class="browse"><b>Also listed under</b> ' + cat_links + '</p>') if cat_links else ''}
<p><a href="{PATH}/submit.html?id={e(l['id'])}&mode=update">Own this listing or see an error? Send an update.</a></p>
<p class="fine">Source: {e(l['source'])}. Last checked {e(l['last_verified'])}. Hours and availability change with the season; confirm before you go.</p>
</div>
<section class="more">
<h2>More near {e(l['city'])}</h2>
<div class="cardgrid">{''.join(card(x) for x in nearby)}</div>
<p class="browse"><a href="{PATH}/in/{slug(l['city'])}/">Everything in {e(l['city'])}</a> &middot; <a href="{PATH}/in-season/">What is ready in {MONTH_NAME}</a></p>
</section>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
var m=L.map('mini',{{scrollWheelZoom:false}}).setView([{l['lat']},{l['lng']}],{13 if exact else 10});
L.tileLayer('{TILES}',{{maxZoom:19,attribution:'{TILE_ATTR}'}}).addTo(m);
L.marker([{l['lat']},{l['lng']}],{{icon:L.divIcon({{className:'',html:'<div class="dot {e(l['type'])} {'' if l['status'] == 'live' else 'unconfirmed'}"></div>',iconSize:[16,16],iconAnchor:[8,8]}}),title:{json.dumps(l['name'])}}}).addTo(m);
</script>
'''
    page += tail()
    d = os.path.join(ROOT, 'l', l['id'])
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w').write(page)
    urls.append(canon)


# ------------------------------------------------------------------ town hubs

for city, rows in sorted(by_city.items()):
    rows = sorted(rows, key=lambda x: (not ready_now(x), x['status'] != 'live', x['name']))
    county = rows[0]['county']
    state_ab = rows[0].get('state', 'AL')
    state_name = STATE_NAME.get(state_ab, 'Alabama')
    kinds = sorted({TYPE_PLURAL[x['type']] for x in rows})
    kind_phrase = ', '.join(kinds[:-1]) + (' and ' + kinds[-1] if len(kinds) > 1 else kinds[0])
    n = len(rows)
    title = f"{n} local food {'places' if n != 1 else 'place'} in {city}, {state_name}"
    desc = (f"{n} local food {'places' if n != 1 else 'place'} in {city}, {county} County, {state_name}. "
            f"Includes {kind_phrase}. Addresses, hours and phone numbers. Free and community maintained.")[:158]
    ready_here = sorted({p for x in rows for p in ready_now(x)})
    intro = (f"All {n} farms, farmers markets, seafood docks and farm stores we can find in "
             f"<b>{e(city)}, {e(county)} County, {state_ab}</b>. "
             + (f"Ready in {MONTH_NAME}: {e(', '.join(ready_here))}. " if ready_here else '')
             + "Hours change with the season, so call before you drive out.")
    other = [c for c in sorted(by_city) if c != city][:14]
    extra = ('<p class="browse"><b>Other towns</b> ' +
             ' &middot; '.join(f'<a href="{PATH}/in/{slug(c)}/">{e(c)}</a>' for c in other) + '</p>')
    hub(f'in/{slug(city)}', title, desc, f'Local food in {city}, {state_name}', intro, rows,
        [('Gulf Coast Farm', BASE + '/'), (f'{city}, {state_ab}', f'{BASE}/in/{slug(city)}/')], extra)


# --------------------------------------------------------------- product hubs

for cat, rows in sorted(by_cat.items()):
    rows = sorted(rows, key=lambda x: (not ready_now(x), x['status'] != 'live', x['name']))
    phrase, label, n = CAT_PHRASE.get(cat, CAT_LABEL.get(cat, cat)), CAT_LABEL.get(cat, cat), len(rows)
    towns = sorted({x['city'] for x in rows})
    title = f"Where to buy {phrase} on the Gulf Coast"
    desc = (f"{n} places selling {phrase} across coastal Alabama, Northwest Florida and the Mississippi Gulf Coast, "
            f"including {', '.join(towns[:4])}. Addresses, hours and phone numbers.")[:158]
    intro = (f"{n} places on the Gulf Coast offering <b>{e(label.lower())}</b>, "
             f"in {e(', '.join(towns[:6]))}{' and elsewhere' if len(towns) > 6 else ''}. "
             "Community maintained and free to use.")
    other = [c for c in sorted(by_cat) if c != cat]
    extra = ('<p class="browse"><b>Other products</b> ' +
             ' &middot; '.join(f'<a href="{PATH}/what/{c}/">{e(CAT_LABEL.get(c, c))}</a>' for c in other) + '</p>')
    hub(f'what/{cat}', title, desc, f'Where to buy {phrase}', intro, rows,
        [('Gulf Coast Farm', BASE + '/'), (label, f'{BASE}/what/{cat}/')], extra)


# ------------------------------------------------------------- in-season page

season_rows = sorted([l for l in listings if ready_now(l)],
                     key=lambda x: (x['status'] != 'live', x['name']))
prods = sorted({p for l in listings for p in ready_now(l)})
title = f"What is in season right now on the Gulf Coast ({MONTH_NAME})"
desc = (f"In {MONTH_NAME} on the Gulf Coast you can buy {', '.join(prods[:6])}. "
        f"{len(season_rows)} local farms, markets and seafood docks have something ready now.")[:158]
intro = (f"On the Gulf Coast, <b>{MONTH_NAME}</b> brings {e(', '.join(prods))}. "
         f"{len(season_rows)} of our {len(listings)} listings have something ready right now. "
         "Harvest windows are estimates and shift with the weather, so call ahead.")
extra = ('<p class="browse"><b>Browse by product</b> ' +
         ' &middot; '.join(f'<a href="{PATH}/what/{c}/">{e(CAT_LABEL.get(c, c))}</a>' for c in sorted(by_cat)) +
         '</p><p class="browse"><b>Browse by town</b> ' +
         ' &middot; '.join(f'<a href="{PATH}/in/{slug(c)}/">{e(c)}</a>' for c in sorted(by_city)) + '</p>')
hub('in-season', title, desc, f'What is in season right now: {MONTH_NAME}', intro, season_rows,
    [('Gulf Coast Farm', BASE + '/'), ('In season now', f'{BASE}/in-season/')], extra)


# ------------------------------------------------------------------ about page

about_canon = f'{BASE}/about/'
about_ld = [crumbs([('Gulf Coast Farm', BASE + '/'), ('About', about_canon)]),
            {'@context': 'https://schema.org', '@type': 'AboutPage',
             'name': 'About Gulf Coast Farm', 'url': about_canon}]
about = head('About Gulf Coast Farm',
             'How Gulf Coast Farm works, where it covers, and how every listing is sourced '
             'and dated. A free, community-built map of local food across coastal Alabama, Northwest Florida and coastal Mississippi.',
             about_canon, about_ld)
about += ('''<nav class="crumb"><a href="{P}/">All listings</a> &rsaquo; About</nav>
<h1 class="big">About Gulf Coast Farm</h1>
<p class="lede">A free map of where to buy food grown, raised, and caught close to home, across coastal Alabama, Northwest Florida, and the Mississippi Gulf Coast.</p>
<div class="prose">
<p>Gulf Coast Farm is a map, not a store and not a delivery service. It shows farms, farmers markets, seafood docks, and farm stores: where each one is, when it is open, and how to get there. You find a place, then you go buy from it directly. Nothing is sold through this site, and there is no charge to be listed.</p>
<h2>Where it covers</h2>
<p>Coverage is stated as named counties, not a distance from wherever you happen to be standing, because the site does not track your location. Right now that is eight counties: Mobile, Baldwin, and Escambia in Alabama; Escambia and Santa Rosa in Florida; and Hancock, Harrison, and Jackson in Mississippi. It started in Mobile and Baldwin and is working outward along the Gulf Coast.</p>
<h2>Where the listings come from</h2>
<p>Every listing records where its information came from and the date it was last checked. You can see both at the bottom of each place&rsquo;s page. Listings we have not been able to confirm are marked <span class="unconf">Unconfirmed</span> and left on the map rather than hidden, so you can judge for yourself and call ahead. Hours, seasons, and whether a place is even open this year all change, so treat everything here as a starting point and confirm before you drive out.</p>
<p>What a place shows as ready this month comes from typical Gulf Coast harvest windows, which shift with the weather. The site does not rank places or call anything the best. It tells you what is out there and lets the map do the sorting.</p>
<h2>Who runs it</h2>
<p>It is built and kept up by one person on the Gulf Coast, by hand, in spare time. That is also why your help matters.</p>
<h2>Add a place, or fix one</h2>
<p>If you run a farm, market, dock, or farm store that belongs here, or you spot something out of date, please <a href="{P}/submit.html">add or update a listing</a>. It takes a couple of minutes, and a person reviews every submission. For a question, a correction, or a place we have missed, <a class="contactlink" data-u="barcus" data-d="high-shot.com" href="#">send an email</a>.</p>
</div>
'''.replace('{P}', PATH))
about += tail()
_ad = os.path.join(ROOT, 'about')
os.makedirs(_ad, exist_ok=True)
open(os.path.join(_ad, 'index.html'), 'w').write(about)
urls.append(about_canon)


# ----------------------------------------------- crawlable copy of the listing
#            list, injected into index.html between markers. The app replaces it
#            on boot, so bots and no-JS visitors get the same content users do.

ordered = sorted(listings, key=lambda x: (not ready_now(x), x['status'] != 'live', x['name']))
static = ('<h2 class="vh">Every farm, market and seafood dock on the Gulf Coast</h2>'
          + ''.join(card(l) for l in ordered)
          + '<nav class="browse"><b>Browse by town</b> '
          + ' &middot; '.join(f'<a href="{PATH}/in/{slug(c)}/">{e(c)}</a>' for c in sorted(by_city))
          + '</nav><nav class="browse"><b>Browse by product</b> '
          + ' &middot; '.join(f'<a href="{PATH}/what/{c}/">{e(CAT_LABEL.get(c, c))}</a>' for c in sorted(by_cat))
          + f'</nav><nav class="browse"><a href="{PATH}/in-season/">What is ready in {MONTH_NAME}</a></nav>')

home_ld = [
    {'@context': 'https://schema.org', '@type': 'WebSite', 'name': 'Gulf Coast Farm',
     'url': BASE + '/',
     'description': 'Every local farm, farmers market, seafood dock and farm store on '
                    'coastal Alabama, Northwest Florida and the Mississippi Gulf Coast. Free and community maintained.',
     'inLanguage': 'en-US',
     'about': {'@type': 'Place', 'name': 'Gulf Coast (Alabama, Northwest Florida, and coastal Mississippi)'}},
    item_list(ordered, 'Local farms, markets and seafood on the Gulf Coast'),
]

idx = os.path.join(ROOT, 'index.html')
s = open(idx).read()
s = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{BASE}/">', s)
s = re.sub(r'<!--STATIC-->.*?<!--/STATIC-->', '<!--STATIC-->' + static + '<!--/STATIC-->', s, flags=re.S)
s = re.sub(r'<script type="application/ld\+json">.*?</script>\s*', '', s, flags=re.S)
s = s.replace('</head>', f'<script type="application/ld+json">{json.dumps(home_ld)}</script>\n</head>')
open(idx, 'w').write(s)

for name in ('index.html', 'submit.html'):
    fp = os.path.join(ROOT, name)
    t = open(fp).read()
    t = re.sub(
        r'(assets/(?:style\.css|app\.js|icon\.svg|favicon-32\.png|apple-touch-icon\.png))(\?v=[0-9a-f]+)?',
        rf'\1?v={VER}', t)
    open(fp, 'w').write(t)

urls.append(BASE + '/submit.html')


# ------------------------------------------------------------ sitemap, robots

today = date.today().isoformat()
open(os.path.join(ROOT, 'sitemap.xml'), 'w').write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + ''.join(f'<url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n' for u in sorted(set(urls)))
    + '</urlset>\n')
open(os.path.join(ROOT, 'robots.txt'), 'w').write(
    f'User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n')
open(os.path.join(ROOT, 'manifest.webmanifest'), 'w').write(json.dumps(
    {'name': 'Gulf Coast Farm', 'short_name': 'Gulf Coast', 'start_url': PATH + '/',
     'display': 'standalone', 'background_color': '#f1f2ee', 'theme_color': '#14603e',
     'icons': [
         {'src': f'assets/icon.svg?v={VER}', 'sizes': 'any', 'type': 'image/svg+xml'},
         {'src': f'assets/icon-192.png?v={VER}', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any maskable'},
         {'src': f'assets/icon-512.png?v={VER}', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'},
     ]}, indent=1))

print(f'{len(listings)} listings, {len(by_city)} town pages, {len(by_cat)} product pages, '
      f'1 in-season page. Sitemap {len(set(urls))} urls. Domain {DOMAIN}, assets v{VER}')
