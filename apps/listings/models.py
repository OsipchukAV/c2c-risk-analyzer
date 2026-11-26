from django.db import models


class Platform(models.TextChoices):
    KUFAR = 'kufar', 'Kufar.by'
    AV_BY = 'av_by', 'av.by'
    ONLINER = 'onliner', 'Onliner Барахолка'


class Listing(models.Model):
    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
        db_index=True,
        verbose_name="Площадка"
    )
    external_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="ID на площадке"
    )
    url = models.URLField(max_length=1000, verbose_name="Ссылка")
    title = models.CharField(max_length=500, verbose_name="Заголовок")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Цена"
    )
    currency = models.CharField(max_length=10, default="BYN", verbose_name="Валюта")

    # Город как отдельное индексированное поле
    city = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name="Город")

    image_url = models.URLField(max_length=1000, blank=True, null=True, verbose_name="Главное фото")

    seller_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID продавца")
    seller_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Имя продавца")

    published_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата публикации")
    scraped_at = models.DateTimeField(auto_now_add=True, verbose_name="Спарсено в")

    # Дополнительные специфичные параметры
    raw_metadata = models.JSONField(default=dict, blank=True, verbose_name="Метаданные")

    class Meta:
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"
        unique_together = ('platform', 'external_id')
        indexes = [
            models.Index(fields=['platform', 'external_id']),
            models.Index(fields=['city']),
            models.Index(fields=['scraped_at']),
        ]

    def __str__(self):
        return f"[{self.platform}] {self.title[:50]}"


class RiskAssessment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает проверки'
        PROCESSING = 'processing', 'Анализируется'
        COMPLETED = 'completed', 'Завершено'
        FAILED = 'failed', 'Ошибка'

    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name='risk_assessment',
        verbose_name="Объявление"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name="Статус"
    )

    model_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Модель")

    # 0.0 — безопасно, 1.0 — критический риск/аномалия
    risk_score = models.FloatField(blank=True, null=True, db_index=True, verbose_name="Оценка риска (0..1)")
    label = models.CharField(max_length=100, blank=True, null=True, verbose_name="Класс риска")

    # Логика решения LLM (Chain of Thought / обоснование)
    explanation = models.TextField(blank=True, null=True, verbose_name="Объяснение модели")

    # Извлечённые признаки (например: {"fake_warranty": true, "telegram_redirect": true})
    markers = models.JSONField(default=dict, blank=True, verbose_name="Маркеры аномалий")

    # Метрики для курсовой (замеры производительности локальной LLM)
    inference_time_ms = models.IntegerField(blank=True, null=True, verbose_name="Время инференса (мс)")
    raw_response = models.TextField(blank=True, null=True, verbose_name="Сырой ответ LLM")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата оценки")

    class Meta:
        verbose_name = "Оценка риска"
        verbose_name_plural = "Оценки рисков"

    def __str__(self):
        score_str = f"{self.risk_score:.2f}" if self.risk_score is not None else "нет"
        return f"Риск [{score_str}] для #{self.listing_id}"
