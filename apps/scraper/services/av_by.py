import re
from decimal import Decimal
import httpx
from selectolax.lexbor import LexborHTMLParser
from apps.listings.models import Listing, Platform
from apps.scraper.utils import parse_russian_date


class AvByScraper:
    BASE_URLS = {
        "cars": "https://cars.av.by/filter",
        "moto": "https://moto.av.by/filter",
        "truck": "https://truck.av.by/filter",
    }
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }

    def fetch_car_details(self, client: httpx.Client, url: str) -> tuple[str, str | None]:
        try:
            resp = client.get(url, timeout=10.0)
            if resp.status_code != 200:
                return "", None
            tree = LexborHTMLParser(resp.text)

            description = ""
            comment_node = tree.css_first(".card__comment")
            if comment_node:
                raw_text = comment_node.text(separator="\n", strip=True)
                description = re.sub(r"^Описание\s*", "", raw_text, flags=re.IGNORECASE).strip()

            og_img = tree.css_first('meta[property="og:image"]')
            image_url = og_img.attributes.get("content") if og_img else None
            return description, image_url
        except Exception:
            return "", None

    def scrape_new(self, target_count: int = 25, category: str = "cars", max_pages: int = 15) -> int:
        target_count = min(max(1, target_count), 200)
        base_url = self.BASE_URLS.get(category, self.BASE_URLS["cars"])
        saved_count = 0
        consecutive_empty_pages = 0

        with httpx.Client(headers=self.HEADERS, timeout=15.0, follow_redirects=True) as client:
            for page in range(1, max_pages + 1):
                if saved_count >= target_count:
                    break

                params = {"page": page} if page > 1 else {}
                resp = client.get(base_url, params=params)
                resp.raise_for_status()

                tree = LexborHTMLParser(resp.text)
                items = tree.css("div.listing-item")
                if not items:
                    break

                parsed_items = []
                batch_ids = []
                for item in items:
                    title_node = (
                        item.css_first("h3 a")
                        or item.css_first("a.listing-item__link")
                        or item.css_first('[class*="listing-item__title"] a')
                    )
                    if not title_node:
                        continue
                    href = title_node.attributes.get("href", "")
                    id_match = re.search(r"/(\d+)(?:[/?#]|$)", href)
                    if not id_match or "finance" in href or "leasing" in href:
                        continue
                    ext_id = id_match.group(1)
                    batch_ids.append(ext_id)
                    parsed_items.append((ext_id, item, title_node, href))

                existing_ids = set(
                    Listing.objects.filter(platform=Platform.AV_BY, external_id__in=batch_ids)
                    .values_list("external_id", flat=True)
                )

                page_saved = 0
                for external_id, item, title_node, href in parsed_items:
                    if saved_count >= target_count:
                        break
                    if external_id in existing_ids:
                        continue  # Пропускаем дубликат, не заходя на его страницу!

                    domain = base_url.split("/filter")[0]
                    full_url = f"{domain}{href}" if href.startswith("/") else href
                    title = re.sub(r"\s+", " ", title_node.text(separator=" ", strip=True))

                    loc_node = item.css_first('[class*="listing-item__location"]')
                    city = loc_node.text(strip=True) if loc_node else ""

                    date_node = item.css_first('[class*="listing-item__date"]')
                    pub_date = parse_russian_date(date_node.text(strip=True)) if date_node else None

                    price = None
                    price_node = item.css_first('[class*="price-primary"]') or item.css_first('[class*="listing-item__price"]')
                    if price_node:
                        raw_price = price_node.text(strip=True)
                        before_rub = raw_price.split("руб")[0] if "руб" in raw_price else raw_price
                        digits = re.sub(r"[^\d]", "", before_rub)
                        if digits:
                            try:
                                price = Decimal(digits)
                            except Exception:
                                price = None

                    seller_desc, image_url = self.fetch_car_details(client, full_url)

                    Listing.objects.create(
                        platform=Platform.AV_BY,
                        external_id=external_id,
                        url=full_url,
                        title=title,
                        description=seller_desc,
                        price=price,
                        currency="BYN",
                        city=city or None,
                        seller_name="Частное лицо",
                        published_at=pub_date,
                        image_url=image_url,
                        raw_metadata={"vehicle_type": category}
                    )
                    existing_ids.add(external_id)
                    saved_count += 1
                    page_saved += 1

                if page_saved == 0:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 3:
                        break
                else:
                    consecutive_empty_pages = 0

        return saved_count
