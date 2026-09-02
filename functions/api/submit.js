// POST /api/submit  ->  creates a row in the Airtable "Submissions" table.
// Env vars (set in Cloudflare Pages > Settings > Environment variables):
//   AIRTABLE_TOKEN  personal access token with data.records:write on the base
//   AIRTABLE_BASE   base id, starts with "app"
//   AIRTABLE_TABLE  table name, default "Submissions"
//   NOTIFY_EMAIL    optional; if set with RESEND_API_KEY, emails you on each submission

const MAX = { name: 120, description: 1200, notes: 2000, default: 300 };

export async function onRequestPost({ request, env }) {
  let body;
  try { body = await request.json(); } catch { return text('Bad request', 400); }

  if (body.company_website) return text('ok', 200); // honeypot filled: pretend success, drop it
  if (!body.contact_email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(body.contact_email)) return text('A valid contact email is required', 400);
  if (body.mode !== 'remove' && !body.name) return text('Name is required', 400);

  const s = (k) => String(body[k] || '').slice(0, MAX[k] || MAX.default);
  const fields = {
    Mode: body.mode || 'new',
    'Listing ID': s('listing_id'),
    Name: s('name'),
    Type: s('type'),
    Description: s('description'),
    Categories: Array.isArray(body.categories) ? body.categories.join(', ') : '',
    Products: Array.isArray(body.products) ? body.products.join(', ').slice(0, 600) : '',
    'How to buy': Array.isArray(body.how_to_buy) ? body.how_to_buy.join(', ') : '',
    'Sells at': s('sells_at'),
    Hours: s('hours'),
    Address: s('address'),
    City: s('city'),
    County: s('county'),
    'Pin precision': s('pin_precision') || 'exact',
    Phone: s('phone'),
    Email: s('email'),
    Website: s('website'),
    Facebook: s('facebook'),
    Instagram: s('instagram'),
    TikTok: s('tiktok'),
    'Contact name': s('contact_name'),
    'Contact email': s('contact_email'),
    Notes: s('notes'),
    Consent: body.consent === 'on',
    Status: 'pending',
    'Submitted at': new Date().toISOString(),
    IP: request.headers.get('cf-connecting-ip') || '',
  };

  const table = encodeURIComponent(env.AIRTABLE_TABLE || 'Submissions');
  const r = await fetch(`https://api.airtable.com/v0/${env.AIRTABLE_BASE}/${table}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${env.AIRTABLE_TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ records: [{ fields }], typecast: true }),
  });
  if (!r.ok) return text('Could not save submission: ' + (await r.text()).slice(0, 300), 502);

  if (env.NOTIFY_EMAIL && env.RESEND_API_KEY) {
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: 'Gulf Coast Farm <noreply@' + new URL(request.url).hostname + '>', to: env.NOTIFY_EMAIL, subject: `[Gulf Coast Farm] ${fields.Mode}: ${fields.Name || fields['Listing ID']}`, text: JSON.stringify(fields, null, 2) }),
    }).catch(() => {});
  }
  return text('ok', 200);
}

const text = (msg, status) => new Response(msg, { status, headers: { 'Content-Type': 'text/plain', 'Access-Control-Allow-Origin': '*' } });
