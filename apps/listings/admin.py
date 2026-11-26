from django.contrib import admin
from django.utils.safestring import mark_safe
from urllib.parse import quote
from .models import Listing, RiskAssessment


class RiskAssessmentInline(admin.StackedInline):
    model = RiskAssessment
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'photo_preview',
        'platform_badge',
        'title',
        'price_display',
        'seller_name',
        'risk_badge',
        'scraped_at'
    )
    list_filter = ('platform', 'scraped_at')
    search_fields = ('title', 'description', 'external_id', 'seller_name')
    readonly_fields = ('scraped_at', 'photo_preview', 'photo_detail')
    inlines = [RiskAssessmentInline]

    fields = (
        'platform',
        'external_id',
        'url',
        'title',
        'photo_detail',
        'image_url',
        'description',
        'price',
        'currency',
        'seller_id',
        'seller_name',
        'published_at',
        'raw_metadata',
        'scraped_at',
    )

    def photo_preview(self, obj):
        if obj.image_url:
            # Отдаем через наш прокси
            proxied_url = f"/proxy-image/?url={quote(obj.image_url)}"
            return mark_safe(
                f'<img src="{proxied_url}" '
                f'style="width: 55px; height: 42px; object-fit: cover; border-radius: 4px; border: 1px solid #444;" />'
            )
        return mark_safe('<span style="color:#6b7280; font-size:11px;">Нет фото</span>')
    photo_preview.short_description = "Фото"

    def photo_detail(self, obj):
        if obj.image_url:
            proxied_url = f"/proxy-image/?url={quote(obj.image_url)}"
            return mark_safe(
                f'<img src="{proxied_url}" '
                f'style="max-width: 320px; max-height: 220px; border-radius: 6px; border: 1px solid #555;" />'
            )
        return "Фото отсутствует"
    photo_detail.short_description = "Просмотр фото"

    def platform_badge(self, obj):
        colors = {'kufar': '#10b981', 'av_by': '#3b82f6', 'onliner': '#f59e0b'}
        color = colors.get(obj.platform, '#6b7280')
        return mark_safe(
            f'<span style="background:{color}; color:white; padding:3px 8px; border-radius:4px; font-weight:bold;">'
            f'{obj.get_platform_display()}</span>'
        )
    platform_badge.short_description = "Площадка"

    def price_display(self, obj):
        if obj.price is not None:
            return f"{obj.price:.2f} {obj.currency}"
        return "—"
    price_display.short_description = "Цена"

    def risk_badge(self, obj):
        if not hasattr(obj, 'risk_assessment'):
            return mark_safe('<span style="color:#9ca3af;">Не оценен</span>')
        score = obj.risk_assessment.risk_score
        color = '#10b981' if score < 0.4 else ('#f59e0b' if score < 0.7 else '#ef4444')
        return mark_safe(
            f'<span style="background:{color}; color:white; padding:3px 8px; border-radius:4px; font-weight:bold;">'
            f'{score:.2f} ({obj.risk_assessment.label})</span>'
        )
    risk_badge.short_description = "Риск"


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ('listing', 'risk_score', 'label', 'model_name', 'created_at')
