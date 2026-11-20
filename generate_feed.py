#!/usr/bin/env python3
"""Convert ActiveShop stock feed into a Shoptet update-only XML feed."""
import os
import urllib.request
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_CEILING
from pathlib import Path

SOURCE = os.getenv('SOURCE_URL', 'https://b2b.activeshop.com.pl/media/productsfeed/stock-b2b.xml')
RATE = Decimal('25')
VAT = Decimal('1.21')  # verify product-specific VAT before production
MARGIN_FACTOR = Decimal('0.75')
MAX_ITEMS = 10000


def main():
  request = urllib.request.Request(
    SOURCE,
    headers={"User-Agent": "Mozilla/5.0"}
)
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read(5_000_001)
    if len(data) > 5_000_000:
        raise RuntimeError('Unexpectedly large source feed')
    root = ET.fromstring(data)
    items = root.findall('./item')
    if not 3000 <= len(items) <= MAX_ITEMS:
        raise RuntimeError(f'Unexpected product count {len(items)}; refusing to publish')
    shop = ET.Element('SHOP')
    seen = set()
    for item in items:
        sku = (item.findtext('indeks') or '').strip()
        qty = (item.findtext('stock') or '').strip()
        price = (item.findtext('price') or '').strip()
        if not sku or sku in seen or not sku.isdigit():
            raise RuntimeError(f'Missing/duplicate/invalid SKU: {sku}')
        seen.add(sku)
        try:
            stock = int(qty)
            purchase = Decimal(price) * RATE
            if stock < 0 or purchase <= 0 or not purchase.is_finite():
                raise ValueError('invalid stock or price')
        except Exception as exc:
            raise RuntimeError(f'Invalid supplier data for {sku}: {exc}') from exc
        gross = (purchase / MARGIN_FACTOR * VAT).to_integral_value(rounding=ROUND_CEILING)
        node = ET.SubElement(shop, 'SHOPITEM')
        ET.SubElement(node, 'CODE').text = sku
        ET.SubElement(node, 'PRICE_VAT').text = str(gross)
        # Never publish supplier purchase price to public GitHub Pages.
        stock_node = ET.SubElement(node, 'STOCK')
        warehouses = ET.SubElement(stock_node, 'WAREHOUSES')
        warehouse = ET.SubElement(warehouses, 'WAREHOUSE')
        ET.SubElement(warehouse, 'NAME').text = 'Výchozí sklad'
        ET.SubElement(warehouse, 'VALUE').text = str(stock)
    output = Path('public')
    output.mkdir(exist_ok=True)
    target = output / 'activeshop-update.xml'
    ET.ElementTree(shop).write(target, encoding='utf-8', xml_declaration=True)
    print(f'Generated {len(items)} items at {target}')


if __name__ == '__main__':
    main()
