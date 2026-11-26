import httpx
from selectolax.lexbor import LexborHTMLParser

TEST_URL = "https://cars.av.by/volkswagen/passat/132360516"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

response = httpx.get(TEST_URL, headers=HEADERS, timeout=15.0)
tree = LexborHTMLParser(response.text)

# 1. Проверяем главное фото через OpenGraph (это самый надежный способ)
og_image = tree.css_first('meta[property="og:image"]')
if og_image:
    print("1. Главное фото (через OpenGraph):", og_image.attributes.get("content"))

# Проверяем фото из галереи
for img in tree.css("img"):
    for attr in ["data-src", "src", "data-original"]:
        val = img.attributes.get(attr, "")
        if "av.by" in val and "base64" not in val and any(ext in val for ext in [".jpg", ".jpeg", ".webp"]):
            print("   Фото из галереи:", val)
            break
    if og_image:
        break

# 2. Ищем реальный текст от продавца (комментарий)
print("\n2. Поиск комментария продавца:")
# Проверяем все блоки, содержащие слово 'comment'
found_comment = False
for node in tree.css('[class*="comment"], [class*="card__comment"]'):
    text = node.text(strip=True)
    if len(text) > 30 and "Комментарий" not in text[:15]:
        print(f"   Селектор [{node.attributes.get('class')}]:")
        print("   Текст:", text[:250], "...\n")
        found_comment = True
        break

if not found_comment:
    # Если класс другой, ищем блок после заголовка 'Описание' или 'Комментарий продавца'
    for heading in tree.css("h2, h3, h4"):
        if any(w in heading.text() for w in ["Описание", "Комментарий", "Дополнительно"]):
            parent = heading.parent
            if parent:
                print("   Текст под заголовком:", parent.text(strip=True)[:250])
                break

# 3. Имя продавца / контакты
print("3. Продавец:")
for node in tree.css('[class*="seller"], [class*="person"]'):
    text = node.text(strip=True)
    if text and len(text) < 40 and not any(w in text for w in ["Написать", "Показать", "звон"]):
        print(f"   [{node.attributes.get('class')}] -> {text}")
