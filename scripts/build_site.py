#!/usr/bin/env python3
"""Generate /l/<id>/index.html for every live or pending listing, plus sitemap.xml, robots.txt, manifest.
Run from the repo root: python3 scripts/build_site.py
Set SITE_DOMAIN (and SITE_PATH for a subpath deploy) in env or edit DOMAIN below."""
import json, os, re, shutil, html, sys, hashlib
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = os.environ.get('SITE_DOMAIN', 'localfood.example.com')
PATH = os.environ.get('SITE_PATH', '').rstrip('/')  # e.g. '/localfood' for a GitHub Pages project site, '' for a custom domain
BASE = f'https://{DOMAIN}{PATH}'
TYPE_LABEL = {'farm': 'Farm', 'market': 'Farmers market', 'seafood': 'Seafood dock', 'store': 'Farm store'}
TILES = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
SCHEMA_TYPE = {'farm': 'LocalBusiness', 'market': 'LocalBusiness', 'seafood': 'FoodEstablishment', 'store': 'GroceryStore'}
e = lambda s: html.escape(str(s if s is not None else ''), quote=True)

# GitHub Pages serves every file with max-age=600. Without a version stamp, a
# visitor who loaded the site in the ten minutes before a deploy gets new HTML
# with cached CSS and JS, which renders as an unstyled page. The stamp is a hash
# of the asset bytes, so it only changes when the assets actually change.
def asset_version():
    h = hashlib.sha256()
    for name in ('assets/style.css', 'assets/app.js'):
        with open(os.path.join(ROOT, name), 'rb') as fh:
            h.update(fh.read())
    return h.hexdigest()[:8]

VER = asset_version()

listings = json.load(open(os.path.join(ROOT, 'data/listings.json')))
outdir = os.path.join(ROOT, 'l')
shutil.rmtree(outdir, ignore_errors=True)
urls = [BASE + '/', BASE + '/submit.html']

def a(label, href):
    return f'<a class="btn" href="{e(href)}" target="_blank" rel="noopener">{label}</a>' if href else ''

for l in listings:
    if l['status'] == 'retired' or not l.get('lat'):
        continue
    exact = l['pin_precision'] == 'exact' and l['address']
    addr = f"{l['address']}, {l['city']}, AL {l['zip']}" if exact else f"{l['city']}, AL"
    title = f"{l['name']}: {TYPE_LABEL[l['type']]} in {l['city']}, Alabama"
    offers = ', '.join(l['products']) if l['products'] else ''
    desc = (l['description'] or f"{l['name']} is a {TYPE_LABEL[l['type']].lower()} in {l['city']}, {l['county']} County, Alabama.")[:155]
    ld = {
        '@context': 'https://schema.org', '@type': SCHEMA_TYPE[l['type']], 'name': l['name'],
        'description': l['description'] or None, 'url': f"{BASE}/l/{l['id']}/", 'telephone': l['phone'] or None,
        'address': {'@type': 'PostalAddress', 'streetAddress': l['address'] if exact else None, 'addressLocality': l['city'], 'addressRegion': 'AL', 'postalCode': l['zip'] or None, 'addressCountry': 'US'},
        'geo': {'@type': 'GeoCoordinates', 'latitude': l['lat'], 'longitude': l['lng']} if exact else None,
        'sameAs': [u for u in [l['website'], l['facebook'], l['instagram'], l['tiktok']] if u] or None,
    }
    ld = json.dumps({k: v for k, v in ld.items() if v is not None})
    pending = '' if l['status'] == 'live' else '<div class="notice warn"><b>Unconfirmed</b>We have not confirmed this listing is current. Call or check their page before you drive out.</div>'
    dirs = f"https://www.google.com/maps/dir/?api=1&destination={e(addr if exact else '')}" if exact else None
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{BASE}/l/{e(l['id'])}/">
<meta property="og:title" content="{e(l['name'])}"><meta property="og:description" content="{e(desc)}">
<meta name="theme-color" content="#14603e">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<link rel="stylesheet" href="{PATH}/assets/style.css?v={VER}">
<script type="application/ld+json">{ld}</script>
</head><body class="doc">
<div class="shell">
<header class="band"><div class="inner">
<p class="wordmark"><a href="{PATH}/">Gulf Coast Farm<span class="co">Mobile &amp; Baldwin County, Alabama</span></a></p>
<a class="add" href="{PATH}/?id={e(l['id'])}">Open on the map &rarr;</a>
</div></header>
<main class="page">
<h1 class="big">{e(l['name'])}</h1>
<p class="lede"><span class="kind t-{e(l['type'])}"><i class="sw"></i>{e(TYPE_LABEL[l['type']])}</span> in {e(l['city'])}, {e(l['county'])} County{' <span class="unconf">Unconfirmed</span>' if l['status'] != 'live' else ''}</p>
{pending}
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
<p><a href="{PATH}/submit.html?id={e(l['id'])}&mode=update">Own this listing or see an error? Send an update.</a></p>
<p class="fine">Source: {e(l['source'])}. Last checked {e(l['last_verified'])}. Hours and availability change with the season; confirm before you go.</p>
</div>
</main>
<footer class="site"><div class="inner">Gulf Coast Farm is a free community project for Mobile and Baldwin County. <a href="{PATH}/">All farms and markets</a> &middot; <a href="{PATH}/submit.html">Add a listing</a></div></footer>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
var m=L.map('mini',{{scrollWheelZoom:false}}).setView([{l['lat']},{l['lng']}],{13 if exact else 10});
L.tileLayer('{TILES}',{{maxZoom:19,attribution:'{TILE_ATTR}'}}).addTo(m);
L.marker([{l['lat']},{l['lng']}],{{icon:L.divIcon({{className:'',html:'<div class="dot {e(l['type'])} {'' if l['status'] == 'live' else 'unconfirmed'}"></div>',iconSize:[16,16],iconAnchor:[8,8]}})}}).addTo(m);
</script>
</body></html>"""
    d = os.path.join(outdir, l['id'])
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w').write(page)
    urls.append(f"{BASE}/l/{l['id']}/")

open(os.path.join(ROOT, 'sitemap.xml'), 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'<url><loc>{u}</loc><lastmod>{date.today().isoformat()}</lastmod></url>\n' for u in urls) + '</urlset>\n')
open(os.path.join(ROOT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
open(os.path.join(ROOT, 'manifest.webmanifest'), 'w').write(json.dumps({'name': 'Gulf Coast Farm: Mobile & Baldwin', 'short_name': 'Gulf Coast', 'start_url': PATH + '/', 'display': 'standalone', 'background_color': '#f1f2ee', 'theme_color': '#14603e', 'icons': [{'src': 'assets/icon.svg', 'sizes': 'any', 'type': 'image/svg+xml'}]}, indent=1))

# stamp the domain into index.html canonical, and the asset version into both pages
idx = os.path.join(ROOT, 'index.html')
s = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{BASE}/">', open(idx).read())
open(idx, 'w').write(s)

for name in ('index.html', 'submit.html'):
    fp = os.path.join(ROOT, name)
    t = open(fp).read()
    t = re.sub(r'(assets/(?:style\.css|app\.js))(\?v=[0-9a-f]+)?', rf'\1?v={VER}', t)
    open(fp, 'w').write(t)

print(f'wrote {len(urls) - 2} listing pages, sitemap with {len(urls)} urls, domain {DOMAIN}, assets v{VER}')
