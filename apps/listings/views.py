import httpx
from django.http import HttpResponse, Http404


def proxy_image(request):
    """Проксирует картинки со сторонних CDN без блокировок hotlink"""
    img_url = request.GET.get('url')
    if not img_url:
        raise Http404("URL не передан")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }
    try:
        with httpx.Client(headers=headers, timeout=10.0, follow_redirects=True) as client:
            resp = client.get(img_url)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "image/jpeg")
                return HttpResponse(resp.content, content_type=content_type)
    except Exception:
        pass

    raise Http404("Не удалось загрузить изображение")
