from decimal import Decimal
import httpx
from selectolax.lexbor import LexborHTMLParser
from django.utils.dateparse import parse_datetime
from apps.listings.models import Listing, Platform


class KufarScraper:
    BASE_URL = "https://api.kufar.by/search-api/v2/search/rendered-paginated"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }

    def fetch_full_description(self, client: httpx.Client, url: str) -> str:
        if not url:
            return ""
        try:
            resp = client.get(url, timeout=10.0)
            if resp.status_code == 200:
                tree = LexborHTMLParser(resp.text)
                desc_node = tree.css_first('[itemprop="description"]') or tree.css_first('[class*="description"]')
                if desc_node:
                    return desc_node.text(strip=True)
        except Exception:
            pass
        return ""

    def scrape_new(self, target_count: int = 40, cat: int | None = 5000, max_pages: int = 15) -> int:
        """Собирает до target_count именно НОВЫХ объявлений с предохранителем в max_pages."""
        target_count = min(max(1, target_count), 200)
        saved_count = 0
        cursor = None
        consecutive_empty_pages = 0

        with httpx.Client(headers=self.HEADERS, timeout=15.0, follow_redirects=True) as client:
            for page in range(max_pages):
                if saved_count >= target_count:
                    break

                params = {"lang": "ru", "size": 42, "sort": "lst.d"}
                if cat:
                    params["prn"] = cat
                if cursor:
                    params["cursor"] = cursor

                resp = client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                ads = data.get("ads", [])
                if not ads:
                    break

                # Проверяем одним запросом к БД, какие ID уже есть (чтобы не дублировать и не парсить лишнего)
                batch_ids = [str(ad.get("ad_id")) for ad in ads if ad.get("ad_id")]
                existing_ids = set(
                    Listing.objects.filter(platform=Platform.KUFAR, external_id__in=batch_ids)
                    .values_list("external_id", flat=True)
                )

                page_saved = 0
                for ad in ads:
                    if saved_count >= target_count:
                        break
                    if ad.get("company_ad", False):
                        continue

                    external_id = str(ad.get("ad_id"))
                    if external_id in existing_ids:
                        continue  # Пропускаем дубликат

                    ad_url = ad.get("ad_link", "")
                    seller_name = "Частное лицо"
                    for param in ad.get("account_parameters", []):
                        if param.get("p") == "name" and param.get("v"):
                            seller_name = param.get("v")
                            break

                    price = None
                    price_byn_raw = ad.get("price_byn")
                    if price_byn_raw and price_byn_raw.isdigit():
                        price = Decimal(price_byn_raw) / Decimal(100)

                    pub_date = parse_datetime(ad.get("list_time")) if ad.get("list_time") else None

                    image_url = None
                    images = ad.get("images", [])
                    if images and isinstance(images, list) and images[0].get("path"):
                        image_url = f"https://rms.kufar.by/v1/gallery/{images[0]['path']}"

                    city = ""
                    for p in ad.get("ad_parameters", []):
                        label = p.get("pl", "")
                        if label in ["Город / Район", "Город", "Населенный пункт"]:
                            city = p.get("vl", "")
                            break
                        elif label in ["Район", "Область", "Регион"] and not city:
                            city = p.get("vl", "")

                    full_desc = self.fetch_full_description(client, ad_url)

                    Listing.objects.create(
                        platform=Platform.KUFAR,
                        external_id=external_id,
                        url=ad_url,
                        title=ad.get("subject", ""),
                        description=full_desc,
                        price=price,
                        currency="BYN",
                        city=city or None,
                        seller_id=ad.get("account_id"),
                        seller_name=seller_name,
                        published_at=pub_date,
                        image_url=image_url,
                        raw_metadata={"category_id": ad.get("category")}
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

                # Ищем токен следующей страницы в ответе Куфара
                next_cursor = None
                for p_info in data.get("pagination", {}).get("pages", []):
                    if p_info.get("label") == "next":
                        next_cursor = p_info.get("token")
                        break
                if not next_cursor:
                    break
                cursor = next_cursor

        return saved_count
