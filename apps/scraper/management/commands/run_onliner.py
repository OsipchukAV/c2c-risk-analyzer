from django.core.management.base import BaseCommand
from apps.scraper.services.onliner import OnlinerScraper

class Command(BaseCommand):
    def handle(self, *args, **options):
        count = OnlinerScraper().scrape_new(target_count=20)
        self.stdout.write(self.style.SUCCESS(f"Onliner: сохранено {count} новых"))
