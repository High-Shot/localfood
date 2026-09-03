import json, re, html, time, urllib.request, urllib.parse, sys
from datetime import date

TODAY = date.today().isoformat()
SGA = json.load(open('/home/claude/sga_members.json'))

BALDWIN = {'Bay Minette','Bon Secour','Daphne','Elberta','Fairhope','Foley','Gulf Shores','Lillian','Loxley','Magnolia Springs','Orange Beach','Perdido','Point Clear','Robertsdale','Seminole','Silverhill','Spanish Fort','Stapleton','Stockton','Summerdale','Montrose'}
MOBILE = {'Bayou La Batre','Chunchula','Citronelle','Coden','Creola','Dauphin Island','Eight Mile','Grand Bay','Irvington','Mobile','Mount Vernon','Prichard','Saraland','Satsuma','Semmes','Theodore','Wilmer'}

def county(city):
    if city in BALDWIN: return 'Baldwin'
    if city in MOBILE: return 'Mobile'
    return None

# product normalization -> category tags
CAT = {
 'Beef':'beef','Pork':'pork','Chicken':'chicken','Lamb':'lamb','Sheep':'lamb','Turkey':'poultry','Quail and Quail Eggs':'eggs',
 'Eggs':'eggs','Milk':'dairy','Cheese':'dairy','Butter':'dairy','Ice Cream':'dairy','Yogurt':'dairy',
 'Honey':'honey','Beeswax Products':'honey',
 'Seafood':'seafood','Oysters':'seafood','Saltwater Shrimp':'seafood',
 'Pecans':'nuts','Peanuts':'nuts','Roasted/Boiled Peanuts':'nuts',
 'Satsumas':'citrus','Blueberries':'berries','Blackberries':'berries','Strawberries':'berries','Raspberries':'berries','U-Pick Fruit':'upick',
 'Peaches':'fruit','Pears':'fruit','Plums':'fruit','Watermelon':'fruit','Cantaloupe':'fruit','Muscadine Grapes':'fruit','Pumpkins':'fruit','Pumpkin Patch':'upick',
 'Flowers':'flowers','Fresh Cut Flowers':'flowers',
 'Baked Goods':'baked','Candy/Confections':'baked',
 'Jams/Jellies':'pantry','Acidified Foods* (Pickles, Salsas, Relishes)':'pantry','Sauces/Condiments':'pantry','Marinades/Dressings':'pantry','Dry Rubs/Spices':'pantry','Grits, cornmeal, flour':'pantry','Syrup':'pantry',
 'Container Plants/Greenhouse & Nursery Products/Shrubs/Etc.':'plants','Container Plants':'plants',
}
VEG = {'Lettuce','Sweet Potatoes','Potatoes','Cabbage','Peas','Cucumbers','Okra','Sweet Corn','Greens','Tomatoes','Squash','Beans','Peppers','Herbs','Microgreens','Mushrooms','Garlic','Onions','Eggplants','Corn (Field)','Zucchini','Spinach','Turnips','Rutabegas','Swiss Chard','Tomatillos','Broccoli','Carrots'}
SKIP_PRODUCTS = {'Hay','Cotton/Cotton Products','Turfgrass','Wood Products','Soybeans','Wheat'}

def cats(products):
    out=set()
    for p in products:
        if p in SKIP_PRODUCTS: continue
        if p in VEG: out.add('vegetables')
        elif p in CAT: out.add(CAT[p])
    return sorted(out)

def slugify(s):
    s=re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')
    return s

def clean_html(s):
    if not s: return ''
    s=re.sub(r'<[^>]+>',' ',s)
    s=html.unescape(s)
    return re.sub(r'\s+',' ',s).strip()

def fix_url(u):
    if not u: return None
    u=u.strip()
    if not u: return None
    if 'fbclid' in u: u=u.split('?')[0]
    if not u.lower().startswith('http'): u='https://'+u
    return u.replace('https://WWW.','https://www.').lower() if u.startswith('https://WWW.') else u

EXCLUDE_SGA = {1054,25,1270,1121,2086,845,1731,1963,1848}  # out of county, orgs, turf, plants-only

