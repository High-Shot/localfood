/* Gulf Coast Farm: Mobile + Baldwin County.
   Map-first. Plain JS, Leaflet, one JSON file, no build step. */
(function () {
  'use strict';

  var CATS = [
    ['beef', 'Beef'], ['pork', 'Pork'], ['chicken', 'Chicken'], ['lamb', 'Lamb'], ['eggs', 'Eggs'], ['dairy', 'Dairy'],
    ['honey', 'Honey'], ['seafood', 'Seafood'], ['vegetables', 'Vegetables'], ['fruit', 'Fruit'], ['berries', 'Berries'],
    ['citrus', 'Satsumas & citrus'], ['nuts', 'Pecans & peanuts'], ['upick', 'U-pick'], ['flowers', 'Flowers'],
    ['baked', 'Baked goods'], ['pantry', 'Jams, sauces & pantry'], ['plants', 'Plants']
  ];
  var TYPES = [['farm', 'Farms'], ['market', 'Farmers markets'], ['seafood', 'Seafood docks'], ['store', 'Farm stores']];
  var TYPE_LABEL = { farm: 'Farm', market: 'Farmers market', seafood: 'Seafood dock', store: 'Farm store' };
  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                'August', 'September', 'October', 'November', 'December'];

  // Gulf Coast harvest windows by month number (1 = Jan). Estimates; edit in one place.
  var SEASON = {
    'Strawberries': [3, 4, 5], 'Blueberries': [5, 6, 7], 'Blackberries': [5, 6], 'Peaches': [5, 6], 'Plums': [5, 6],
    'Satsumas': [10, 11, 12], 'Pecans': [10, 11, 12, 1], 'Muscadine Grapes': [8, 9], 'Sweet Corn': [6, 7],
    'Tomatoes': [5, 6, 7, 10, 11], 'Watermelon': [6, 7, 8], 'Cantaloupe': [6, 7], 'Pumpkins': [10], 'Pumpkin Patch': [10],
    'Peas': [6, 7, 8], 'Okra': [6, 7, 8, 9], 'Squash': [5, 6, 7, 10], 'Cucumbers': [5, 6, 7], 'Greens': [10, 11, 12, 1, 2, 3],
    'Sweet Potatoes': [9, 10, 11, 12], 'Peppers': [6, 7, 8, 9, 10], 'Pears': [8, 9], 'Fresh Cut Flowers': [4, 5, 6, 7, 8, 9, 10],
    'Saltwater Shrimp': [6, 7, 8, 9, 10, 11, 12], 'Oysters': [10, 11, 12, 1, 2, 3], 'Lettuce': [10, 11, 12, 1, 2, 3, 4],
    'Roasted/Boiled Peanuts': [7, 8, 9, 10]
  };

  var $ = function (s, el) { return (el || document).querySelector(s); };
  var esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var narrow = function () { return window.innerWidth <= 860; };

  var state = {
    q: '', type: null, cats: [], season: null, near: null,
    hidePending: false, active: null, hover: null, data: [], monthProducts: []
  };
  var map, markers = {}, hereMarker = null, PANEL_SHELL = '';

  /* ---------------------------------------------------------------- season */

  function inSeasonProducts() {
    var m = new Date().getMonth() + 1;
    return Object.keys(SEASON).filter(function (p) { return SEASON[p].indexOf(m) > -1; });
  }
  function readyAt(l) {
    var out = [];
    for (var i = 0; i < l.products.length; i++) {
      if (state.monthProducts.indexOf(l.products[i]) > -1) out.push(l.products[i]);
    }
    return out;
  }
  function catLabel(c) {
    for (var i = 0; i < CATS.length; i++) if (CATS[i][0] === c) return CATS[i][1];
    return c;
  }

  /* --------------------------------------------------------------- filters */

  function haversine(a, b, c, d) {
    var R = 3958.8, toR = function (x) { return (x * Math.PI) / 180; };
    var dLat = toR(c - a), dLng = toR(d - b);
    var h = Math.pow(Math.sin(dLat / 2), 2) +
            Math.cos(toR(a)) * Math.cos(toR(c)) * Math.pow(Math.sin(dLng / 2), 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  function matches(l) {
    if (state.type && l.type !== state.type) return false;
    if (state.hidePending && l.status !== 'live') return false;
    for (var i = 0; i < state.cats.length; i++) {
      if (l.categories.indexOf(state.cats[i]) === -1) return false;
    }
    if (state.season && l.products.indexOf(state.season) === -1) return false;
    if (state.q) {
      var hay = [l.name, l.city, l.county, l.description, l.products.join(' '),
                 l.categories.join(' '), TYPE_LABEL[l.type]].join(' ').toLowerCase();
      var w = state.q.toLowerCase().split(/\s+/);
      for (var j = 0; j < w.length; j++) if (w[j] && hay.indexOf(w[j]) === -1) return false;
    }
    return true;
  }

  // Ranked by whether you can actually go: something ready this month first,
  // then confirmed listings, then alphabetical. Distance wins when located.
  function filtered() {
    var out = state.data.filter(matches);
    if (state.near) {
      out.forEach(function (l) { l._d = haversine(state.near[0], state.near[1], l.lat, l.lng); });
      out.sort(function (a, b) { return a._d - b._d; });
      return out;
    }
    out.forEach(function (l) { l._ready = readyAt(l); });
    out.sort(function (a, b) {
      if ((b._ready.length > 0) !== (a._ready.length > 0)) return b._ready.length - a._ready.length;
      if ((a.status === 'live') !== (b.status === 'live')) return a.status === 'live' ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    return out;
  }

  /* ------------------------------------------------------------------ map */

  function mapReady() {
    if (!map) return false;
    var s = map.getSize();
    return s.x > 0 && s.y > 0;
  }

  // Pad the fit so the floating panel never covers a pin.
  function fitTo(list, maxZoom) {
    if (!mapReady() || !list.length) return;
    var panel = $('#panel'), pad = 30;
    var opts = { maxZoom: maxZoom || 12 };
    if (narrow()) {
      opts.paddingTopLeft = [pad, pad];
      opts.paddingBottomRight = [pad, (panel ? panel.offsetHeight : 0) + 10];
    } else {
      opts.paddingTopLeft = [(panel ? panel.offsetWidth + 32 : pad), pad];
      opts.paddingBottomRight = [pad, pad];
    }
    map.fitBounds(L.latLngBounds(list.map(function (l) { return [l.lat, l.lng]; })), opts);
  }

  function initMap() {
    map = L.map('map', { zoomControl: false }).setView([30.62, -87.95], 9);
    L.control.zoom({ position: 'topright' }).addTo(map);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    state.data.forEach(function (l) {
      var cls = 'dot ' + l.type + (readyAt(l).length ? ' r' : '') + (l.status !== 'live' ? ' unconfirmed' : '');
      var m = L.marker([l.lat, l.lng], {
        icon: L.divIcon({ className: '', html: '<div class="' + cls + '"></div>', iconSize: [16, 16], iconAnchor: [8, 8] }),
        title: l.name
      });
      m.bindPopup('<b>' + esc(l.name) + '</b>' + esc(TYPE_LABEL[l.type]) + ' &middot; ' + esc(l.city));
      m.on('click', function () { openDetail(l.id); });
      m.on('mouseover', function () { if (!narrow()) markHover(l.id); });
      m.on('mouseout', function () { if (!narrow()) markHover(null); });
      markers[l.id] = m;
    });
  }

  function syncMarkers(rows, refit) {
    if (!map) return;
    var visible = {}, id;
    rows.forEach(function (l) { visible[l.id] = 1; });
    for (id in markers) {
      var on = !!visible[id];
      if (on && !map.hasLayer(markers[id])) markers[id].addTo(map);
      if (!on && map.hasLayer(markers[id])) map.removeLayer(markers[id]);
    }
    if (refit && rows.length) fitTo(rows);
  }

  function markActive(id) {
    for (var k in markers) {
      var el = markers[k].getElement();
      if (el && el.firstChild) el.firstChild.classList.toggle('active', k === id);
    }
  }

  function markHover(id) {
    state.hover = id;
    var list = $('#plist');
    if (!list) return;
    var cards = list.querySelectorAll('.card'), i, c;
    for (i = 0; i < cards.length; i++) {
      c = cards[i];
      c.classList.toggle('is-hover', c.dataset.id === id);
    }
    if (!id) return;
    var card = list.querySelector('.card[data-id="' + id + '"]');
    if (!card) return;
    var box = list.getBoundingClientRect(), r = card.getBoundingClientRect();
    if (r.top < box.top) list.scrollTop += r.top - box.top - 8;
    else if (r.bottom > box.bottom) list.scrollTop += r.bottom - box.bottom + 8;
  }

  /* ---------------------------------------------------------------- render */

  function cardMarkup(l) {
    var r = l._ready || readyAt(l);
    var tags = r.length
      ? r.slice(0, 2).map(function (p) { return '<span class="tag">' + esc(p) + '</span>'; }).join('')
      : l.categories.slice(0, 2).map(function (c) { return '<span class="tag muted">' + esc(catLabel(c)) + '</span>'; }).join('');
    var hours = l.hours ? esc(l.hours) : 'Hours not posted &mdash; call first';
    var dist = (state.near && l._d != null) ? ' &middot; <span class="dist">' + l._d.toFixed(1) + ' mi</span>' : '';
    return '<button class="card t-' + l.type + (state.active === l.id ? ' is-active' : '') + '" data-id="' + esc(l.id) + '">' +
      '<span class="kind"><i class="sw"></i>' + esc(TYPE_LABEL[l.type]) + '</span>' +
      '<h3>' + esc(l.name) + '</h3>' +
      '<p class="where">' + esc(l.city) + ', ' + esc(l.county) + ' County, ' + esc(l.state || 'AL') + dist +
        (l.categories.indexOf('upick') > -1 ? '<span class="upick">U-pick</span>' : '') +
        (l.status !== 'live' ? '<span class="unconf">Unconfirmed</span>' : '') + '</p>' +
      '<div class="tags">' + tags + '</div>' +
      '<p class="hours' + (l.hours ? '' : ' callfirst') + '">' + hours + '</p>' +
      '<span class="go">Directions &rarr;</span>' +
      '</button>';
  }

  function renderList(refit) {
    var rows = filtered();
    var pendingN = state.data.filter(function (l) { return l.status !== 'live'; }).length;
    var listEl = $('#plist'), countEl = $('#count');

    countEl.innerHTML = '<span><b>' + rows.length + '</b> ' +
      (rows.length === state.data.length ? 'places' : 'of ' + state.data.length + ' places') + '</span>' +
      '<label class="toggle"><input type="checkbox" id="hidePending"' + (state.hidePending ? ' checked' : '') +
      '> hide ' + pendingN + ' unconfirmed</label>';
    $('#hidePending').addEventListener('change', function () {
      state.hidePending = this.checked; renderList(true);
    });

    if (!rows.length) {
      listEl.innerHTML = '<div class="notice-row"><div class="big">Nothing matches</div>' +
        '<p>No places fit those filters right now.</p>' +
        '<button class="btn primary" id="resetAll" type="button">Clear filters</button>' +
        '<p style="margin-top:12px">Or <a href="submit.html">add a place we are missing</a>.</p></div>';
      $('#resetAll').addEventListener('click', resetAll);
      syncMarkers(rows, false);
      return;
    }

    var html = '', i;
    for (i = 0; i < rows.length; i++) html += cardMarkup(rows[i]);
    listEl.innerHTML = html;
    listEl.querySelectorAll('.card').forEach(function (b) {
      b.addEventListener('click', function () { openDetail(b.dataset.id); });
      b.addEventListener('mouseenter', function () { if (!narrow()) markActive(b.dataset.id); });
      b.addEventListener('mouseleave', function () { if (!narrow()) markActive(state.active); });
    });
    listEl.scrollTop = 0;
    syncMarkers(rows, refit);
  }

  /* ---------------------------------------------------------------- detail */

  function link(label, href, primary) {
    return href ? '<a class="btn ' + (primary ? 'primary' : '') + '" href="' + esc(href) +
      '" target="_blank" rel="noopener">' + label + '</a>' : '';
  }
  function cell(label, value, flag) {
    if (!value) return '';
    return '<div><dt>' + label + '</dt><dd' + (flag ? ' class="flag"' : '') + '>' + esc(value) + '</dd></div>';
  }

  function openDetail(id) {
    var l = null, i;
    for (i = 0; i < state.data.length; i++) if (state.data[i].id === id) l = state.data[i];
    if (!l) return;
    state.active = id;
    history.replaceState(null, '', '?id=' + encodeURIComponent(id));
    markActive(id);

    if (narrow() && sheetIndex() === 0) setDetent(1);
    if (mapReady()) {
      map.flyTo([l.lat, l.lng], Math.max(map.getZoom(), 13), { duration: reduceMotion ? 0 : 0.6 });
    }

    var exact = l.pin_precision === 'exact' && l.address;
    var st = l.state || 'AL';
    var addr = exact ? (l.address + ', ' + l.city + ', ' + st + ' ' + l.zip) : (l.city + ', ' + st);
    var dirs = exact ? 'https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(addr) : null;
    var ready = readyAt(l);
    var offers = l.products.length ? l.products.join(', ') : l.categories.map(catLabel).join(', ');

    var panel = $('#panel');
    panel.innerHTML = (narrow() ? '<button class="grab" id="grab" aria-label="Resize the list"></button>' : '') +
      '<div class="detail t-' + l.type + '">' +
      '<button class="back" id="back" type="button">&larr; All places</button>' +
      '<span class="kind"><i class="sw"></i>' + esc(TYPE_LABEL[l.type]) + '</span>' +
      '<h2>' + esc(l.name) + '</h2>' +
      '<p class="where">' + esc(l.city) + ', ' + esc(l.county) + ' County, ' + esc(st) +
        (l.categories.indexOf('upick') > -1 ? '<span class="upick">U-pick</span>' : '') + '</p>' +
      (ready.length ? '<div class="notice ready"><b>Ready this month</b>' + esc(ready.join(', ')) + '</div>' : '') +
      (l.status !== 'live' ? '<div class="notice warn"><b>Unconfirmed</b>We have not confirmed this listing is current. Call or check their page before you drive out.</div>' : '') +
      (l.description ? '<p>' + esc(l.description) + '</p>' : '') +
      '<div class="actions">' +
        link('Directions', dirs, true) +
        (l.phone ? '<a class="btn" href="tel:' + esc(l.phone.replace(/[^\d+]/g, '')) + '">Call</a>' : '') +
        link('Website', l.website) + link('Facebook', l.facebook) +
        link('Instagram', l.instagram) + link('TikTok', l.tiktok) +
        (l.email ? '<a class="btn" href="mailto:' + esc(l.email) + '">Email</a>' : '') +
      '</div>' +
      '<dl class="cells">' +
        cell('Offers', offers || 'Not listed') +
        cell('Hours', l.hours || 'Not published, call ahead', !l.hours) +
        cell('How to buy', l.how_to_buy.join(', ')) +
        cell('Sells at', l.sells_at) +
        cell('Address', exact ? addr : addr + ' (exact location not published)') +
        cell('Phone', l.phone) +
        (l.certified_organic ? cell('Certified', 'USDA Organic') : '') +
      '</dl>' +
      '<p style="font-size:13.5px"><a href="submit.html?id=' + encodeURIComponent(l.id) + '&mode=update">Own this listing or see an error? Send an update.</a></p>' +
      '<p class="fine">Source: ' + esc(l.source) + '. Last checked ' + esc(l.last_verified) +
      '. Hours and availability change with the season; confirm before you go. ' +
      '<a href="l/' + esc(l.id) + '/">Permanent link</a></p>' +
      '</div>';

    $('#back').addEventListener('click', backToList);
    if (narrow()) wireGrab();
  }

  function backToList() {
    state.active = null;
    history.replaceState(null, '', location.pathname);
    markActive(null);
    $('#panel').innerHTML = PANEL_SHELL;
    wirePanel();
    buildSeason();
    buildFilters();
    renderList(false);
  }

  function update(refit) {
    if (state.active) { backToList(); }
    else { renderList(refit !== false); }
  }

  function resetAll() {
    state.q = ''; state.type = null; state.cats = [];
    state.season = null; state.hidePending = false;
    var q = $('#q');
    if (q) { q.value = ''; q.parentElement.classList.remove('has-text'); }
    buildSeason(); buildFilters(); renderList(true);
  }

  /* --------------------------------------------------------------- chrome */

  function plate(label, attr, val, pressed, cls) {
    return '<button class="plate ' + (cls || '') + '" type="button" ' + attr + '="' + esc(val) +
      '" aria-pressed="' + (pressed ? 'true' : 'false') + '">' + esc(label) + '</button>';
  }

  function buildSeason() {
    var el = $('#seasonPlates');
    if (!el) return;
    $('#seasonMonth').textContent = MONTHS[new Date().getMonth()];
    var have = state.monthProducts.filter(function (p) {
      return state.data.some(function (l) { return l.products.indexOf(p) > -1; });
    });
    if (!have.length) { el.innerHTML = ''; $('#seasonLede').textContent = 'Every farm, market and seafood dock we can find.'; return; }
    $('#seasonLede').innerHTML = '<b>In season now.</b> Tap one to filter.';
    el.innerHTML = have.map(function (p) { return plate(p, 'data-season', p, state.season === p, 'season'); }).join('');
    el.querySelectorAll('[data-season]').forEach(function (b) {
      b.addEventListener('click', function () {
        state.season = state.season === b.dataset.season ? null : b.dataset.season;
        buildSeason(); update();
      });
    });
  }

  function buildFilters() {
    var f = $('#filters');
    if (!f) return;
    f.innerHTML = TYPES.map(function (p) {
      return plate(p[1], 'data-type', p[0], state.type === p[0]);
    }).join('');
    f.querySelectorAll('[data-type]').forEach(function (b) {
      b.addEventListener('click', function () {
        state.type = state.type === b.dataset.type ? null : b.dataset.type;
        buildFilters(); update();
      });
    });
    buildCats();
  }

  function buildCats() {
    var c = $('#catFilters');
    if (!c) return;
    c.innerHTML = CATS.map(function (p) {
      return plate(p[1], 'data-cat', p[0], state.cats.indexOf(p[0]) > -1);
    }).join('');
    c.querySelectorAll('[data-cat]').forEach(function (b) {
      b.addEventListener('click', function () {
        var v = b.dataset.cat, i = state.cats.indexOf(v);
        if (i > -1) state.cats.splice(i, 1); else state.cats.push(v);
        buildFilters(); update();
      });
    });
    var ol = $('#offerLabel');
    if (ol) ol.textContent = 'What they offer' + (state.cats.length ? ' (' + state.cats.length + ')' : '');
  }

  function wireNear() {
    var btn = $('#nearBtn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      if (state.near) {
        state.near = null;
        btn.setAttribute('aria-pressed', 'false');
        btn.textContent = 'Near me';
        if (hereMarker && map) { map.removeLayer(hereMarker); hereMarker = null; }
        update(); return;
      }
      if (!navigator.geolocation) { btn.disabled = true; btn.textContent = 'No GPS'; return; }
      btn.textContent = 'Locating';
      navigator.geolocation.getCurrentPosition(function (p) {
        state.near = [p.coords.latitude, p.coords.longitude];
        btn.textContent = 'Near me';
        btn.setAttribute('aria-pressed', 'true');
        hereMarker = L.circleMarker(state.near, {
          radius: 7, color: '#14603e', fillColor: '#14603e', fillOpacity: .9, weight: 2, className: 'here'
        }).addTo(map).bindPopup('You are here');
        if (mapReady()) map.setView(state.near, 11);
        update(false);
      }, function () {
        btn.textContent = 'Location off';
        setTimeout(function () { btn.textContent = 'Near me'; }, 2600);
      }, { timeout: 8000 });
    });
  }

  /* ------------------------------------------------------- the phone sheet */

  var DETENTS = ['16dvh', '54dvh', '88dvh'], di = 1;
  function sheetIndex() { return di; }
  function setDetent(i) {
    di = Math.max(0, Math.min(2, i));
    document.documentElement.style.setProperty('--sheet', DETENTS[di]);
    setTimeout(function () { if (map) map.invalidateSize(); }, 300);
  }
  function wireGrab() {
    var grab = $('#grab');
    if (!grab) return;
    grab.addEventListener('click', function () { setDetent(di >= 2 ? 0 : di + 1); });
    grab.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowUp') { setDetent(di + 1); ev.preventDefault(); }
      if (ev.key === 'ArrowDown') { setDetent(di - 1); ev.preventDefault(); }
    });
    var sy = null;
    grab.addEventListener('pointerdown', function (ev) { sy = ev.clientY; grab.setPointerCapture(ev.pointerId); });
    grab.addEventListener('pointerup', function (ev) {
      if (sy === null) return;
      var dy = ev.clientY - sy; sy = null;
      if (dy < -40) setDetent(di + 1); else if (dy > 40) setDetent(di - 1);
    });
  }

  function wirePanel() {
    wireGrab();
    var q = $('#q');
    if (q) {
      q.addEventListener('input', function () {
        state.q = q.value.trim();
        q.parentElement.classList.toggle('has-text', !!state.q);
        renderList(true);
      });
      $('#clearQ').addEventListener('click', function () {
        q.value = ''; state.q = '';
        q.parentElement.classList.remove('has-text');
        renderList(true); q.focus();
      });
    }
    wireNear();
  }

  function showError() {
    $('#plist').innerHTML = '<div class="notice-row alarm"><div class="big">The listings did not load</div>' +
      '<p>Check your connection and reload.</p>' +
      '<button class="btn primary" type="button" onclick="location.reload()">Reload</button></div>';
    $('#count').textContent = 'Offline';
  }

  /* ----------------------------------------------------------------- boot */

  function boot() {
    PANEL_SHELL = $('#panel').innerHTML;
    state.monthProducts = inSeasonProducts();

    fetch('data/listings.json', { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (json) {
        state.data = json.filter(function (l) { return l.lat && l.lng && l.status !== 'retired'; });
        initMap();
        buildSeason();
        buildFilters();
        wirePanel();
        renderList(false);
        fitTo(state.data, 11);
        window.addEventListener('resize', function () { if (!state.active) fitTo(filtered()); });

        var id = new URLSearchParams(location.search).get('id');
        if (id) openDetail(id);
      })
      .catch(showError);
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
