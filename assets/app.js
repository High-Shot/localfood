/* Gulf Coast Farm: Mobile + Baldwin County. Plain JS, Leaflet, one JSON file. */
(function () {
  'use strict';

  const CATS = [
    ['beef', 'Beef'], ['pork', 'Pork'], ['chicken', 'Chicken'], ['lamb', 'Lamb'], ['eggs', 'Eggs'], ['dairy', 'Dairy'],
    ['honey', 'Honey'], ['seafood', 'Seafood'], ['vegetables', 'Vegetables'], ['fruit', 'Fruit'], ['berries', 'Berries'],
    ['citrus', 'Satsumas & citrus'], ['nuts', 'Pecans & peanuts'], ['upick', 'U-pick'], ['flowers', 'Flowers'],
    ['baked', 'Baked goods'], ['pantry', 'Jams, sauces & pantry'], ['plants', 'Plants']
  ];
  const TYPES = [['farm', 'Farms'], ['market', 'Farmers markets'], ['seafood', 'Seafood'], ['store', 'Farm stores']];
  const TYPE_LABEL = { farm: 'Farm', market: 'Farmers market', seafood: 'Seafood', store: 'Farm store' };

  // Gulf Coast harvest windows by month number (1 = Jan). Estimates; edit in one place.
  const SEASON = {
    'Strawberries': [3, 4, 5], 'Blueberries': [5, 6, 7], 'Blackberries': [5, 6], 'Peaches': [5, 6], 'Plums': [5, 6],
    'Satsumas': [10, 11, 12], 'Pecans': [10, 11, 12, 1], 'Muscadine Grapes': [8, 9], 'Sweet Corn': [6, 7],
    'Tomatoes': [5, 6, 7, 10, 11], 'Watermelon': [6, 7, 8], 'Cantaloupe': [6, 7], 'Pumpkins': [10], 'Pumpkin Patch': [10],
    'Peas': [6, 7, 8], 'Okra': [6, 7, 8, 9], 'Squash': [5, 6, 7, 10], 'Cucumbers': [5, 6, 7], 'Greens': [10, 11, 12, 1, 2, 3],
    'Sweet Potatoes': [9, 10, 11, 12], 'Peppers': [6, 7, 8, 9, 10], 'Pears': [8, 9], 'Fresh Cut Flowers': [4, 5, 6, 7, 8, 9, 10],
    'Saltwater Shrimp': [6, 7, 8, 9, 10, 11, 12], 'Oysters': [10, 11, 12, 1, 2, 3], 'Lettuce': [10, 11, 12, 1, 2, 3, 4],
    'Roasted/Boiled Peanuts': [7, 8, 9, 10]
  };

  const $ = (s, el) => (el || document).querySelector(s);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const state = { q: '', county: 'all', type: null, cats: new Set(), season: null, near: null, hidePending: false, active: null, data: [] };
  let map, markers = {};

  function inSeasonProducts() {
    const m = new Date().getMonth() + 1;
    return Object.keys(SEASON).filter((p) => SEASON[p].includes(m));
  }

  function haversine(a, b, c, d) {
    const R = 3958.8, toR = (x) => (x * Math.PI) / 180;
    const dLat = toR(c - a), dLng = toR(d - b);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(toR(a)) * Math.cos(toR(c)) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  function matches(l) {
    if (state.county !== 'all' && l.county !== state.county) return false;
    if (state.type && l.type !== state.type) return false;
    if (state.hidePending && l.status !== 'live') return false;
    for (const c of state.cats) if (!l.categories.includes(c)) return false;
    if (state.season && !l.products.includes(state.season)) return false;
    if (state.q) {
      const hay = [l.name, l.city, l.description, l.products.join(' '), l.categories.join(' '), TYPE_LABEL[l.type]].join(' ').toLowerCase();
      for (const w of state.q.toLowerCase().split(/\s+/).filter(Boolean)) if (!hay.includes(w)) return false;
    }
    return true;
  }

  function filtered() {
    let out = state.data.filter(matches);
    if (state.near) {
      out.forEach((l) => (l._d = haversine(state.near[0], state.near[1], l.lat, l.lng)));
      out.sort((a, b) => a._d - b._d);
    } else {
      out.sort((a, b) => (a.status === b.status ? a.name.localeCompare(b.name) : a.status === 'live' ? -1 : 1));
    }
    return out;
  }

  function catLabel(c) { const f = CATS.find((x) => x[0] === c); return f ? f[1] : c; }

  function renderList() {
    const rows = filtered();
    const el = $('#results');
    el.classList.remove('showing-detail');
    const pendingN = state.data.filter((l) => l.status !== 'live').length;
    let html = `<div class="count"><span>${rows.length} of ${state.data.length} places</span>
      <label><input type="checkbox" id="hidePending" ${state.hidePending ? 'checked' : ''}> hide ${pendingN} unverified</label></div>`;
    if (!rows.length) {
      html += `<div class="empty">Nothing matches. Clear a filter, or <a href="submit.html">add a farm we're missing</a>.</div>`;
    }
    for (const l of rows) {
      html += `<button class="card ${state.active === l.id ? 'active' : ''}" data-id="${l.id}">
        <div class="name"><span class="dot ${l.type}"></span>${esc(l.name)}${l.status !== 'live' ? ' <span class="pendingtag">unverified</span>' : ''}</div>
        <div class="meta">${esc(TYPE_LABEL[l.type])} &middot; ${esc(l.city)}, ${esc(l.county)} County${l._d != null && state.near ? ` &middot; <span class="dist">${l._d.toFixed(1)} mi</span>` : ''}</div>
        <div class="tags">${l.categories.slice(0, 6).map((c) => `<span class="tag">${esc(catLabel(c))}</span>`).join('')}</div>
      </button>`;
    }
    el.innerHTML = html;
    $('#hidePending').addEventListener('change', (e) => { state.hidePending = e.target.checked; update(); });
    el.querySelectorAll('.card').forEach((b) => b.addEventListener('click', () => openDetail(b.dataset.id)));
    // map markers
    const visible = new Set(rows.map((l) => l.id));
    for (const id in markers) {
      const on = visible.has(id);
      if (on && !map.hasLayer(markers[id])) markers[id].addTo(map);
      if (!on && map.hasLayer(markers[id])) map.removeLayer(markers[id]);
    }
    if (rows.length && (state.q || state.cats.size || state.type || state.season || state.county !== 'all')) {
      const b = L.latLngBounds(rows.map((l) => [l.lat, l.lng]));
      map.fitBounds(b.pad(0.15), { maxZoom: 12 });
    }
  }

  function link(label, href, primary) {
    return href ? `<a class="btn ${primary ? 'primary' : ''}" href="${esc(href)}" target="_blank" rel="noopener">${label}</a>` : '';
  }

  function openDetail(id) {
    const l = state.data.find((x) => x.id === id);
    if (!l) return;
    state.active = id;
    history.replaceState(null, '', '?id=' + encodeURIComponent(id));
    for (const k in markers) markers[k].getElement()?.classList.toggle('active', k === id);
    const mobile = window.innerWidth < 900;
    map.once('moveend', () => { if (mobile) map.panBy([0, Math.round(map.getSize().y * 0.3)], { animate: true }); });
    map.flyTo([l.lat, l.lng], Math.max(map.getZoom(), 13), { duration: 0.6 });
    const el = $('#results');
    el.classList.add('showing-detail');
    const addr = l.pin_precision === 'exact' && l.address ? `${l.address}, ${l.city}, AL ${l.zip}` : `${l.city}, AL (exact location not published)`;
    const dirs = l.pin_precision === 'exact' ? `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(l.address ? addr : l.lat + ',' + l.lng)}` : null;
    el.innerHTML = `<div class="detail">
      <button class="back" id="back">&larr; All results</button>
      <h2>${esc(l.name)}</h2>
      <div class="kind"><span class="dot ${l.type}"></span>${esc(TYPE_LABEL[l.type])} in ${esc(l.city)}, ${esc(l.county)} County${l.status !== 'live' ? ' <span class="pendingtag">unverified</span>' : ''}</div>
      ${l.status !== 'live' ? `<div class="notice">We have not confirmed this listing is current. Call or check their page before you drive out.</div>` : ''}
      ${l.description ? `<p>${esc(l.description)}</p>` : ''}
      <div class="actions">
        ${link('Directions', dirs, true)}
        ${l.phone ? `<a class="btn" href="tel:${esc(l.phone.replace(/[^\d+]/g, ''))}">Call</a>` : ''}
        ${link('Website', l.website)}${link('Facebook', l.facebook)}${link('Instagram', l.instagram)}${link('TikTok', l.tiktok)}
        ${l.email ? `<a class="btn" href="mailto:${esc(l.email)}">Email</a>` : ''}
      </div>
      <dl>
        <dt>Offers</dt><dd>${esc(l.products.length ? l.products.join(', ') : l.categories.map(catLabel).join(', ') || 'Not listed')}</dd>
        ${l.hours ? `<dt>Hours</dt><dd>${esc(l.hours)}</dd>` : ''}
        ${l.how_to_buy.length ? `<dt>How to buy</dt><dd>${esc(l.how_to_buy.join(', '))}</dd>` : ''}
        ${l.sells_at ? `<dt>Sells at</dt><dd>${esc(l.sells_at)}</dd>` : ''}
        <dt>Address</dt><dd>${esc(addr)}</dd>
        ${l.phone ? `<dt>Phone</dt><dd>${esc(l.phone)}</dd>` : ''}
        ${l.certified_organic ? `<dt>Certified</dt><dd>USDA Organic</dd>` : ''}
      </dl>
      <p><a href="submit.html?id=${encodeURIComponent(l.id)}&mode=update">Own this listing or see an error? Send an update.</a></p>
      <p class="fine">Source: ${esc(l.source)}. Last checked ${esc(l.last_verified)}. Hours and availability change with the season; confirm before you go. <a href="l/${esc(l.id)}/">Share link</a></p>
    </div>`;
    $('#back').addEventListener('click', () => { state.active = null; history.replaceState(null, '', location.pathname); renderList(); });
    el.scrollTop = 0;
  }

  function update() { renderList(); }

  function buildChips() {
    const county = $('#countyChips');
    county.innerHTML = [['all', 'Both counties'], ['Baldwin', 'Baldwin'], ['Mobile', 'Mobile']].map(([v, t]) => `<button class="chip" data-county="${v}" aria-pressed="${state.county === v}">${t}</button>`).join('')
      + TYPES.map(([v, t]) => `<button class="chip" data-type="${v}" aria-pressed="false">${t}</button>`).join('')
      + `<button class="chip near" id="nearBtn" aria-pressed="false">Near me</button>`;
    county.querySelectorAll('[data-county]').forEach((b) => b.addEventListener('click', () => { state.county = b.dataset.county; county.querySelectorAll('[data-county]').forEach((x) => x.setAttribute('aria-pressed', x === b)); update(); }));
    county.querySelectorAll('[data-type]').forEach((b) => b.addEventListener('click', () => { const on = state.type !== b.dataset.type; state.type = on ? b.dataset.type : null; county.querySelectorAll('[data-type]').forEach((x) => x.setAttribute('aria-pressed', x === b && on)); update(); }));
    $('#nearBtn').addEventListener('click', () => {
      if (state.near) { state.near = null; $('#nearBtn').setAttribute('aria-pressed', 'false'); update(); return; }
      if (!navigator.geolocation) return alert('Location is not available on this device.');
      $('#nearBtn').textContent = 'Locating';
      navigator.geolocation.getCurrentPosition((p) => {
        state.near = [p.coords.latitude, p.coords.longitude];
        $('#nearBtn').textContent = 'Near me'; $('#nearBtn').setAttribute('aria-pressed', 'true');
        L.circleMarker(state.near, { radius: 7, color: '#3e7a96', fillColor: '#3e7a96', fillOpacity: 0.9 }).addTo(map).bindPopup('You are here');
        map.setView(state.near, 11); update();
      }, () => { $('#nearBtn').textContent = 'Near me'; alert('Could not get your location. Check your browser permission.'); }, { timeout: 8000 });
    });

    const cats = $('#catChips');
    cats.innerHTML = CATS.map(([v, t]) => `<button class="chip" data-cat="${v}" aria-pressed="false">${t}</button>`).join('');
    cats.querySelectorAll('[data-cat]').forEach((b) => b.addEventListener('click', () => { const v = b.dataset.cat; state.cats.has(v) ? state.cats.delete(v) : state.cats.add(v); b.setAttribute('aria-pressed', state.cats.has(v)); update(); }));

    const now = inSeasonProducts().filter((p) => state.data.some((l) => l.products.includes(p)));
    const season = $('#seasonChips');
    if (!now.length) { season.parentElement.hidden = true; return; }
    season.innerHTML = now.map((p) => `<button class="chip season" data-season="${esc(p)}" aria-pressed="false">${esc(p)}</button>`).join('');
    season.querySelectorAll('[data-season]').forEach((b) => b.addEventListener('click', () => { const on = state.season !== b.dataset.season; state.season = on ? b.dataset.season : null; season.querySelectorAll('[data-season]').forEach((x) => x.setAttribute('aria-pressed', x === b && on)); update(); }));
  }

  function initMap() {
    map = L.map('map', { zoomControl: true, attributionControl: true }).setView([30.62, -87.95], 9);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(map);
    for (const l of state.data) {
      const icon = L.divIcon({ className: '', html: `<div class="pin ${l.type} ${l.status !== 'live' ? 'pending' : ''} ${l.pin_precision !== 'exact' ? 'town' : ''}"></div>`, iconSize: [18, 18], iconAnchor: [9, 9] });
      const m = L.marker([l.lat, l.lng], { icon, title: l.name });
      m.bindPopup(`<b>${esc(l.name)}</b>${esc(TYPE_LABEL[l.type])} &middot; ${esc(l.city)}`);
      m.on('click', () => openDetail(l.id));
      markers[l.id] = m;
    }
  }

  async function boot() {
    const res = await fetch('data/listings.json', { cache: 'no-cache' });
    state.data = (await res.json()).filter((l) => l.lat && l.lng && l.status !== 'retired');
    initMap();
    buildChips();
    const q = $('#q');
    q.addEventListener('input', () => { state.q = q.value.trim(); q.parentElement.classList.toggle('has-text', !!state.q); update(); });
    $('#clearQ').addEventListener('click', () => { q.value = ''; state.q = ''; q.parentElement.classList.remove('has-text'); update(); q.focus(); });
    map.fitBounds(L.latLngBounds(state.data.map((l) => [l.lat, l.lng])).pad(0.05));
    renderList();
    const id = new URLSearchParams(location.search).get('id');
    if (id) openDetail(id);
  }
  document.addEventListener('DOMContentLoaded', boot);
})();
