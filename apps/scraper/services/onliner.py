import re
from decimal import Decimal
import httpx
from selectolax.lexbor import LexborHTMLParser
from apps.listings.models import Listing, Platform
from apps.scraper.utils import parse_russian_date


class OnlinerScraper:
    BASE_URL = "https://baraholka.onliner.by/viewforum.php"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }

    def scrape_new(self, target_count: int = 40, forum_id: int = 1178, max_pages: int = 15) -> int:
        target_count = min(max(1, target_count), 200)
        saved_count = 0
        consecutive_empty_pages = 0

        with httpx.Client(headers=self.HEADERS, timeout=15.0, follow_redirects=True) as client:
            for page in range(max_pages):
                if saved_count >= target_count:
                    break

                params = {"f": forum_id, "start": page * 50}
                resp = client.get(self.BASE_URL, params=params)
                resp.raise_for_status()

                tree = LexborHTMLParser(resp.text)
                rows = [r for r in tree.css("tr") if r.css_first("td.cost") and r.css_first("h2.wraptxt a")]
                if not rows:
                    break

                parsed_rows = []
                batch_ids = []
                for row in rows:
                    title_node = row.css_first("h2.wraptxt a")
                    href = title_node.attributes.get("href", "")
                    id_match = re.search(r"t=(\d+)", href)
                    if id_match:
                        ext_id = id_match.group(1)
                        batch_ids.append(ext_id)
                        parsed_rows.append((ext_id, row, title_node))

                existing_ids = set(
                    Listing.objects.filter(platform=Platform.ONLINER, external_id__in=batch_ids)
                    .values_list("external_id", flat=True)
                )

                page_saved = 0
                for external_id, row, title_node in parsed_rows:
                    if saved_count >= target_count:
                        break
                    if external_id in existing_ids:
                        continue

                    title = title_node.text(strip=True)
                    full_url = f"https://baraholka.onliner.by/viewtopic.php?t={external_id}"

                    desc_node = row.css_first("p.ba-description")
                    description = desc_node.text(strip=True) if desc_node else ""

                    city_node = row.css_first("p.ba-signature strong")
                    city = city_node.text(strip=True) if city_node else ""

                    user_node = row.css_first("p.ba-signature a[href*='/user/']") or row.css_first("p.ba-signature a")
                    seller_name = "Не указан"
                    seller_id = None
                    if user_node:
                        seller_name = user_node.text(strip=True)
                        uid_match = re.search(r"/user/(\d+)", user_node.attributes.get("href", ""))
                        if uid_match:
                            seller_id = uid_match.group(1)

                    price = None
                    price_node = row.css_first("td.cost div.price-primary")
                    if price_node:
                        clean_price = re.search(r"([\d\s]+[.,]?\d*)", price_node.text(strip=True))
                        if clean_price:
                            try:
                                price = Decimal(clean_price.group(1).replace(" ", "").replace(",", "."))
                            except Exception:
                                price = None

                    img_node = row.css_first("td.ph img")
                    image_url = img_node.attributes.get("src") if img_node else None

                    # Извлекаем и нормализуем дату публикации/апа
                    date_node = row.css_first("p.ba-post-up")
                    pub_date = parse_russian_date(date_node.text(strip=True)) if date_node else None

                    Listing.objects.create(
                        platform=Platform.ONLINER,
                        external_id=external_id,
                        url=full_url,
                        title=title,
                        description=description,
                        price=price,
                        currency="BYN",
                        city=city or None,
                        seller_id=seller_id,
                        seller_name=seller_name,
                        published_at=pub_date,
                        image_url=image_url,
                        raw_metadata={"forum_id": forum_id}
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
