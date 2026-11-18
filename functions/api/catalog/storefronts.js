const storefronts = [
  {id:'mercari',source:'Mercari',origin:'https://www.mercari.com'},
  {id:'replay',source:'Replay Toys',origin:'https://replaytoys.com'},
  {id:'toyco',source:'Toyco',origin:'https://www.toyco.store'},
  {id:'timewalker',source:'Timewalker Toys',origin:'https://www.timewalkertoys.com'},
  {id:'notjust',source:'Not Just Toyz',origin:'https://www.notjusttoyz.com',bigCommerce:true},
  {id:'nerdz',source:'Game Nerdz',origin:'https://www.gamenerdz.com',bigCommerce:true},
];
const entities = {amp:'&',quot:'"',apos:"'",lt:'<',gt:'>',nbsp:' '};
function decode(text) {
  return text.replace(/&(#x[0-9a-f]+|#\d+|amp|quot|apos|lt|gt|nbsp);/gi,(entity,key)=>{
    if (key[0]!=='#') return entities[key.toLowerCase()] ?? entity;
    const code = /^#x/i.test(key) ? parseInt(key.slice(2),16) : Number(key.slice(1));
    return code<=0x10ffff ? String.fromCodePoint(code) : entity;
  }).trim();
}
function category(name) {
  if (/\bhot toys\b|\b(?:tms|mms)\d+\b/i.test(name)) return 'Hot Toys';
  if (/\bfunko\b|\bpop!/i.test(name)) return 'Funko Pops';
  if (/\blego\b/i.test(name)) return 'LEGO';
  if (/\b(?:pokemon|pokémon|magic: the gathering|trading cards|booster pack)\b/i.test(name)) return 'Trading cards';
  return 'Action figures';
}

export function parseStorefront(html, store) {
  const cards = html.split(/<div class="card-wrapper product-card-wrapper\b[^"]*">/i).slice(1);
  const products = new Map();
  for (const card of cards) {
    const link = /<a\b(?=[^>]*\bid="CardLink--(\d+)")(?=[^>]*\bhref="(\/products\/[a-z0-9-]+)(?:\?[^"]*)?")[^>]*>([^<]+)<\/a>/i.exec(card);
    if (!link) continue;
    const [,productId,path,title] = link;
    const name = decode(title);
    const imagePath = /<img\b[^>]*\ssrc="((?:https:)?\/\/[^"]+)"/i.exec(card)?.[1];
    const image = imagePath ? new URL(decode(imagePath),store.origin).href : '';
    const identifier = store.id+':'+productId;
    products.set(identifier,{
      name,category:category(name),identifier,image,storefront:true,source:store.source,
      sourceUrl:store.origin+path,available:!/\bprice--sold-out\b/.test(card),
    });
  }
  return [...products.values()];
}

export async function onRequestGet({request}) {
  const params = new URL(request.url).searchParams;
  if (params.has('product')) return productQuote(params);
  const query = params.get('q')?.trim();
  if (!query || query.length<2 || query.length>100) return Response.json({results:[],unavailable:[]});
  const results = await Promise.allSettled(storefronts.map(async store=>{
    if(store.id==='mercari'){
      const slug=query.toLowerCase().match(/[a-z0-9]+/g)?.join('-');
      if(!slug)return [];
      return parseMercari(await storefrontPage(new URL('/us/shop/'+slug+'/',store.origin)));
    }
    const timewalker = store.id==='timewalker';
    const url = new URL(timewalker?'/SearchResults.asp':store.bigCommerce?'/search.php':'/search',store.origin);
    url.search = new URLSearchParams(timewalker?{Search:query}:store.bigCommerce
      ? {search_query:query,section:'product'} : {q:query,type:'product'});
    const html = await storefrontPage(url);
    const rows = timewalker?parseTimewalker(html,store):store.bigCommerce?parseBigCommerce(html,store):parseStorefront(html,store);
    if (!rows.length && !/\b(?:no results found|No results for|0 results)\b/i.test(html)) throw Error('unrecognized search page');
    return rows;
  }));
  const unavailable = storefronts.filter((_,index)=>results[index].status==='rejected').map(store=>store.source);
  const issues = results.flatMap((result,index)=>result.status==='rejected'
    ? [{source:storefronts[index].source,reason:result.reason?.message||'request failed'}] : []);
  return Response.json({results:results.flatMap(result=>result.status==='fulfilled'?result.value:[]),unavailable,issues},{
    headers:{'Cache-Control':unavailable.length?'no-store':'public, max-age=300'},
  });
}

