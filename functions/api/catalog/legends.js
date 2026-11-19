export function parseRetail(html,id,year) {
  const figure = /capture\('figure_viewed',\s*(\{[^\n]+?\})\)/.exec(html);
  if (!figure) return null;
  const row = JSON.parse(figure[1]);
  return String(row.packaging_id)===id && String(row.release_year)===year &&
    row.line==='Marvel Legends' && Number.isFinite(row.retail_price) && row.retail_price>0
    ? row.retail_price : null;
}

export async function onRequestGet({request}) {
  const {searchParams} = new URL(request.url);
  const id=searchParams.get('id'), year=searchParams.get('year'), slug=searchParams.get('slug');
  if (!/^[a-z0-9]{2,20}$/.test(id||'') || !/^\d{4}$/.test(year||'') ||
      !/^[a-z0-9-]{3,200}$/.test(slug||'') || !slug.endsWith('-'+id)) return Response.json({amount:null},{status:400});
  const sourceUrl='https://legendsverse.com/checklist/marvel-legends/figures/'+slug;
  try {
    const response=await fetch(sourceUrl,{redirect:'error',signal:AbortSignal.timeout(6500)});
    if (!response.ok) throw Error();
    const amount=parseRetail(await response.text(),id,year);
    return Response.json({amount,source:'Legendsverse original retail',sourceUrl,currency:'USD',basis:'retail'},
      {headers:{'Cache-Control':'public, max-age=3600'}});
  } catch {
    return Response.json({amount:null},{status:503});
  }
}
