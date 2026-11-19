"""Build a Vault catalog snapshot from a saved public Soosoo Toys shop page."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from lxml import html


def import_cards(source):
    page = html.fromstring(source)
    records = {}
    for card in page.xpath('//*[@id="products-wrapper"]//*[@data-product-id]'):
        titles = card.xpath('.//h3/a[@href]')
        if not titles:
            continue
        link = titles[0]
        url = urlparse(link.get('href'))
        if url.scheme != 'https' or url.hostname != 'soosootoysfigure.com' or not url.path.startswith('/product/'):
            continue
        name = ' '.join(link.text_content().split())
        prices = card.xpath('.//span[contains(concat(" ",normalize-space(@class)," ")," text-primary ") and contains(concat(" ",normalize-space(@class)," ")," font-medium ")]/text()')
        amount = re.fullmatch(r'\$([\d,]+\.\d{2})', prices[0].strip()) if len(prices) == 1 else None
        images = card.xpath('.//a[1]/div/img/@src')
        image = next((image for image in images if image.startswith('https://')), '')
        model = re.search(r'\bSST[- ]?\d+[A-Z]?\b', name, re.I)
        records[url.path] = {
            'name': name, 'category': 'Action figures',
            'identifier': model.group().upper() if model else '',
            'image': image, 'retailPrice': float(amount[1].replace(',', '')) if amount else None,
            'sourceUrl': url.geturl(),
        }
    return list(records.values())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    items = import_cards(args.html.read_bytes())
    if not items:
        parser.error('No public shop product cards found')
    args.output.write_text(json.dumps({
        'schema': 'vault-soosoo-shop-v1',
        'checkedAt': datetime.now(timezone.utc).isoformat(),
        'items': items,
    }, ensure_ascii=False, indent=2) + '\n')
    print(f'{len(items)} listings; {sum(bool(i["retailPrice"]) for i in items)} with listed prices; {sum(bool(i["image"]) for i in items)} with images')