listings=[]
for m in SGA:
    if m['id'] in EXCLUDE_SGA: continue
    if not m['latitude']: continue
    if not (30.15<=m['latitude']<=31.35 and -88.6<=m['longitude']<=-87.35): continue
    city=(m['city'] or '').strip()
    c=county(city)
    if not c: 
        print('no county for',m['name'],city,file=sys.stderr); continue
    prods=[p['name'] for p in m['products']]
    btypes=[b['name'] for b in m['business_types']]
    if 'Farmers Markets' in btypes: t='market'
    elif 'Seafood' in btypes and 'Farm' not in btypes: t='seafood'
    elif 'Specialty Store' in btypes and 'Farm' not in btypes: t='store'
    else: t='farm'
    if m['id'] in (1995,1996): t='store'  # 3 Arrows Meat Co is a butcher shop
    buy=[]
    if m.get('purchase_on_farm'): buy.append('On-farm pickup')
    if m.get('purchase_pick_your_own'): buy.append('U-pick')
    if m.get('purchase_farmers_market'): buy.append('Farmers market')
    if m.get('purchase_local_delivery'): buy.append('Local delivery')
    if m.get('purchase_online'): buy.append('Online orders')
    if m.get('purchase_retail'): buy.append('Retail stores')
    if m.get('purchase_wholesale'): buy.append('Wholesale')
    if m.get('purchase_restaurant'): buy.append('Restaurants')
    addr=m['address'] or ''
    precision='exact'
    if addr.lower().startswith('p.o') or addr.lower().startswith('po box'):
        precision='town'; addr=''
    listings.append(dict(
        id=slugify(m['name']),
        name=m['name'].strip(),
        type=t,
        county=c,
        state='AL',
        city=city,
        address=addr,
        zip=(m['zip'] or '')[:5],
        lat=round(m['latitude'],5) if precision=='exact' else None,
        lng=round(m['longitude'],5) if precision=='exact' else None,
        pin_precision=precision,
        products=[p for p in prods if p not in SKIP_PRODUCTS],
        categories=cats(prods),
        description=clean_html(m['bio'])[:900],
        phone=m['phone'],
        email=m['email'],
        website=fix_url(m['website']),
        facebook=m['facebook_link'],
        instagram=m['instagram_link'],
        tiktok=m.get('tiktok_link'),
        hours=clean_html(m['hours_of_operation']) if m.get('hours_of_operation') else '',
        how_to_buy=buy,
        sells_at=clean_html(m['sold_at_farmers_market']) if m.get('sold_at_farmers_market') else '',
        certified_organic=bool(m.get('certified_organic')),
        status='live',
        source='Sweet Grown Alabama directory',
        source_url=f'https://www.sweetgrownalabama.org/sga-members/{m["id"]}',
        last_verified=TODAY,
    ))

# ---- manual entries (state Ag Dept 2026 SFMNP list, u-pick directory, city sites) ----
AG='Alabama Dept. of Agriculture 2026 farmers market list'
AGURL='https://agi.alabama.gov/farmersmarket/wp-content/uploads/sites/9/2023/02/2026-statewide-redemption-sites.pdf'
PYO='PickYourOwn.org Mobile-area directory'
PYOURL='https://pickyourown.org/ALmobile.htm'
def M(**k):
    d=dict(id=None,type='farm',state='AL',address='',zip='',lat=None,lng=None,pin_precision='exact',products=[],categories=[],description='',phone=None,email=None,website=None,facebook=None,instagram=None,tiktok=None,hours='',how_to_buy=[],sells_at='',certified_organic=False,status='live',source='',source_url='',last_verified=TODAY)
    d.update(k); d['id']=slugify(d['name']); 
    if not d['categories']: d['categories']=cats(d['products'])
    return d

