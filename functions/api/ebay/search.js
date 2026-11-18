const EBAY_API = 'https://api.ebay.com';
const BASE_SCOPE = 'https://api.ebay.com/oauth/api_scope';
const modes = {
  listings: { path: '/buy/browse/v1/item_summary/search', scope: BASE_SCOPE },
  catalog: {
    path: '/commerce/catalog/v1_beta/product_summary/search',
    scope: BASE_SCOPE + '/commerce.catalog.readonly',
  },
};
const tokens = new Map();

function json(data, status = 200) {
  return Response.json(data, {status, headers: {'Cache-Control': 'no-store'}});
}

async function accessToken({EBAY_CLIENT_ID, EBAY_CLIENT_SECRET}, scope) {
  const key = EBAY_CLIENT_ID + ':' + scope;
  const cached = tokens.get(key);
  if (cached && cached.expires > Date.now()) return cached.token;
  const response = await fetch(EBAY_API + '/identity/v1/oauth2/token', {
    method: 'POST',
    headers: {
      Authorization: 'Basic ' + btoa(EBAY_CLIENT_ID + ':' + EBAY_CLIENT_SECRET),
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({grant_type: 'client_credentials', scope}),
    signal: AbortSignal.timeout(7000),
  });
  if (!response.ok) throw Error('eBay could not authorize this API with the configured app keys.');
  const data = await response.json();
  if (typeof data.access_token !== 'string') throw Error('eBay did not return an access token.');
  tokens.set(key, {token: data.access_token, expires: Date.now() + (Number(data.expires_in) - 60) * 1000});
  return data.access_token;
}

function listing(row) {
  const price = Number(row.price?.value);
  let url;
  try { url = new URL(row.itemWebUrl); } catch { return null; }
  if (url.origin !== 'https://www.ebay.com' || typeof row.title !== 'string' ||
      row.price?.currency !== 'USD' || !Number.isFinite(price) || price <= 0 ||
      !row.buyingOptions?.includes('FIXED_PRICE')) return null;
  return {title: row.title, price, condition: row.condition ?? '', url: url.href};
}

export async function onRequestGet({request, env}) {
  const params = new URL(request.url).searchParams;
  const mode = params.get('mode') ?? 'listings';
  const config = Object.hasOwn(modes, mode) ? modes[mode] : null;
  const query = params.get('q')?.trim() ?? '';
  const epid = params.get('epid') ?? '';
  if (!config || query.length > 100 || (epid ? mode !== 'listings' || !/^\d{1,20}$/.test(epid) : query.length < 2)) {
    return json({error: 'Enter a collectible name, barcode, or valid eBay product ID.'}, 400);
  }
  if (!env.EBAY_CLIENT_ID || !env.EBAY_CLIENT_SECRET) {
    return json({error: 'Live eBay pricing has not been connected to this deployment.'}, 503);
  }
  const url = new URL(config.path, EBAY_API);
  url.searchParams.set('limit', '12');
  if (epid) url.searchParams.set('epid', epid);
  else if (/^(?:\d{8}|\d{12,14})$/.test(query)) url.searchParams.set('gtin', query);
  else url.searchParams.set('q', query);
  try {
    const token = await accessToken(env, config.scope);
    const response = await fetch(url, {
      headers: {Authorization: 'Bearer ' + token, 'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'},
      signal: AbortSignal.timeout(7000),
    });
    if (!response.ok) {
      const error = response.status === 429 ? 'eBay’s request limit was reached. Try again later.' :
        'This eBay search is unavailable. Check the app’s API access and try again.';
      return json({error}, response.status === 429 ? 429 : 502);
    }
    const data = await response.json();
    const results = mode === 'listings'
      ? (data.itemSummaries ?? []).map(listing).filter(Boolean)
      : (data.productSummaries ?? []).filter(row => /^\d{1,20}$/.test(row.epid ?? '') && typeof row.title === 'string')
        .map(row => ({epid: String(row.epid), title: row.title}));
    return json({mode, observedAt: new Date().toISOString(), results});
  } catch (error) {
    return json({error: error.name === 'TimeoutError' ? 'eBay took too long to respond.' : 'Could not connect to eBay. Check the app’s credentials and API access.'}, 502);
  }
}
