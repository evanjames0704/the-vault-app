const providers = [
  {provider:'Entertainment Earth', url:'https://www.entertainmentearth.com/s/hasbro/daredevil/ct', markers:['HSG1598','Daredevil'], requirePrice:true},
  {provider:'GameStop', url:'https://www.gamestop.com/collectibles/figures/products/marvel-legends-series-the-man-without-fear-daredevil-6-in-action-figure/432054.html', markers:['The Man Without Fear', 'Daredevil'], requirePrice:true},
  {provider:'Walmart', url:'https://www.walmart.com/c/kp/marvel-legends-daredevil', markers:['Marvel Legends', 'Daredevil'], requirePrice:true},
  {provider:'Target', url:'https://www.target.com/s/hasbro%2Bmarvel%2Blegends', markers:['Marvel Legends', 'Spider-Man'], requirePrice:true},
  {provider:'Soosoo Toys', url:'https://soosootoysfigure.com/shop', markers:['SST-073', 'SST-064']},
  {provider:'Card Hedge', url:'https://ai.cardhedger.com/price-guide/category/pokemon', markers:['POKEMON CARD PRICE GUIDE'], requirePrice:true},
  {provider:'Galactic Toys', url:'https://galactictoys.com/collections/funko', markers:['Galactic Toys Exclusive', 'Funko Pop']},
  {provider:'Toy Dojo', url:'https://toydojo.com/collections/official-transformers', markers:['Leader Megatron', 'Leader Soundwave']},
  {provider:'ActionFigure411', url:'https://www.actionfigure411.com/marvel/marvel-legends-exclusives-daredevil-born-again-10265.php', markers:['5010996282842', 'sold auctions']},
  {provider:'Sports Card Investor', url:'https://www.sportscardinvestor.com/cards/ken-griffey-jr-baseball/1989-upper-deck-base-1/raw', markers:['Ken Griffey Jr.', 'Recent Sales']},
  {provider:'TCGplayer', url:'https://www.tcgplayer.com/categories/trading-and-collectible-card-games/pokemon/price-guides/base-set', markers:['Pikachu', 'Market Price']},
  {provider:'PriceCharting', url:'https://www.pricecharting.com/game/pokemon-base-set/pikachu-58', markers:['Pikachu', 'Full Price Guide']},
  {provider:'PokéData Unlimited', url:'https://ssr.pokedata.io/set/Base%2BSet%2BUnlimited', markers:['Pikachu', 'Base Set Unlimited']},
  {provider:'PokéData Shadowless', url:'https://ssr.pokedata.io/set/Base%2BSet%2BShadowless', markers:['Pikachu', 'Shadowless']},
];

async function probe({provider,url,markers,requirePrice}) {
  try {
    const response = await fetch(url, {redirect:'manual', signal:AbortSignal.timeout(6000)});
    const isHtml = response.headers.get('content-type')?.includes('text/html');
    if (!response.ok || !isHtml || !response.body) {
      await response.body?.cancel();
      return {provider,status:response.status,readable:false};
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let html = '', bytes = 0, readable = false;
    try {
      while (bytes < 2000000) {
        const {done,value} = await reader.read();
        if (done) break;
        bytes += value.byteLength;
        html += decoder.decode(value,{stream:true});
        readable = markers.every(marker=>html.includes(marker)) && (!requirePrice || /\$\s*[0-9][0-9,]*\.[0-9]{2}\b/.test(html));
        if (readable) break;
      }
    } finally {
      await reader.cancel().catch(()=>{});
    }
    return {provider,status:response.status,readable};
  } catch (error) {
    return {provider,status:null,readable:false,error:error.name==='TimeoutError'?'timeout':'request failed'};
  }
}

export async function onRequestGet() {
  return Response.json({probes:await Promise.all(providers.map(probe))},{
    headers:{'Cache-Control':'public, max-age=300'},
  });
}