manual=[
 # Markets, Baldwin
 M(name='Fairhope Outdoor Farmers Market',type='market',county='Baldwin',city='Fairhope',address='501 Fairhope Ave',zip='36532',hours='Thursdays 2 to 6 pm, April through June, plus first Saturdays of the month. Behind the Fairhope Public Library.',phone='(251) 928-1474',email='bethann.greisinger@fairhopeal.gov',description='City-run open-air market behind the public library. Spring season on Thursdays, plus first-Saturday markets.',categories=['vegetables','fruit','eggs','baked','honey'],source=AG,source_url=AGURL),
 M(name='Orange Beach Pop-Up Farmers Market',type='market',county='Baldwin',city='Orange Beach',address='26425 Canal Rd',zip='36561',hours='Select Sundays in spring, 10 am to 2 pm (2026 dates: April 19, May 3, June 7). Moves to the Community Center in bad weather.',website='https://www.orangebeachal.gov/1652/Pop-Up-Farmers-Market',description='Parks and Recreation pop-up market at Waterfront Park with local produce, artisan goods, and a food truck.',categories=['vegetables','fruit','baked'],source='City of Orange Beach',source_url='https://www.orangebeachal.gov/1652/Pop-Up-Farmers-Market'),
 M(name="Daphne Farmer's Market",type='market',county='Baldwin',city='Daphne',address='',zip='36526',pin_precision='town',phone='(251) 202-9767',facebook='https://www.facebook.com/daphnefarmersmarket/',website='https://daphnemuseumalabama.org',description='Friday afternoon market with local produce, baked goods, and Gulf fish. Confirm current season and location before going.',categories=['vegetables','seafood','baked'],status='pending',source='Facebook page (schedule not confirmed for 2026)',source_url='https://www.facebook.com/daphnefarmersmarket/'),
 M(name='Chicago Street Farmers Market',type='market',county='Baldwin',city='Foley',address='',zip='36535',pin_precision='town',description='Friday evening market run by the Foley Convention and Visitors Bureau: plants, produce, eggs, baked goods, bay shrimp, grass-fed beef. Confirm current season before going.',categories=['vegetables','eggs','seafood','beef','baked'],status='pending',source='LocalHarvest listing (undated)',source_url='https://www.localharvest.org/daphne-al/farmers-markets'),
 # Markets, Mobile
 M(name='Market in the Park',type='market',county='Mobile',city='Mobile',address='300 Conti St',zip='36602',hours='Saturdays 7:30 am to noon. Spring: May 4 through July 6. Fall: October 11 through November 15.',phone='(251) 208-1551',email='gloria.hernandez@cityofmobile.gov',description='City of Mobile farmers market in Cathedral Square, downtown.',categories=['vegetables','fruit','eggs','baked','honey'],source=AG,source_url=AGURL),
 M(name='Prichard Farmers Market',type='market',county='Mobile',city='Prichard',address='204 S Wilson Ave',zip='36610',hours='First and third Saturdays, April through December, 8 am to noon.',description='Community farmers market in Prichard.',categories=['vegetables','fruit'],source=AG,source_url=AGURL),
 M(name='Prichard Main Street Farmers Market',type='market',county='Mobile',city='Prichard',address='2501 W Main St',zip='36610',hours='Second and fourth Thursdays, mid May through late November.',phone='(251) 289-9303',description='Twice-monthly Thursday market on West Main Street.',categories=['vegetables','fruit'],source=AG,source_url=AGURL),
 M(name='Shiloh Avenue Farmers Market',type='market',county='Mobile',city='Mobile',address='300 New Shiloh Ave',zip='36607',hours='Second and fourth Wednesdays, mid May through late November.',phone='(251) 289-9303',email='phadep1@hotmail.com',description='Twice-monthly Wednesday market.',categories=['vegetables','fruit'],source=AG,source_url=AGURL),
 M(name='Saraland Farmers Market',type='market',county='Mobile',city='Saraland',address='712 A Saraland Blvd',zip='36571',hours='Tuesdays 3 to 6 pm, late April through late July.',phone='(251) 358-3305',email='aflowers@saraland.org',description='City of Saraland Tuesday afternoon market.',categories=['vegetables','fruit','baked'],source=AG,source_url=AGURL),
 # Farm stands / u-pick, Baldwin
 M(name="Lyrene's Blueberry Farm",county='Baldwin',city='Fairhope',address='11911-A State Highway 104',zip='36532',phone='(251) 928-0925',hours='Monday through Saturday 7 am to noon, Fridays until 7 pm, roughly early May through late July.',products=['Blueberries','U-Pick Fruit'],how_to_buy=['U-pick','On-farm pickup'],description='U-pick and pre-picked blueberries, in Baldwin County for over 30 years. On Highway 104 two miles east of 181.',source=f'{AG}; {PYO}',source_url=PYOURL),
 M(name='Hillcrest Farm',county='Baldwin',city='Elberta',address='30497 Hixson Rd',zip='36530',phone='(251) 962-2500',email='hillcrestfarmupick@yahoo.com',hours='Check Facebook for current hours. Blueberries mid May to July 1; muscadines August 1 to mid September. Farm store open year-round.',products=['Blueberries','Muscadine Grapes','U-Pick Fruit','Honey','Eggs','Jams/Jellies','Flowers','Ice Cream'],how_to_buy=['U-pick','On-farm pickup'],description='U-pick blueberries and muscadines with a year-round farm store: brown eggs, honey from hives on the farm, preserves, hot sauce, ice cream, and home-grown produce. Four miles west of the Lillian bridge on Highway 98.',source=f'{AG}; {PYO}',source_url=PYOURL),
 M(name='Baldwin Blueberries',county='Baldwin',city='Loxley',address='27608 County Road 65',zip='36551',phone='(251) 234-0444',hours='7 am to noon Monday through Saturday, mid May through early July.',products=['Blueberries','U-Pick Fruit'],how_to_buy=['U-pick','On-farm pickup'],description='No-pesticide u-pick and pre-picked blueberries. Formerly Suberi\'s Blueberries.',source=f'{AG}; {PYO}',source_url=PYOURL),
 M(name='Norden & Sons',county='Baldwin',city='Silverhill',address='16370 4th Ave',zip='36576',phone='(251) 945-5232',email='beekeeper@gulftel.com',hours='September through October.',products=['Muscadine Grapes','U-Pick Fruit','Honey'],how_to_buy=['U-pick','On-farm pickup'],description='U-pick red and white grapes and muscadines in Silverhill. Listed as a state farm stand.',source=f'{AG}; {PYO}',source_url=PYOURL),
 M(name='Perdido Vineyards',county='Baldwin',city='Perdido',address='22100 County Road 47',zip='36562',phone='(251) 937-9463',email='perdidovineyards@gmail.com',website='https://www.perdidovineyards.com',products=['Muscadine Grapes','Wine'],categories=['fruit','pantry'],how_to_buy=['On-farm pickup'],description='Muscadine winery near I-65 exit 45 with a tasting room and seasonal u-pick when the crop allows. Listed as a state farm stand. Call for u-pick status.',source=f'{AG}; {PYO}',source_url=PYOURL),
 M(name='Loxley Farm Market',type='store',county='Baldwin',city='Loxley',address='',zip='36551',pin_precision='town',products=[],categories=['vegetables','fruit'],description='Listed by the state as a Baldwin County farm stand. Address and hours not yet confirmed.',status='pending',source=AG,source_url=AGURL),
 M(name='Bee Natural Farm',county='Baldwin',city='Fairhope',address='9711 Twin Beech Rd',zip='36532',phone='(251) 367-3238',email='Beenaturalfarm549@gmail.com',hours='June through July, six days a week sunup to sundown, closed Wednesdays.',products=['Blueberries','U-Pick Fruit'],how_to_buy=['U-pick'],description='Naturally grown u-pick blueberries east of Fairhope High School.',source=PYO,source_url=PYOURL),
 M(name='Weeks Bay Plantation',county='Baldwin',city='Fairhope',address='12562 Mary Ann Beach Rd',zip='36532',phone='(251) 928-7786',email='tynes@laberryfarms.com',hours='Seasonal, check Facebook for dates and hours.',products=['Blueberries','U-Pick Fruit'],how_to_buy=['U-pick'],description='U-pick blueberry farm (also known as LA Berry Farms) off Highway 98 south of Fairhope. Natural practices.',source=PYO,source_url=PYOURL),
 M(name='Meadowlark Farms of Fairhope',county='Baldwin',city='Fairhope',address='12744 Mary Ann Beach Rd',zip='36532',phone='(256) 617-0467',email='info@meadowlarkfarmsoffairhope.com',hours='Blueberries mid May to mid July. Fri and Sat 7 am to 2 pm, Sun 1 to 5 pm, weekdays by appointment. Verify on Facebook.',products=['Blueberries','U-Pick Fruit'],how_to_buy=['U-pick'],description='Naturally grown u-pick blueberries with a refreshment stand.',status='pending',source=f'{PYO} (added 2022)',source_url=PYOURL),
 M(name='Reeves Farm',county='Baldwin',city='Stapleton',address='34605 US Highway 31',zip='36578',phone='(251) 232-0572',email='reeve528@bellsouth.net',hours='Sunday to Friday 7 am to 7 pm in season. Blackberries and blueberries in June.',products=['Blackberries','Blueberries','Strawberries','Muscadine Grapes','U-Pick Fruit'],how_to_buy=['U-pick'],description='U-pick berries, figs, and muscadines just south of the Highway 59 and 31 intersection.',status='pending',source=PYO,source_url=PYOURL),
 M(name='Peebles Farm',county='Baldwin',city='Lillian',address='11850 County Road 91',zip='36549',phone='(251) 494-4730',email='peeb.farm@hotmail.com',hours='Monday through Saturday 7 am to 5 pm, May through July. Pecans in fall and winter.',products=['Blackberries','Blueberries','Pecans','U-Pick Fruit'],how_to_buy=['U-pick','On-farm pickup'],description='No-pesticide u-pick blackberries and blueberries, pecans in fall. One mile south of Highway 98 on County Road 91.',status='pending',source=f'{PYO} (last updated 2018)',source_url=PYOURL),
 M(name='Zimlich Ideal Farms',county='Baldwin',city='Robertsdale',address='21790 Ranchette Rd',zip='36567',phone='(251) 947-8819',email='waynezimlich@gulftel.com',hours='Call ahead to arrange a visit.',products=['Tomatoes','Squash','Sweet Corn','Eggplants','Cucumbers','Beans','Okra','Peppers','Blueberries','Eggs'],description='Small farm south of Robertsdale with seasonal vegetables, blueberries, and eggs. Call before visiting.',status='pending',source=f'{PYO} (last updated 2009)',source_url=PYOURL),
 M(name='Burris Farm Market',type='store',county='Baldwin',city='Loxley',address='3100 S Hickory St',zip='36551',description='Long-running roadside farm market on Highway 59 in Loxley with produce, pies, breads, and canned goods. Address and hours to be confirmed with the market.',categories=['vegetables','fruit','baked','pantry'],status='pending',source='Visit Coastal Alabama article',source_url='http://www.visitcoastalalabama.org/fresh-flavorful-coastal-farmers-markets/'),
 M(name='Allegri Farm Market',type='store',county='Baldwin',city='Daphne',address='',zip='36526',lat=30.60338,lng=-87.85265,phone='(251) 621-1955',instagram='https://www.instagram.com/allegri.farm.market/',description='Farm market at the corner of County Road 64 and Highway 181 with fresh produce, satsumas in season, and local foods.',categories=['vegetables','fruit','citrus','pantry'],status='pending',source='Instagram and Nextdoor listings',source_url='https://www.instagram.com/allegri.farm.market/'),
 # Farm stands / u-pick, Mobile
 M(name='Oak Hill Produce',county='Mobile',city='Grand Bay',address='7600 Grand Bay Wilmer Rd',zip='36541',phone='(251) 865-2001',email='info@oakhillproduce.com',website='https://oakhillproduce.com',hours='Website posts daily availability.',products=['Strawberries','Blueberries','Sweet Corn','Tomatoes','Squash','Cucumbers','Peas','Peppers','Eggplants','Broccoli','U-Pick Fruit'],how_to_buy=['U-pick','On-farm pickup'],description='Farm stand and u-pick with strawberries, blueberries, and a full run of summer vegetables. Accepts SFMNP vouchers.',source=f'{AG}; {PYO}',source_url=PYOURL),
 M(name="Betty's Berry Farm",county='Mobile',city='Wilmer',address='3887 Driskell Loop Rd',zip='36587',phone='(251) 649-1711',email='bettysberryfarm@aol.com',hours='Self-serve 6 am to 10 pm, seven days, May 15 to July 15.',products=['Blueberries','Blackberries','U-Pick Fruit'],how_to_buy=['U-pick'],description='Self-serve u-pick blueberries and blackberries in Wilmer.',source=f'{AG}; {PYO}',source_url=PYOURL),
 M(name='Blue Moon Farm',county='Mobile',city='Mobile',address='13620 Tom Gaston Rd',zip='36695',phone='(251) 263-2008',email='BlueMoonFarm.GrandBay@gmail.com',hours='In season daily 8 am to 7 pm, closed Monday and Tuesday. Blueberries from mid May.',products=['Blueberries','Fresh Cut Flowers','U-Pick Fruit'],how_to_buy=['U-pick'],description='Certified Naturally Grown u-pick blueberries and u-cut flowers. Family friendly with a picnic area. Call for directions; GPS routes are unreliable.',source=f'{PYO} (updated 2024)',source_url=PYOURL),
 M(name='Brannan Blueberry Brae',county='Mobile',city='Mobile',address='700B Grand Bay Wilmer Rd N',zip='36608',phone='(251) 327-6503',hours='Late May through early July, Monday through Saturday 7 am to 1 pm.',products=['Blueberries','U-Pick Fruit'],how_to_buy=['U-pick'],description='U-pick blueberries off Tanner Williams Road. Cash only.',source=f'{PYO} (updated 2023)',source_url=PYOURL),
 M(name='Ken Buck Farms',county='Mobile',city='Irvington',address='7701 Ken Buck Rd',zip='36544',phone='(251) 824-2838',hours='Monday through Saturday 8 am to 5 pm in season.',products=['Peaches','Sweet Corn','Peas','Pecans','Satsumas'],how_to_buy=['On-farm pickup'],description='Peaches in May and June, Silver King corn and purple hull peas in early summer, pecans and satsumas in November and December.',status='pending',source=f'{PYO} (added 2014)',source_url=PYOURL),
 M(name='Fresh Off The Farm',county='Mobile',city='Theodore',address='3201 Bay Rd',zip='36582',phone='(251) 623-1868',hours='7 am to 6 pm, seven days in season. U-pick by reservation.',products=['Tomatoes','Cucumbers','Peppers','Eggplants','Okra','Squash','Peas','Beans','Watermelon'],how_to_buy=['On-farm pickup','U-pick'],description='Vegetable farm in Theodore with peas, beans, tomatoes, and melons. U-pick by reservation only.',status='pending',source=f'{PYO} (added 2014)',source_url=PYOURL),
]
listings += manual

