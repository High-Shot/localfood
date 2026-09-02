/* Gulf Coast Farm: Mobile + Baldwin County.
   The board. Plain JS, Leaflet, one JSON file, no build step. */
(function () {
  'use strict';

  var CATS = [
    ['beef', 'Beef'], ['pork', 'Pork'], ['chicken', 'Chicken'], ['lamb', 'Lamb'], ['eggs', 'Eggs'], ['dairy', 'Dairy'],
    ['honey', 'Honey'], ['seafood', 'Seafood'], ['vegetables', 'Vegetables'], ['fruit', 'Fruit'], ['berries', 'Berries'],
    ['citrus', 'Satsumas & citrus'], ['nuts', 'Pecans & peanuts'], ['upick', 'U-pick'], ['flowers', 'Flowers'],
    ['baked', 'Baked goods'], ['pantry', 'Jams, sauces & pantry'], ['plants', 'Plants']
  ];
  var TYPES = [['farm', 'Farms'], ['market', 'Markets'], ['seafood', 'Seafood'], ['store', 'Farm stores']];
  var TYPE_LABEL = { farm: 'Farm', market: 'Farmers market', seafood: 'Seafood', store: 'Farm store' };
  // Four-letter service codes. These replace coloured dots on rows and pins.
  var TYPE_CODE = { farm: 'FARM', market: 'MKT', seafood: 'SEA', store: 'STOR' };
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

  var state = {
    q: '', county: 'all', type: null, cats: [], season: null, near: null,
    hidePending: false, active: null, data: [], monthProducts: [], lastIds: ''
  };
  var map, markers = {}, hereMarker = null, catsOpen = false;

  // Below 1040px the map is hidden behind the Board/Map switch. Leaflet reports
  // a zero-size container then, and flyTo/fitBounds produce NaN LatLngs that
  // throw and abort whatever called them.
  function mapReady() {
    if (!map) return false;
    var el = map.getContainer();
    if (!el.offsetParent && el.style.position !== 'fixed') return false;
    var size = map.getSize();
    return size.x > 0 && size.y > 0;
  }

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

  /* --------------------------------------------------------------- filters */

  function haversine(a, b, c, d) {
    var R = 3958.8, toR = function (x) { return (x * Math.PI) / 180; };
    var dLat = toR(c - a), dLng = toR(d - b);
    var h = Math.pow(Math.sin(dLat / 2), 2) +
            Math.cos(toR(a)) * Math.cos(toR(c)) * Math.pow(Math.sin(dLng / 2), 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  function matches(l) {
    if (state.county !== 'all' && l.county !== state.county) return false;
    if (state.type && l.type !== state.type) return false;
    if (state.hidePending && l.status !== 'live') return false;
    for (var i = 0; i < state.cats.length; i++) {
      if (l.categories.indexOf(state.cats[i]) === -1) return false;
    }
    if (state.season && l.products.indexOf(state.season) === -1) return false;
    if (state.q) {
      var hay = [l.name, l.city, l.description, l.products.join(' '),
                 l.categories.join(' '), TYPE_LABEL[l.type]].join(' ').toLowerCase();
      var words = state.q.toLowerCase().split(/\s+/);
      for (var w = 0; w < words.length; w++) {
        if (words[w] && hay.indexOf(words[w]) === -1) return false;
      }
    }
    return true;
  }

  // Rows are ranked by whether you can actually go: something ready this month
  // first, then confirmed listings, then alphabetical. Distance wins when the
  // visitor has shared a location.
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

  function catLabel(c) {
    for (var i = 0; i < CATS.length; i++) if (CATS[i][0] === c) return CATS[i][1];
    return c;
  }

  /* ------------------------------------------------------------- the flip */
  /* One authored moment: when the board changes, the letters change with it. */

  var GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&-.';
  var flipQueue = [], flipRunning = false;

  function queueFlip(el, text, order) {
    if (reduceMotion || order > 13) { el.textContent = text; return; }
    flipQueue.push({ el: el, text: text, start: order * 20, done: false });
  }

  function runFlips() {
    if (!flipQueue.length || flipRunning) { flipQueue.length = 0; return; }
    flipRunning = true;
    var t0 = performance.now(), CHAR_MS = 18;
    function frame(now) {
      var t = now - t0, active = false, i, f, out, settled, c;
      for (i = 0; i < flipQueue.length; i++) {
        f = flipQueue[i];
        if (f.done) continue;
        var local = t - f.start;
        if (local < 0) { active = true; continue; }
        settled = Math.floor(local / CHAR_MS);
        if (settled >= f.text.length) {
          f.el.textContent = f.text;
          f.el.classList.remove('flipping');
          f.done = true;
          continue;
        }
        active = true;
        f.el.classList.add('flipping');
        out = f.text.slice(0, settled);
        for (c = settled; c < f.text.length; c++) {
          out += f.text.charAt(c) === ' ' ? ' ' : GLYPHS.charAt((Math.random() * GLYPHS.length) | 0);
        }
        f.el.textContent = out;
      }
      if (active) { requestAnimationFrame(frame); }
      else { flipQueue.length = 0; flipRunning = false; }
    }
    requestAnimationFrame(frame);
  }

  /* ---------------------------------------------------------------- render */

  function rowMarkup(l, i) {
    var ready = l._ready || readyAt(l);
    var readyText = ready.length
      ? ready.join(', ')
      : (l.categories.slice(0, 3).map(catLabel).join(', ') || 'Not listed');
    var hours = l.hours ? l.hours : 'Call ahead';
    var dist = (state.near && l._d != null) ? l._d.toFixed(1) : '\u2014';
    return '<li>' +
      '<button class="row ' + (l.status !== 'live' ? 'unconfirmed ' : '') +
        (state.active === l.id ? 'is-active' : '') + '" data-id="' + esc(l.id) + '" data-i="' + i + '">' +
        '<span class="code">' + TYPE_CODE[l.type] + '</span>' +
        '<span class="place"><span class="name dest" data-flip="1">' + esc(l.name) + '</span>' +
          (l.status !== 'live' ? '<span class="tag-unconfirmed">Unconfirmed</span>' : '') + '</span>' +
        '<span class="town"><span class="clip">' + esc(l.city) + '</span></span>' +
        '<span class="ready' + (ready.length ? '' : ' none') + '"><span class="clip">' + esc(readyText) + '</span></span>' +
        '<span class="when' + (l.hours ? '' : ' callahead') + '"><span class="clip">' + esc(hours) + '</span></span>' +
        '<span class="dist' + (state.near && l._d != null ? ' has' : '') + '">' + dist + '</span>' +
      '</button></li>';
  }

  function renderBoard() {
    var rows = filtered();
    var pendingN = state.data.filter(function (l) { return l.status !== 'live'; }).length;
    var rowsEl = $('#rows'), tally = $('#tally');

    $('#cols').hidden = false;
    $('#hideWrap').hidden = false;
    $('#hideLabel').textContent = 'Hide ' + pendingN + ' unconfirmed';
    $('#mapCount').textContent = rows.length + ' shown';

    var tallyText = rows.length === state.data.length
      ? state.data.length + ' places on the board'
      : rows.length + ' of ' + state.data.length + ' places';
    tally.innerHTML = '<em>' + rows.length + '</em> ' +
      (rows.length === state.data.length ? 'places on the board' : 'of ' + state.data.length + ' places');
    tally.setAttribute('aria-label', tallyText);

    rowsEl.className = 'rows';
    if (!rows.length) {
      rowsEl.innerHTML = '<li class="notice-row"><div class="big">No services match</div>' +
        '<p>Nothing on the board fits those filters right now.</p>' +
        '<button class="btn primary" id="resetAll" type="button">Clear filters</button>' +
        '<p style="margin-top:14px">Or <a href="submit.html">add a place we are missing</a>.</p></li>';
      $('#resetAll').addEventListener('click', resetAll);
      syncMarkers(rows);
      return;
    }

    var html = '', i;
    for (i = 0; i < rows.length; i++) html += rowMarkup(rows[i], i);
    rowsEl.innerHTML = html;

    // Flip the destinations only when the visible set actually changed.
    var ids = rows.map(function (l) { return l.id; }).join(',');
    if (ids !== state.lastIds) {
      var names = rowsEl.querySelectorAll('[data-flip]');
      for (i = 0; i < names.length && i < 14; i++) {
        queueFlip(names[i], names[i].textContent, i);
      }
      runFlips();
      state.lastIds = ids;
    }

    var buttons = rowsEl.querySelectorAll('.row');
    for (i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener('click', function () { openDetail(this.dataset.id); });
    }
    syncMarkers(rows);
  }

  function syncMarkers(rows) {
    if (!map) return;
    var visible = {}, id;
    rows.forEach(function (l) { visible[l.id] = 1; });
    for (id in markers) {
      var on = !!visible[id];
      if (on && !map.hasLayer(markers[id])) markers[id].addTo(map);
      if (!on && map.hasLayer(markers[id])) map.removeLayer(markers[id]);
    }
    var filtersOn = state.q || state.cats.length || state.type || state.season || state.county !== 'all';
    if (rows.length && filtersOn && mapReady()) {
      map.fitBounds(L.latLngBounds(rows.map(function (l) { return [l.lat, l.lng]; })).pad(0.15), { maxZoom: 12 });
    }
  }

  function link(label, href, primary) {
    return href ? '<a class="btn ' + (primary ? 'primary' : '') + '" href="' + esc(href) +
      '" target="_blank" rel="noopener">' + label + '</a>' : '';
  }

  function cell(label, value, amber) {
    if (!value) return '';
    return '<div><dt class="lbl">' + label + '</dt><dd' + (amber ? ' class="amber"' : '') + '>' + esc(value) + '</dd></div>';
  }

  function openDetail(id) {
    var l = null, i;
    for (i = 0; i < state.data.length; i++) if (state.data[i].id === id) l = state.data[i];
    if (!l) return;
    state.active = id;
    // On phones the season strip and filter rail are dead weight over an open
    // detail; they push the listing name below the fold.
    $('#app').classList.add('detail-open');
    history.replaceState(null, '', '?id=' + encodeURIComponent(id));

    for (var k in markers) {
      var el = markers[k].getElement();
      if (el && el.firstChild) el.firstChild.classList.toggle('active', k === id);
    }
    if (mapReady()) {
      map.flyTo([l.lat, l.lng], Math.max(map.getZoom(), 13), { duration: reduceMotion ? 0 : 0.6 });
    }

    var exact = l.pin_precision === 'exact' && l.address;
    var addr = exact ? (l.address + ', ' + l.city + ', AL ' + l.zip) : (l.city + ', AL');
    var dirs = exact ? 'https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(addr) : null;
    var ready = readyAt(l);
    var offers = l.products.length ? l.products.join(', ') : l.categories.map(catLabel).join(', ');

    var board = $('#board');
    board.innerHTML = '<div class="detail">' +
      '<button class="back" id="back" type="button">&larr; Back to the board</button>' +
      '<h2>' + esc(l.name) + '</h2>' +
      '<div class="sub"><span class="code">' + TYPE_CODE[l.type] + '</span>' +
        esc(TYPE_LABEL[l.type]) + ' in ' + esc(l.city) + ', ' + esc(l.county) + ' County' +
        (l.status !== 'live' ? '<span class="tag-unconfirmed">Unconfirmed</span>' : '') + '</div>' +
      (l.status !== 'live'
        ? '<div class="notice"><b>Unconfirmed</b>We have not confirmed this listing is current. Call or check their page before you drive out.</div>'
        : '') +
      (ready.length
        ? '<div class="notice"><b>Ready this month</b>' + esc(ready.join(', ')) + '</div>'
        : '') +
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
      '<p><a href="submit.html?id=' + encodeURIComponent(l.id) + '&mode=update">Own this listing or see an error? Send an update.</a></p>' +
      '<p class="fine">Source: ' + esc(l.source) + '. Last checked ' + esc(l.last_verified) +
      '. Hours and availability change with the season; confirm before you go. ' +
      '<a href="l/' + esc(l.id) + '/">Permanent link</a></p>' +
      '</div>';

    $('#back').addEventListener('click', backToBoard);
    board.scrollTop = 0;
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
  }

  function backToBoard() {
    state.active = null;
    state.lastIds = '';
    $('#app').classList.remove('detail-open');
    history.replaceState(null, '', location.pathname);
    for (var k in markers) {
      var el = markers[k].getElement();
      if (el && el.firstChild) el.firstChild.classList.remove('active');
    }
    $('#board').innerHTML = BOARD_SHELL;
    wireBoardShell();
    renderBoard();
  }

  var BOARD_SHELL = '';

  function wireBoardShell() {
    $('#hidePending').addEventListener('change', function () {
      state.hidePending = this.checked;
      state.lastIds = '';
      renderBoard();
    });
    $('#hidePending').checked = state.hidePending;
  }

  function update() {
    if (state.active) backToBoard(); else renderBoard();
  }

  function resetAll() {
    state.q = ''; state.county = 'all'; state.type = null; state.cats = [];
    state.season = null; state.hidePending = false;
    $('#q').value = '';
    $('#q').parentElement.classList.remove('has-text');
    buildFilters();
    buildSeason();
    update();
  }

  /* --------------------------------------------------------------- chrome */

  function chip(label, attr, val, pressed, cls) {
    return '<button class="flapchip ' + (cls || '') + '" type="button" ' + attr + '="' + esc(val) +
      '" aria-pressed="' + (pressed ? 'true' : 'false') + '">' + esc(label) + '</button>';
  }

  function buildFilters() {
    var f = $('#filters'), html = '';
    [['all', 'Both counties'], ['Baldwin', 'Baldwin'], ['Mobile', 'Mobile']].forEach(function (p) {
      html += chip(p[1], 'data-county', p[0], state.county === p[0]);
    });
    html += '<span class="sep"></span>';
    TYPES.forEach(function (p) {
      html += chip(p[1], 'data-type', p[0], state.type === p[0]);
    });
    html += '<span class="sep"></span>';
    html += '<button class="flapchip" type="button" id="catToggle" aria-expanded="' + catsOpen + '" aria-controls="catFilters">' +
      'What they sell' + (state.cats.length ? ' (' + state.cats.length + ')' : '') +
      ' ' + (catsOpen ? '\u25B4' : '\u25BE') + '</button>';
    f.innerHTML = html;

    f.querySelectorAll('[data-county]').forEach(function (b) {
      b.addEventListener('click', function () {
        state.county = b.dataset.county; buildFilters(); update();
      });
    });
    f.querySelectorAll('[data-type]').forEach(function (b) {
      b.addEventListener('click', function () {
        state.type = state.type === b.dataset.type ? null : b.dataset.type;
        buildFilters(); update();
      });
    });
    $('#catToggle').addEventListener('click', function () {
      catsOpen = !catsOpen;
      buildFilters();
      buildCats();
      if (catsOpen) $('#catFilters').querySelector('button').focus();
    });
    if (state.cats.length) $('#catToggle').setAttribute('aria-pressed', 'true');
    buildCats();
  }

  function buildCats() {
    var c = $('#catFilters');
    c.hidden = !catsOpen;
    if (!catsOpen) { c.innerHTML = ''; return; }
    c.style.flexWrap = 'wrap';
    c.style.overflowX = 'visible';
    c.innerHTML = CATS.map(function (p) {
      return chip(p[1], 'data-cat', p[0], state.cats.indexOf(p[0]) > -1);
    }).join('');
    c.querySelectorAll('[data-cat]').forEach(function (b) {
      b.addEventListener('click', function () {
        var v = b.dataset.cat, i = state.cats.indexOf(v);
        if (i > -1) state.cats.splice(i, 1); else state.cats.push(v);
        buildFilters(); update();
      });
    });
  }

  function buildSeason() {
    var now = new Date();
    $('#seasonMonth').textContent = MONTHS[now.getMonth()];
    var have = state.monthProducts.filter(function (p) {
      return state.data.some(function (l) { return l.products.indexOf(p) > -1; });
    });
    var flaps = $('#seasonFlaps');
    if (!have.length) {
      flaps.innerHTML = '';
      $('#seasonNote').innerHTML = 'Free and community built. Every farm, market, and seafood dock we can find in Mobile and Baldwin County.';
      return;
    }
    $('#seasonNote').innerHTML = '<strong>Ready right now.</strong> Tap one to filter the board.';
    flaps.innerHTML = have.map(function (p) {
      return chip(p, 'data-season', p, state.season === p);
    }).join('');
    flaps.querySelectorAll('[data-season]').forEach(function (b) {
      b.addEventListener('click', function () {
        state.season = state.season === b.dataset.season ? null : b.dataset.season;
        buildSeason(); update();
      });
    });
  }

  /* ------------------------------------------------------------------ map */

  function initMap() {
    map = L.map('map', { zoomControl: true, attributionControl: true }).setView([30.62, -87.95], 9);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    // 81 code tiles fuse into one mass when zoomed out; thin them to markers.
    function densityClass() {
      map.getContainer().classList.toggle('lowzoom', map.getZoom() < 11);
    }
    map.on('zoomend', densityClass);
    densityClass();

    state.data.forEach(function (l) {
      var cls = 'pin' + (l.status !== 'live' ? ' unconfirmed' : '') + (l.pin_precision !== 'exact' ? ' town' : '');
      var icon = L.divIcon({
        className: '',
        html: '<div class="' + cls + '">' + TYPE_CODE[l.type] + '</div>',
        iconSize: [30, 18], iconAnchor: [15, 9]
      });
      var m = L.marker([l.lat, l.lng], { icon: icon, title: l.name });
      m.bindPopup('<b>' + esc(l.name) + '</b>' + esc(TYPE_LABEL[l.type]) + ' &middot; ' + esc(l.city));
      m.on('click', function () { openDetail(l.id); });
      markers[l.id] = m;
    });
  }

  function wireViewSwitch() {
    var app = $('#app'), listBtn = $('#viewList'), mapBtn = $('#viewMap');
    function set(showMap) {
      app.classList.toggle('show-map', showMap);
      listBtn.setAttribute('aria-pressed', String(!showMap));
      mapBtn.setAttribute('aria-pressed', String(showMap));
      if (showMap && map) {
        setTimeout(function () {
          map.invalidateSize();
          var l = null, i;
          for (i = 0; i < state.data.length; i++) if (state.data[i].id === state.active) l = state.data[i];
          if (l) { map.setView([l.lat, l.lng], Math.max(map.getZoom(), 13)); return; }
          var rows = filtered();
          if (rows.length) {
            map.fitBounds(L.latLngBounds(rows.map(function (r) { return [r.lat, r.lng]; })).pad(0.15), { maxZoom: 12 });
          }
        }, 40);
      }
    }
    listBtn.addEventListener('click', function () { set(false); });
    mapBtn.addEventListener('click', function () { set(true); });
  }

  function wireNear() {
    var btn = $('#nearBtn');
    btn.addEventListener('click', function () {
      if (state.near) {
        state.near = null;
        btn.setAttribute('aria-pressed', 'false');
        if (hereMarker) { map.removeLayer(hereMarker); hereMarker = null; }
        state.lastIds = '';
        update();
        return;
      }
      if (!navigator.geolocation) {
        btn.disabled = true;
        btn.lastChild.textContent = 'No location';
        return;
      }
      btn.classList.add('locating');
      navigator.geolocation.getCurrentPosition(function (p) {
        state.near = [p.coords.latitude, p.coords.longitude];
        btn.classList.remove('locating');
        btn.setAttribute('aria-pressed', 'true');
        hereMarker = L.circleMarker(state.near, {
          radius: 7, color: '#ffb000', fillColor: '#ffb000', fillOpacity: 0.9, weight: 2
        }).addTo(map).bindPopup('You are here');
        if (mapReady()) map.setView(state.near, 11);
        state.lastIds = '';
        update();
      }, function () {
        btn.classList.remove('locating');
        btn.lastChild.textContent = 'Location blocked';
        setTimeout(function () { btn.lastChild.textContent = 'Near me'; }, 3000);
      }, { timeout: 8000 });
    });
  }

  function showError() {
    $('#cols').hidden = true;
    $('#tally').textContent = 'Board offline';
    $('#rows').className = 'rows';
    $('#rows').innerHTML = '<li class="notice-row alarm"><div class="big">The board did not load</div>' +
      '<p>The listing data could not be fetched. Check your connection and reload.</p>' +
      '<button class="btn primary" type="button" onclick="location.reload()">Reload</button></li>';
  }

  /* ----------------------------------------------------------------- boot */

  function boot() {
    BOARD_SHELL = $('#board').innerHTML;
    state.monthProducts = inSeasonProducts();

    fetch('data/listings.json', { cache: 'no-cache' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (json) {
        state.data = json.filter(function (l) { return l.lat && l.lng && l.status !== 'retired'; });
        initMap();
        buildSeason();
        buildFilters();
        wireBoardShell();
        wireViewSwitch();
        wireNear();

        var q = $('#q');
        q.addEventListener('input', function () {
          state.q = q.value.trim();
          q.parentElement.classList.toggle('has-text', !!state.q);
          update();
        });
        $('#clearQ').addEventListener('click', function () {
          q.value = ''; state.q = '';
          q.parentElement.classList.remove('has-text');
          update(); q.focus();
        });

        if (mapReady()) {
          map.fitBounds(L.latLngBounds(state.data.map(function (l) { return [l.lat, l.lng]; })).pad(0.05));
        }
        renderBoard();

        var id = new URLSearchParams(location.search).get('id');
        if (id) openDetail(id);
      })
      .catch(showError);
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
