#!/usr/bin/env python3
"""Pull approved rows from Airtable into data/listings.json.
Airtable base needs two tables:
  Listings     the live directory (same columns as data/listings.json; Status = live | pending | retired)
  Submissions  raw form submissions (written by functions/api/submit.js)
Workflow: review a Submission, copy or merge it into Listings, set Status=live. Then run this script (locally or in CI)
followed by scripts/build_site.py, and deploy.
Env: AIRTABLE_TOKEN, AIRTABLE_BASE, AIRTABLE_LISTINGS_TABLE (default 'Listings').
First-time setup: python3 scripts/sync_airtable.py --push  uploads data/listings.json into the Listings table."""
import json, os, sys, time, urllib.request, urllib.parse

TOKEN = os.environ.get('AIRTABLE_TOKEN'); BASE = os.environ.get('AIRTABLE_BASE'); TABLE = os.environ.get('AIRTABLE_LISTINGS_TABLE', 'Listings')
if not TOKEN or not BASE: sys.exit('Set AIRTABLE_TOKEN and AIRTABLE_BASE')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = f'https://api.airtable.com/v0/{BASE}/{urllib.parse.quote(TABLE)}'
H = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
LIST_FIELDS = ['products', 'categories', 'how_to_buy']

def req(url, data=None, method='GET'):
    r = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers=H, method=method)
    return json.load(urllib.request.urlopen(r))

def to_fields(l):
    f = dict(l)
    for k in LIST_FIELDS: f[k] = ', '.join(l.get(k) or [])
    return {k: v for k, v in f.items() if v not in (None, '')}

def from_fields(f):
    l = {k: f.get(k) for k in ['id','name','type','county','city','address','zip','lat','lng','pin_precision','description','phone','email','website','facebook','instagram','tiktok','hours','sells_at','status','source','source_url','last_verified']}
    for k in LIST_FIELDS: l[k] = [x.strip() for x in (f.get(k) or '').split(',') if x.strip()]
    l['certified_organic'] = bool(f.get('certified_organic'))
    for k in ['address','zip','description','hours','sells_at','source','source_url']: l[k] = l[k] or ''
    return l

if '--push' in sys.argv:
    data = json.load(open(os.path.join(ROOT, 'data/listings.json')))
    for i in range(0, len(data), 10):
        req(URL, {'records': [{'fields': to_fields(l)} for l in data[i:i+10]], 'typecast': True}, 'POST'); time.sleep(0.25)
    print('pushed', len(data)); sys.exit()

out, offset = [], None
while True:
    q = {'pageSize': 100, 'filterByFormula': "OR({status}='live',{status}='pending')"}
    if offset: q['offset'] = offset
    r = req(URL + '?' + urllib.parse.urlencode(q))
    out += [from_fields(rec['fields']) for rec in r['records']]
    offset = r.get('offset')
    if not offset: break
out = [l for l in out if l['id'] and l['name'] and l['lat'] and l['lng']]
out.sort(key=lambda x: (x['county'] or '', x['name'].lower()))
json.dump(out, open(os.path.join(ROOT, 'data/listings.json'), 'w'), indent=1)
print('pulled', len(out), 'listings')