export function parseMercari(html) {
  const products=new Map();
  for(const [,raw] of html.matchAll(/<script[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi)){
    let item;
    try{item=JSON.parse(raw);}catch{continue;}
    const offer=item?.offers;
    const link=/^https:\/\/www\.mercari\.com\/us\/item\/(m\d+)\/$/.exec(offer?.url||'');
    const amount=Number(offer?.price);
    if(item?.['@type']!=='Product'||!link||typeof item.name!=='string'||offer.priceCurrency!=='USD'||
       !offer.availability?.endsWith('/InStock')||!Number.isFinite(amount)||amount<=0)continue;
    const image=Array.isArray(item.image)?item.image[0]:'';
    products.set(link[1],{name:item.name,identifier:'mercari:'+link[1],category:category(item.name),
      source:'Mercari listing',sourceUrl:offer.url,image:/^https:\/\/[^/]+\.mercdn\.net\//.test(image)?image:'',
      askingPrice:amount});
  }
  return [...products.values()].slice(0,24);
}

export function parseBigCommerce(html, store) {
  const rows = new Map();
  const usd = /data-currency-code="USD"/.test(html);
  for (const [,card] of html.matchAll(/<article class="card\b[^"]*"[^>]*>([\s\S]*?)<\/article>/gi)) {
    const link = /<h[234] class="card-title"[^>]*>\s*<a href="([^"]+)"[^>]*>([^<]+)<\/a>/i.exec(card);
    if (!link) continue;
    const sourceUrl = new URL(decode(link[1]),store.origin);
    if (sourceUrl.origin!==store.origin || !/^\/[a-z0-9-]+\/$/i.test(sourceUrl.pathname)) continue;
    const name = decode(link[2]);
    const image = /<img src="(https:\/\/cdn\d*\.bigcommerce\.com\/[^"]+)"/i.exec(card)?.[1]||'';
    const price = /<span data-product-price-without-tax\b[^>]*>\s*\$([\d,]+\.\d{2})\s*<\/span>/i.exec(card);
    const amount = price ? Number(price[1].replaceAll(',','')) : 0;
    const retailPrice = usd && amount>0 && !/\b(?:deposit|down payment)\b/i.test(name)?amount:null;
    const identifier = store.id+':'+sourceUrl.pathname.slice(1,-1);
    rows.set(identifier,{identifier,name,category:category(name),image:decode(image),retailPrice,
      source:store.source,sourceUrl:sourceUrl.href});
  }
  return [...rows.values()];
}

export function parseTimewalker(html, store) {
  const rows = new Map();
  for (const card of html.split(/<div class="v-product" itemscope\b/i).slice(1)) {
    const link = /<a href="(https:\/\/www\.timewalkertoys\.com\/[a-z0-9-]+-p\/([a-z0-9-]+)\.htm)" class="v-product__title[^"]*"/i.exec(card);
    const title = /<span itemprop="name">([^<]+)<\/span>/i.exec(card)?.[1];
    if (!link || !title) continue;
    const name = decode(title);
    const imagePath = /<img src="(\/v\/vspfiles\/photos\/[^"]+)"[^>]*itemprop="image"/i.exec(card)?.[1];
    const price = /Our price:<\/font>\s*\$<span itemprop='price' content='(\d+\.\d{2})'>/i.exec(card)?.[1];
    const retailPrice = /itemprop='priceCurrency' content='USD'/.test(card) &&
      !/\b(?:deposit|down payment)\b/i.test(name) && Number(price)>0 ? Number(price) : null;
    const identifier = store.id+':'+link[2].toLowerCase();
    rows.set(identifier,{identifier,name,category:category(name),retailPrice,
      image:imagePath?new URL(decode(imagePath),store.origin).href:'',
      source:store.source,sourceUrl:link[1]});
  }
  return [...rows.values()];
}

async function storefrontPage(url) {
  const signal = AbortSignal.timeout(7000);
  const origin = url.origin;
  for (let i=0;i<3;i++) {
    let response;
    try {
      response = await fetch(url,{redirect:'manual',signal});
    } catch {
      throw Error(signal.aborted?'upstream timeout':'upstream request failed');
    }
    if ([301,302,303,307,308].includes(response.status)) {
      const location = response.headers.get('location');
      if (!location) throw Error('redirect without destination');
      url = new URL(location,url);
      if (url.origin!==origin) throw Error('redirect outside storefront');
      continue;
    }
    if (!response.ok) throw Error('upstream HTTP '+response.status);
    if (!response.headers.get('content-type')?.includes('text/html')) throw Error('unexpected upstream response');
    return response.text();
  }
  throw Error('too many storefront redirects');
}

export function parseProductPrice(html, id) {
  const productId = /"productId":(\d+),"productGid"/.exec(html)?.[1];
  if (productId!==id) return null;
  const nodes = [];
  for (const [,json] of html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/gi)) {
    try {
      const node = JSON.parse(json);
      if (['Product','ProductGroup'].includes(node['@type'])) nodes.push(node);
    } catch {}
  }
  if (nodes.length!==1) return null;
  const [node] = nodes;
  const variants = Array.isArray(node.hasVariant) ? node.hasVariant : [node];
  const deposit = /\b(?:deposit|down payment|balance only|installment)\b/i;
  const full = /\b(?:full price|pay in full|full payment)\b/i;
  const candidates = variants.filter(x=>x.name && !deposit.test(x.name));
  const fullPrice = candidates.filter(x=>full.test(x.name));
  if (candidates.length!==variants.length && !fullPrice.length) return null;
  const amounts = (fullPrice.length?fullPrice:candidates).map(x=>
    x.offers?.priceCurrency==='USD' && x.offers['@type']==='Offer' ? Number(x.offers.price) : NaN
  );
  const amount = amounts[0];
  return Number.isFinite(amount) && amount>0 && amounts.every(value=>value===amount) ? amount : null;
}

async function productQuote(params) {
  const [provider,id] = params.get('product').split(':');
  const store = storefronts.find(item=>item.id===provider);
  const path = params.get('path');
  if (!store || !['replay','toyco'].includes(store.id) || !/^\d{1,20}$/.test(id||'') || params.get('product')!==provider+':'+id ||
      !/^\/products\/[a-z0-9-]{1,240}$/.test(path||'')) return Response.json({error:'Unknown product'},{status:400});
  try {
    const amount = parseProductPrice(await storefrontPage(new URL(path,store.origin)),id);
    return Response.json({amount,currency:'USD',checkedAt:new Date().toISOString()},{
      headers:{'Cache-Control':amount?'public, max-age=600':'no-store'},
    });
  } catch(error) {
    return Response.json({error:error.message},{status:503});
  }
}
