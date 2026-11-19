"""Import Neon Ichiban digital editions listed in its public product sitemaps."""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ORIGIN = 'https://neonichiban.com'
CATALOG = ORIGIN + '/sitemap.xml'


def fetch(url):
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'TheVaultCollectionCatalog/1.0'})
            with urlopen(request, timeout=25) as response:
                if urlsplit(response.url).hostname != 'neonichiban.com':
                    raise ValueError('Unexpected redirect')
                return response.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))


def discover(url):
    root = ET.fromstring(fetch(url))
    if root.tag.endswith('sitemapindex'):
        for loc in root.findall('.//{*}loc'):
            child = (loc.text or '').strip()
            if child.startswith(ORIGIN + '/sitemaps/sitemap-products-'):
                yield from discover(child)
    elif root.tag.endswith('urlset'):
        for loc in root.findall('./{*}url/{*}loc'):
            item = (loc.text or '').strip()
            match = re.fullmatch(r'https://neonichiban\.com/item/(\d+)(?:/[^/?#]+)?/?', item)
            if match:
                yield match.group(1), item
    else:
        raise ValueError(f'Unexpected sitemap format: {url}')


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.structured = []
        self.script = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            key = attrs.get('property') or attrs.get('name')
            if key and attrs.get('content'):
                self.meta.setdefault(key, attrs['content'])
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.script = []

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            try:
                self.structured.append(json.loads(''.join(self.script)))
            except ValueError:
                pass
            self.script = None


def nodes(value):
    if isinstance(value, list):
        for entry in value:
            yield from nodes(entry)
    elif isinstance(value, dict):
        yield value
        yield from nodes(value.get('@graph', []))


def label(value):
    if isinstance(value, dict):
        return str(value.get('name') or '')
    return value if isinstance(value, str) else ''


def parse_item(item_id, url, payload):
    page = Metadata()
    page.feed(payload.decode('utf-8', errors='replace'))
    product = next((x for x in nodes(page.structured)
                    if 'Product' in x.get('@type', [])), {})
    title = (label(product.get('name')) or page.meta.get('og:title', '')).strip()
    title = title.removesuffix(' | Neon Ichiban')
    if not title or title.casefold() in {'neon ichiban', 'page not found'}:
        raise ValueError('No edition title')
    cover = product.get('image') or page.meta.get('og:image') or ''
    if isinstance(cover, list):
        cover = next(iter(cover), '')
    if isinstance(cover, dict):
        cover = cover.get('url') or cover.get('contentUrl') or ''
    image = urljoin(ORIGIN, cover) if isinstance(cover, str) and cover else ''
    if urlsplit(image).scheme != 'https' or urlsplit(image).hostname not in {'neonichiban.com','assets.neonichiban.com'}:
        image = ''
    offers = product.get('offers') or {}
    if isinstance(offers, list):
        offers = next((offer for offer in offers if isinstance(offer, dict) and offer.get('priceCurrency') == 'USD'), {})
    currency = offers.get('priceCurrency') or page.meta.get('product:price:currency')
    quoted = offers.get('price') if 'price' in offers else page.meta.get('product:price:amount')
    try:
        price = float(quoted) if currency == 'USD' else None
    except (ValueError, TypeError):
        price = None
    if price is not None and not 0 <= price < 100000:
        price = None
    issue = re.search(r'#\s*(-?\d+[a-z]?)\b', title, re.I)
    return {
        'name': title, 'identifier': f'Neon Ichiban {item_id}',
        'number': issue.group(1) if issue else '', 'brand': label(product.get('brand')) or label(product.get('publisher')),
        'category': 'Comic books', 'variant': 'Digital edition', 'source': 'Neon Ichiban',
        'sourceUrl': url, 'image': image, 'retailPrice': price, 'priceSource': 'Neon Ichiban digital edition',
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--output', type=Path, default=Path('neon-ichiban-catalog.json'))
    cli.add_argument('--cache', type=Path, default=Path('.neon-catalog-cache'))
    cli.add_argument('--workers', type=int, default=2, choices=range(1, 5))
    cli.add_argument('--limit', type=int, help='Import a sample only')
    args = cli.parse_args()
    urls = dict(discover(CATALOG))
    if not urls:
        raise SystemExit('No product URLs were found. Existing catalog retained.')
    work = list(urls.items())
    print(f'{len(work)} unique item URLs in publisher sitemaps', flush=True)
    if args.limit:
        work = work[:args.limit]
    args.cache.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()

    def import_item(pair):
        item_id, url = pair
        version = hashlib.sha256(url.encode()).hexdigest()[:12]
        saved = args.cache / f'{today}-{item_id}-{version}.json'
        if saved.exists():
            return json.loads(saved.read_text())
        time.sleep(0.5)
        row = parse_item(item_id, url, fetch(url))
        saved.write_text(json.dumps(row, ensure_ascii=False))
        return row

    rows, failures = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(import_item, pair): pair[1] for pair in work}
        for future in concurrent.futures.as_completed(futures):
            try:
                rows.append(future.result())
                if len(rows) % 250 == 0:
                    print(f'{len(rows)} of {len(work)} imported', flush=True)
            except (OSError, ValueError) as error:
                failures.append((futures[future], str(error)))
    if failures:
        for url, error in failures[:20]:
            print(f'{url}: {error}')
        raise SystemExit(f'{len(failures)} pages failed. Existing catalog retained.')
    rows.sort(key=lambda row: int(row['identifier'].split()[-1]))
    result = dict(schema='vault-neon-ichiban-v1', checkedAt=today, items=rows)
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':'))+'\n')
    temporary.replace(args.output)
    print(f"{len(rows)} editions; {sum(r['image'] != '' for r in rows)} covers; "
          f"{sum(r['retailPrice'] is not None for r in rows)} listed USD prices", flush=True)


if __name__ == '__main__':
    main()
