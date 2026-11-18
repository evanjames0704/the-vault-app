import {readFileSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';

const output = process.argv[2];
if (!output) throw Error('Specify the Pages output directory');
const routes = {search:'ebay/search', estimate:'ebay/estimate', card:'tcdb/card'};
const modules = Object.entries(routes).map(([route,path]) => {
  const source = readFileSync(new URL(`../functions/api/${path}.js`, import.meta.url),'utf8');
  return `const ${route} = (() => {\n${source.replace(/^export /gm,'')}\nreturn onRequestGet;\n})();\n`;
});
writeFileSync(join(output,'_worker.js'), modules.join('\n')+`
export default {
  fetch(request, env, ctx) {
    const pathname = new URL(request.url).pathname;
    if (pathname !== '/api/ebay/estimate' && pathname !== '/api/ebay/search' && pathname !== '/api/tcdb/card') return env.ASSETS.fetch(request);
    if (request.method !== 'GET') return new Response(null,{status:405,headers:{Allow:'GET'}});
    const handler = pathname === '/api/tcdb/card' ? card : pathname === '/api/ebay/estimate' ? estimate : search;
    return handler({request, env, waitUntil: promise => ctx.waitUntil(promise)});
  },
};
`);
writeFileSync(join(output,'_routes.json'), JSON.stringify({
  version: 1, include: Object.values(routes).map(path=>'/api/'+path), exclude: [],
}, null, 2));
