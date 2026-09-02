#!/usr/bin/env python3
"""Generate /l/<id>/index.html for every live or pending listing, plus sitemap.xml, robots.txt, manifest.
Run from the repo root: python3 scripts/build_site.py
Set SITE_DOMAIN (and SITE_PATH for a subpath deploy) in env or edit DOMAIN below."""
import json, os, re, shutil, html, sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = os.environ.get('SITE_DOMAIN', 'localfood.example.com')
PATH = os.environ.get('SITE_PATH', '').rstrip('/')  # e.g. '/localfood' for a GitHub Pages project site, '' for a custom domain
BASE = f'https://{DOMAIN}{PATH}'
TYPE_LABEL = {'farm': 'Farm', 'market': 'Farmers market', 'seafood': 'Seafood', 'store': 'Farm store'}
SCHEMA_TYPE = {'farm': 'LocalBusiness', 'market': 'LocalBusiness', 'seafood': 'FoodEstablishment', 'store': 'GroceryStore'}
e = lambda s: html.escape(str(s if s is not None else ''), quote=True)

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
    pending = '' if l['status'] == 'live' else '<div class="notice">We have not confirmed this listing is current. Call or check their page before you drive out.</div>'
    dirs = f"https://www.google.com/maps/dir/?api=1&destination={e(addr if exact else '')}" if exact else None
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{BASE}/l/{e(l['id'])}/">
<meta property="og:title" content="{e(l['name'])}"><meta property="og:description" content="{e(desc)}">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<link rel="stylesheet" href="{PATH}/assets/style.css">
<script type="application/ld+json">{ld}</script>
</head><body>
<main class="page">
<header class="top"><h1><a href="{PATH}/" style="text-decoration:none;color:inherit">Local Food Map <span>Mobile &amp; Baldwin</span></a></h1><a class="add" href="{PATH}/?id={e(l['id'])}">Open on the map</a></header>
<h1 class="big">{e(l['name'])}</h1>
<p class="lede"><span class="dot {e(l['type'])}"></span> {e(TYPE_LABEL[l['type']])} in {e(l['city'])}, {e(l['county'])} County{' <span class="pendingtag">unverified</span>' if l['status'] != 'live' else ''}</p>
{pending}
<div class="detail" style="padding:0">
{('<p>' + e(l['description']) + '</p>') if l['description'] else ''}
<div class="actions">{a('Directions', dirs)}{('<a class="btn" href="tel:' + e(''.join(ch for ch in l['phone'] if ch.isdigit() or ch == '+')) + '">Call</a>') if l['phone'] else ''}{a('Website', l['website'])}{a('Facebook', l['facebook'])}{a('Instagram', l['instagram'])}{a('TikTok', l['tiktok'])}{('<a class="btn" href="mailto:' + e(l['email']) + '">Email</a>') if l['email'] else ''}</div>
<div id="mini" class="miniMap"></div>
<dl>
<dt>Offers</dt><dd>{e(offers or 'Not listed')}</dd>
{('<dt>Hours</dt><dd>' + e(l['hours']) + '</dd>') if l['hours'] else ''}
{('<dt>How to buy</dt><dd>' + e(', '.join(l['how_to_buy'])) + '</dd>') if l['how_to_buy'] else ''}
{('<dt>Sells at</dt><dd>' + e(l['sells_at']) + '</dd>') if l['sells_at'] else ''}
<dt>Address</dt><dd>{e(addr)}{'' if exact else ' (exact location not published)'}</dd>
{('<dt>Phone</dt><dd>' + e(l['phone']) + '</dd>') if l['phone'] else ''}
</dl>
<p><a href="{PATH}/submit.html?id={e(l['id'])}&mode=update">Own this listing or see an error? Send an update.</a></p>
<p class="fine">Source: {e(l['source'])}. Last checked {e(l['last_verified'])}. Hours and availability change with the season; confirm before you go.</p>
</div>
</main>
<footer class="site">Local Food Map is a free community project for Mobile and Baldwin County. <a href="{PATH}/">All farms and markets</a> &middot; <a href="{PATH}/submit.html">Add a listing</a></footer>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
var m=L.map('mini',{{scrollWheelZoom:false}}).setView([{l['lat']},{l['lng']}],{13 if exact else 10});
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}}).addTo(m);
L.marker([{l['lat']},{l['lng']}],{{icon:L.divIcon({{className:'',html:'<div class="pin {e(l['type'])} {'' if exact else 'town'}"></div>',iconSize:[18,18],iconAnchor:[9,9]}})}}).addTo(m);
</script>
</body></html>"""
    d = os.path.join(outdir, l['id'])
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w').write(page)
    urls.append(f"{BASE}/l/{l['id']}/")

open(os.path.join(ROOT, 'sitemap.xml'), 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'<url><loc>{u}</loc><lastmod>{date.today().isoformat()}</lastmod></url>\n' for u in urls) + '</urlset>\n')
open(os.path.join(ROOT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
open(os.path.join(ROOT, 'manifest.webmanifest'), 'w').write(json.dumps({'name': 'Local Food Map: Mobile & Baldwin', 'short_name': 'Local Food', 'start_url': PATH + '/', 'display': 'standalone', 'background_color': '#ffffff', 'theme_color': '#2c5f49', 'icons': [{'src': 'assets/icon.svg', 'sizes': 'any', 'type': 'image/svg+xml'}]}, indent=1))

# stamp the domain into index.html canonical
idx = os.path.join(ROOT, 'index.html')
s = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{BASE}/">', open(idx).read())
open(idx, 'w').write(s)
print(f'wrote {len(urls) - 2} listing pages, sitemap with {len(urls)} urls, domain {DOMAIN}')
