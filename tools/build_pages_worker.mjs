import {readFileSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';

const output = process.argv[2];
if (!output) throw Error('Specify the Pages output directory');
const routes = {search:'ebay/search', estimate:'ebay/estimate', card:'tcdb/card', diagnostics:'catalog/diagnostics', pricecharting:'catalog/pricecharting', storefronts:'catalog/storefronts', legends:'catalog/legends'};
const modules = Object.entries(routes).map(([route,path]) => {
  const source = readFileSync(new URL(`../functions/api/${path}.js`, import.meta.url),'utf8');
  return `const ${route} = (() => {\n${source.replace(/^export /gm,'')}\nreturn onRequestGet;\n})();\n`;
});
writeFileSync(join(output,'_worker.js'), modules.join('\n')+`
export default {
  fetch(request, env, ctx) {
    const pathname = new URL(request.url).pathname;
    const handler = {
      '/api/ebay/search': search, '/api/ebay/estimate': estimate,
      '/api/tcdb/card': card, '/api/catalog/diagnostics': diagnostics,
      '/api/catalog/pricecharting': pricecharting, '/api/catalog/storefronts': storefronts, '/api/catalog/legends': legends,
    }[pathname];
    if (!handler) return env.ASSETS.fetch(request);
    if (request.method !== 'GET') return new Response(null,{status:405,headers:{Allow:'GET'}});
    return handler({request, env, waitUntil: promise => ctx.waitUntil(promise)});
  },
};
`);
writeFileSync(join(output,'_routes.json'), JSON.stringify({
  version: 1, include: Object.values(routes).map(path=>'/api/'+path), exclude: [],
}, null, 2));
