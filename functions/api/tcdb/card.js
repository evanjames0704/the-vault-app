const ORIGIN = 'https://www.tcdb.com';
const CARD_PATH = /^\/ViewCard\.cfm\/sid\/\d+\/cid\/\d+\/[a-z0-9._~%()-]{1,180}$/i;

export async function onRequestGet({request}) {
  const path = new URL(request.url).searchParams.get('path') || '';
  if (!CARD_PATH.test(path)) return Response.json({error:'Enter an exact TCDB card URL.'},{status:400});
  try {
    const upstream = await fetch(ORIGIN+path,{redirect:'error',signal:AbortSignal.timeout(7000)});
    if (!upstream.ok) throw Error('Card page unavailable');
    let name='', image='', price='', sport='';
    const parsed=new HTMLRewriter()
      .on('meta[property="og:title"]',{element(node){name=node.getAttribute('content')||'';}})
      .on('meta[property="og:image"]',{element(node){image=node.getAttribute('content')||'';}})
      .on('a[href^="/Price.cfm/"]',{text(chunk){price+=chunk.text;}})
      .on('select[name="SearchCategory"] option[selected]',{element(node){sport=node.getAttribute('value')||'';}})
      .transform(upstream);
    await parsed.body.pipeTo(new WritableStream());
    if (!name.includes('#')) throw Error('Card details unavailable');
    const match=/^\$([\d,]+\.\d{2})$/.exec(price.trim());
    const amount=match?Number(match[1].replaceAll(',','')):null;
    const category=['Gaming','Non-Sport'].includes(sport)?'Trading cards':'Sports cards';
    return Response.json({
      name, category, number:/#([^\s]+)/.exec(name)?.[1]||'',
      image:image.startsWith(ORIGIN+'/Images/')?image:'',
      marketPrice:Number.isFinite(amount)&&amount>0?amount:null,
      source:'TCDB',
    },{headers:{'Cache-Control':'public, max-age=3600'}});
  } catch {
    return Response.json({error:'TCDB card details are temporarily unavailable.'},{status:503});
  }
}
