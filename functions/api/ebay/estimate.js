const MARKETPLACE = 'https://www.ebay.com';
const DAY = 86400;
const normalize = value => String(value || '').normalize('NFKD').replace(/\p{M}/gu, '')
  .toLowerCase().match(/[a-z0-9]+/g) || [];

function json(data, status = 200, maxAge = 0) {
  return Response.json(data, {
    status,
    headers: {'Cache-Control': maxAge ? 'public, max-age='+maxAge : 'no-store'},
  });
}

export function estimateRows(rows, terms, sold) {
  const prices = new Map();
  for (const row of rows) {
    if (!row.id || prices.has(row.id) || (sold && !/\bsold\b/i.test(row.marker))) continue;
    const words = new Set(normalize(row.title));
    if (!terms.every(term => words.has(term))) continue;
    if (/\b(?:lot of|custom|reproduction|bootleg|pre[- ]?order|box only|parts only|accessories only)\b/i.test(row.title)) continue;
    const amount = /^\$([\d,]+\.\d{2})$/.exec(row.price.trim());
    if (!amount) continue;
    const price = Number(amount[1].replaceAll(',', ''));
    if (price > 0 && price <= 100000) prices.set(row.id, price);
  }
  const values = [...prices.values()].sort((a,b) => a-b);
  const mid = Math.floor(values.length/2);
  if (values.length < 2) return null;
  return {
    amount: Math.round((values.length%2 ? values[mid] : (values[mid-1]+values[mid])/2)*100)/100,
    sampleSize: values.length,
    basis: sold ? 'sold' : 'asking',
  };
}

async function searchPage(query, sold) {
  const url = new URL('/sch/i.html', MARKETPLACE);
  url.search = new URLSearchParams({_nkw:query});
  if (sold) {
    url.searchParams.set('LH_Sold','1');
    url.searchParams.set('LH_Complete','1');
  } else {
    url.searchParams.set('LH_BIN','1');
  }
  const response = await fetch(url, {redirect:'error',signal:AbortSignal.timeout(6500)});
  if (!response.ok) throw Error('eBay search is unavailable.');
  const rows = [];
  let title = '';
  const capture = key => ({text(chunk) {
    if (rows.length && rows.length <= 80) rows.at(-1)[key] += chunk.text;
  }});
  const transformed = new HTMLRewriter()
    .on('title', {text(chunk){title += chunk.text;}})
    .on('.s-card, .s-item', {element(){rows.push({title:'',price:'',marker:'',id:''});}})
    .on('.s-card__title, .s-item__title',capture('title'))
    .on('.s-card__price, .s-item__price',capture('price'))
    .on('.s-card__caption, .s-item__title--tagblock',capture('marker'))
    .on('.s-card__link, .s-item__link', {element(el){
      const match = /^https:\/\/www\.ebay\.com\/itm\/(?:[^/?]+\/)?(\d+)(?:[/?]|$)/.exec(el.getAttribute('href')||'');
      if (match && rows.length) rows.at(-1).id = match[1];
    }})
    .transform(response);
  // Drain the response so the rewriter can emit every matching card.
  await transformed.body.pipeTo(new WritableStream());
  if (/security measure|verify.*human|pardon our interruption/i.test(title)) throw Error('eBay verification required.');
  return rows.slice(0,80);
}

export function listingResults(rows, terms) {
  const results = new Map();
  for (const row of rows) {
    const title = row.title.trim();
    const words = new Set(normalize(title));
    if (!row.id || !title || !terms.every(term => words.has(term))) continue;
    const match = /^\$([\d,]+\.\d{2})$/.exec(row.price.trim());
    const price = match ? Number(match[1].replaceAll(',', '')) : null;
    results.set(row.id, {id: row.id, title, askingPrice: price > 0 && price <= 100000 ? price : null});
  }
  return [...results.values()].slice(0, 20);
}

export async function onRequestGet({request,env,waitUntil}) {
  const url = new URL(request.url);
  const name = (url.searchParams.get('name') || '').trim();
  const edition = (url.searchParams.get('edition') || '').trim();
  const query = [name,edition].filter(Boolean).join(' ');
  const terms = [...new Set(normalize(query))];
  const lookup = url.searchParams.get('mode') === 'lookup';
  if (lookup && (query.length > 140 || !terms.length || terms.length > 14)) return json({results:[]});
  if (!lookup && (query.length > 140 || !name || terms.length < 2 || terms.length > 14)) return json({quote:null});
  const key = new URL(url.origin+'/api/ebay/estimate');
  key.searchParams.set('q',terms.join(' '));
  if (lookup) key.searchParams.set('mode','lookup');
  key.searchParams.set('sold',env.EBAY_WEBSITE_SOLD_ENABLED === 'true' ? '1' : '0');
  const cache = globalThis.caches?.default;
  const hit = await cache?.match(key.href).catch(()=>null);
  if (hit) return hit;
  try {
    if (lookup) {
      const result = json({results:listingResults(await searchPage(query,false),terms)},200,DAY);
      if (cache) waitUntil(cache.put(key.href,result.clone()).catch(()=>{}));
      return result;
    }
    let quote;
    if (env.EBAY_WEBSITE_SOLD_ENABLED === 'true') {
      quote = estimateRows(await searchPage(query,true),terms,true);
    }
    if (!quote) quote = estimateRows(await searchPage(query,false),terms,false);
    const result = json({quote:quote ? {...quote, checkedAt:new Date().toISOString()} : null},200,DAY);
    if (cache) waitUntil(cache.put(key.href,result.clone()).catch(()=>{}));
    return result;
  } catch {
    return json({error:lookup?'eBay website lookup is temporarily unavailable.':'eBay pricing is temporarily unavailable.'},503);
  }
}
