const url = 'https://www.pricecharting.com/game/pokemon-base-set/pikachu-58';
const grades = {ungraded:'Ungraded', psa10:'PSA 10'};
const plain = html => html.replace(/<[^>]*>/g,' ').replace(/&nbsp;|&#160;/gi,' ').replace(/\s+/g,' ').trim();

export function parsePriceGuide(html) {
  const guide = /Full Price Guide:\s*Pikachu\s*#58\s*\(Pokemon Base Set\)/i.exec(plain(html));
  if (!guide) return {};
  const prices = {};
  // Prefer explicitly labeled rows, with a narrow fallback for provider layout changes.
  for (const [key,label] of Object.entries(grades)) {
    const match = new RegExp('(?:^|\\s)'+label+'\\s+\\$([0-9][0-9,]*\\.\\d{2})(?![0-9])')
      .exec(guide.input.slice(guide.index + guide[0].length, guide.index + guide[0].length + 1200));
    const amount = match ? Number(match[1].replaceAll(',','')) : 0;
    if (amount > 0 && amount < 1000000) prices[key] = amount;
  }
  return prices;
}

export async function onRequestGet({request,waitUntil}) {
  const id = new URL(request.url).searchParams.get('id');
  if (/^base1-\d{1,3}$/.test(id)) return baseSetQuote(request,id,waitUntil);
  if (id !== '630471') return Response.json({error:'Item not supported'}, {status:404});
  try {
    const response = await fetch(url,{redirect:'error',signal:AbortSignal.timeout(6000)});
    if (!response.ok || !response.headers.get('content-type')?.includes('text/html')) throw Error();
    const prices = parsePriceGuide(await response.text());
    if (!Object.keys(prices).length) throw Error();
    return Response.json({id:'630471',source:'PriceCharting',currency:'USD',checkedAt:new Date().toISOString(),prices},{
      headers:{'Cache-Control':'public, max-age=900'},
    });
  } catch {
    return Response.json({error:'PriceCharting quote unavailable'},{status:503});
  }
}

const baseSetUrl = 'https://www.pricecharting.com/console/pokemon-base-set?exclude-variants=true&view=table';

export function parseBaseSet(html) {
  const pricesByCard = new Map();
  const table = /<table\b[^>]*id="games_table"[^>]*>([\s\S]*?)<\/table>/i.exec(html)?.[1];
  if (!table || !/\bUngraded\b/i.test(plain(table.split('</thead>')[0])) ||
      !/\bPSA 10\b/i.test(plain(table.split('</thead>')[0]))) return pricesByCard;
  for (const [, row] of table.matchAll(/<tr\b[^>]*data-product="\d+"[^>]*>([\s\S]*?)<\/tr>/gi)) {
    const product = /<a href="(\/game\/pokemon-base-set\/[a-z0-9-]+)">([^<]+) #(\d{1,3})<\/a>/i.exec(row);
    if (!product || /[[\]]/.test(product[2])) continue;
    const name = product[2].replaceAll('&#39;',"'").replaceAll('&amp;','&').trim();
    const id = 'base1-'+product[3];
    if (pricesByCard.has(id)) {
      pricesByCard.set(id, null);
      continue;
    }
    const prices = {};
    for (const [grade, column] of [['ungraded','used_price'],['psa10','new_price']]) {
      const cell = new RegExp('<td class="[^"]*\\b'+column+'\\b[^"]*">([\\s\\S]*?)</td>').exec(row);
      const amount = /^\$([\d,]+\.\d{2})$/.exec(plain(cell?.[1]||''));
      if (amount && Number(amount[1].replaceAll(',','')) > 0) prices[grade] = Number(amount[1].replaceAll(',',''));
    }
    pricesByCard.set(id, {id,name,prices,sourceUrl:'https://www.pricecharting.com'+product[1]});
  }
  return pricesByCard;
}

async function baseSetQuote(request, id, waitUntil) {
  const cache = globalThis.caches?.default;
  const key = new URL('/api/catalog/pricecharting?base-set=unlimited',request.url).href;
  try {
    let response = await cache?.match(key);
    if (!response) {
      const source = await fetch(baseSetUrl,{redirect:'error',signal:AbortSignal.timeout(6000)});
      if (!source.ok) throw Error('Price guide unavailable');
      const rows = [...parseBaseSet(await source.text()).values()].filter(row=>row && Object.keys(row.prices).length);
      if (!rows.length) throw Error('Empty price guide');
      response = Response.json({rows,checkedAt:new Date().toISOString()},{headers:{'Cache-Control':'public, max-age=900'}});
      if (cache && waitUntil) waitUntil(cache.put(key,response.clone()).catch(()=>{}));
    }
    const {rows,checkedAt} = await response.json();
    const row = rows.find(item=>item.id===id);
    return row ? Response.json({...row,checkedAt,currency:'USD',source:'PriceCharting'},{headers:{'Cache-Control':'public, max-age=900'}})
      : Response.json({error:'Item not found in Base Set Unlimited guide'},{status:404});
  } catch {
    return Response.json({error:'PriceCharting quote unavailable'},{status:503});
  }
}
