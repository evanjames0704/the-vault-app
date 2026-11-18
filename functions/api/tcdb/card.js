const ORIGIN = 'https://www.tcdb.com';
const CARD_PATH = /^\/ViewCard\.cfm\/sid\/\d+\/cid\/\d+\/[a-z0-9._~%,()!'-]{1,180}$/i;

const SPORTS = new Set(['Baseball','Basketball','Boxing','Cricket','Football','Golf','Hockey','MMA','Racing','Soccer','Tennis','Wrestling','Multi-Sport','Misc Sports']);
const PLAYER_PATH = /^\/Person\.cfm\/pid\/\d+\/col\/1\/yea\/0(?:\/[a-z0-9._~%,()'-]{1,180})?\/?$/i;

function playerPage(value) {
  try {
    const url = new URL(value, ORIGIN);
    if (url.origin!==ORIGIN || !PLAYER_PATH.test(url.pathname)) return null;
    const page=url.searchParams.get('PageIndex')||'1';
    if (!/^[1-9]\d{0,5}$/.test(page)) return null;
    url.search=new URLSearchParams({PageIndex:page});
    url.hash='';
    return url;
  } catch { return null; }
}

async function playerCards(params) {
  const name=(params.get('name')||'').trim();
  const sport=params.get('sport')||'';
  const next=params.get('next');
  let current=next?playerPage(next):null;
  if (next ? !current : name.length<2 || name.length>80 || !SPORTS.has(sport)) {
    return Response.json({error:'Enter a player name and sport.'},{status:400});
  }
  const options={redirect:'manual',signal:AbortSignal.timeout(8000)};
  try {
    let response;
    if (!current) {
      response=await fetch(ORIGIN+'/ViewResults.cfm?MODE=ADVANCED',{
        ...options,method:'POST',body:new URLSearchParams({MODE:'GET',Type:sport,Name:name}),
      });
      const location=response.headers.get('location');
      if (location) {
        current=playerPage(location);
        if (!current) throw Error('Unexpected TCDB redirect');
      }
    }
    if (current) response=await fetch(current,options);
    if (!response.ok) throw Error('Player checklist unavailable');
    const cards=new Map();
    let card, following=null, title='';
    const parsed=new HTMLRewriter()
      .on('title',{text(chunk){title+=chunk.text;}})
      .on('td.vertical a[href^="/ViewCard.cfm/"]',{
        element(node){
          const path=node.getAttribute('href')||'';
          card=CARD_PATH.test(path)?{path,name:''}:null;
          if(card)cards.set(path,card);
        },
        text(chunk){if(card)card.name+=chunk.text;},
      })
      .on('a.page-link[href*="PageIndex="]',{
        element(node){
          const page=playerPage(node.getAttribute('href'));
          const expected=Number(current?.searchParams.get('PageIndex')||1)+1;
          if(page&&(!current||page.pathname.split('/')[3]===current.pathname.split('/')[3])&&Number(page.searchParams.get('PageIndex'))===expected)
            following=page.pathname+page.search;
        },
      }).transform(response);
    await parsed.body.pipeTo(new WritableStream());
    if (/attention required|verify.*human|just a moment/i.test(title)) throw Error('Verification required');
    const results=[...cards.values()].map(row=>({...row,name:row.name.trim()})).filter(row=>row.name);
    return Response.json({results,next:results.length?following:null});
  } catch {
    return Response.json({error:'TCDB player search is temporarily unavailable.'},{status:503});
  }
}

export async function onRequestGet({request}) {
  const params=new URL(request.url).searchParams;
  if(params.get('mode')==='player')return playerCards(params);
  const path = params.get('path') || '';
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
