import re
from datetime import datetime, timedelta
from django.utils import timezone

MONTHS_RU = {
    'январ': 1, 'феврал': 2, 'март': 3, 'апрел': 4,
    'мая': 5, 'май': 5, 'июн': 6, 'июл': 7, 'август': 8,
    'сентябр': 9, 'октябр': 10, 'ноябр': 11, 'декабр': 12
}


def parse_russian_date(raw_str: str | None) -> datetime | None:
    """
    Преобразует текстовые и относительные даты (av.by, Onliner)
    в валидный timezone-aware datetime для сохранения в PostgreSQL.
    """
    if not raw_str:
        return None

    text = raw_str.lower().strip()
    text = re.sub(r'^up!\s*', '', text).strip()
    now = timezone.now()

    if any(w in text for w in ['только что', 'менее минуты', 'секунд']):
        return now

    if 'минут' in text:
        match = re.search(r'(\d+)', text)
        mins = int(match.group(1)) if match else 1
        return now - timedelta(minutes=mins)

    if 'час' in text:
        match = re.search(r'(\d+)', text)
        hours = int(match.group(1)) if match else 1
        return now - timedelta(hours=hours)

    if 'дн' in text or 'ден' in text or 'сут' in text:
        match = re.search(r'(\d+)', text)
        days = int(match.group(1)) if match else 1
        return now - timedelta(days=days)

    if 'месяц' in text:
        match = re.search(r'(\d+)', text)
        months = int(match.group(1)) if match else 1
        return now - timedelta(days=30 * months)

    if 'год' in text or 'лет' in text:
        match = re.search(r'(\d+)', text)
        years = int(match.group(1)) if match else 1
        return now - timedelta(days=365 * years)

    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if 'сегодня' in text:
        dt = now
        if time_match:
            dt = dt.replace(hour=int(time_match.group(1)), minute=int(time_match.group(2)), second=0, microsecond=0)
        return dt

    if 'вчера' in text:
        dt = now - timedelta(days=1)
        if time_match:
            dt = dt.replace(hour=int(time_match.group(1)), minute=int(time_match.group(2)), second=0, microsecond=0)
        return dt

    day_match = re.search(r'(\d{1,2})\s+([а-я]+)(?:\s+(\d{4}))?', text)
    if day_match:
        day = int(day_match.group(1))
        month_str = day_match.group(2)
        year = int(day_match.group(3)) if day_match.group(3) else now.year

        month = None
        for prefix, m_num in MONTHS_RU.items():
            if month_str.startswith(prefix):
                month = m_num
                break

        if month:
            try:
                dt = now.replace(year=year, month=month, day=day, hour=12, minute=0, second=0, microsecond=0)
                if not day_match.group(3) and dt > now + timedelta(days=1):
                    dt = dt.replace(year=year - 1)
                return dt
            except ValueError:
                pass

    return None