# ---- geocode anything missing coordinates (Nominatim, 1 req/sec) ----
def geocode(q):
    # US Census geocoder first (no key, no rate limit for light use), Nominatim as fallback
    url='https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?'+urllib.parse.urlencode({'address':q,'benchmark':'Public_AR_Current','format':'json'})
    try:
        r=json.load(urllib.request.urlopen(url,timeout=25))
        m=r['result']['addressMatches']
        if m: return float(m[0]['coordinates']['y']),float(m[0]['coordinates']['x'])
    except Exception as e:
        print('census error',q,e,file=sys.stderr)
    url='https://nominatim.openstreetmap.org/search?'+urllib.parse.urlencode({'q':q,'format':'json','limit':1,'countrycodes':'us'})
    req=urllib.request.Request(url,headers={'User-Agent':'localfoodmap-build/0.1 (community project)'})
    try:
        time.sleep(1.5)
        r=json.load(urllib.request.urlopen(req,timeout=20))
        if r: return float(r[0]['lat']),float(r[0]['lon'])
    except Exception as e:
        print('nominatim error',q,e,file=sys.stderr)
    return None,None

TOWN={'Daphne':(30.6031,-87.9036),'Foley':(30.4066,-87.6836),'Loxley':(30.6188,-87.7533),'Point Clear':(30.4830,-87.9203),'Fairhope':(30.5230,-87.9033),'Orange Beach':(30.2944,-87.5736),'Mobile':(30.6944,-88.0431),'Prichard':(30.7388,-88.0789),'Saraland':(30.8207,-88.0706),'Elberta':(30.4144,-87.5978),'Silverhill':(30.5430,-87.7500),'Perdido':(31.0035,-87.6242),'Stapleton':(30.7405,-87.7897),'Lillian':(30.4133,-87.4413),'Robertsdale':(30.5538,-87.7119),'Grand Bay':(30.4750,-88.3420),'Wilmer':(30.8146,-88.3634),'Theodore':(30.5477,-88.1753),'Irvington':(30.4930,-88.2350)}
STATE_NAME={'AL':'Alabama','FL':'Florida'}
for L in listings:
    if L['lat'] is None:
        stt=L.get('state','AL'); stnm=STATE_NAME.get(stt,'Alabama')
        if L['pin_precision']=='town' or not L['address']:
            L['pin_precision']='town'
            if L['city'] in TOWN: L['lat'],L['lng']=TOWN[L['city']]
            else:
                time.sleep(1.1); L['lat'],L['lng']=geocode(f"{L['city']}, {stnm}")
        else:
            lat,lng=geocode(f"{L['address']}, {L['city']}, {stt} {L['zip']}")
            if lat is None:
                print('FALLBACK to town for',L['name'],file=sys.stderr)
                L['pin_precision']='town'
                lat,lng=geocode(f"{L['city']}, {stnm}")
            L['lat'],L['lng']=lat,lng
        if L['lat']: L['lat'],L['lng']=round(L['lat'],5),round(L['lng'],5)

# dedupe ids
seen={}
for L in listings:
    if L['id'] in seen:
        L['id']+='-'+slugify(L['city'])
    seen[L['id']]=1
listings.sort(key=lambda x:(x.get('state','AL'),x['county'],x['name'].lower()))
json.dump(listings,open('data/listings.json','w'),indent=1)
print(len(listings),'listings;',sum(1 for l in listings if l['status']=='live'),'live;',sum(1 for l in listings if l['status']=='pending'),'pending')
from collections import Counter
print(Counter(l['county'] for l in listings)); print(Counter(l['type'] for l in listings))
print('missing coords:',[l['name'] for l in listings if not l['lat']])
