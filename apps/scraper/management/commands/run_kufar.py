from django.core.management.base import BaseCommand
from apps.scraper.services.kufar import KufarScraper

class Command(BaseCommand):
    def handle(self, *args, **options):
        count = KufarScraper().scrape_new(target_count=20)
        self.stdout.write(self.style.SUCCESS(f"Kufar: сохранено {count} новых"))
