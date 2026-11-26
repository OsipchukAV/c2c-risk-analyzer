from django.contrib import admin
from django.urls import path
from apps.listings.views import proxy_image  # импортируем наш прокси

urlpatterns = [
    path('admin/', admin.site.urls),
    path('proxy-image/', proxy_image, name='proxy-image'), # <--- вот этот маршрут
]
