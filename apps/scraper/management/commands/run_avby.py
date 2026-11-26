from django.core.management.base import BaseCommand
from apps.scraper.services.av_by import AvByScraper

class Command(BaseCommand):
    def handle(self, *args, **options):
        count = AvByScraper().scrape_new(target_count=20)
        self.stdout.write(self.style.SUCCESS(f"av.by: сохранено {count} новых"))
