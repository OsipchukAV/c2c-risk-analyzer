import json
import httpx
from selectolax.lexbor import LexborHTMLParser

URL = "https://www.kufar.by/item/1096619579"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

response = httpx.get(URL, headers=HEADERS, timeout=10.0, follow_redirects=True)
print("Статус страницы Куфара:", response.status_code)

tree = LexborHTMLParser(response.text)

# Вариант А: Ищем в __NEXT_DATA__
script = tree.css_first("script#__NEXT_DATA__")
if script:
    try:
        data = json.loads(script.text())
        ad = data.get("props", {}).get("pageProps", {}).get("ad", {})
        if ad and "body" in ad:
            print("\nНайдено описание через __NEXT_DATA__:")
            print(ad.get("body"))
    except Exception as e:
        print("Ошибка разбора JSON:", e)

# Вариант Б: Ищем в HTML тегах
desc_node = tree.css_first('[itemprop="description"]') or tree.css_first('[class*="description"]')
if desc_node and len(desc_node.text(strip=True)) > 10:
    print("\nНайдено описание через HTML-селектор:")
    print(desc_node.text(strip=True))
