from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from performance.models import AppSettings, WeeklyPlan


class WeekService:
    @staticmethod
    def settings():
        return AppSettings.load()

    @classmethod
    def current_timezone(cls):
        return ZoneInfo(cls.settings().timezone)

    @classmethod
    def today(cls) -> date:
        return timezone.now().astimezone(cls.current_timezone()).date()

    @staticmethod
    def week_start_for(day: date, week_starts_on: int) -> date:
        offset = (day.weekday() - week_starts_on) % 7
        return day - timedelta(days=offset)

    @classmethod
    def current_week_start(cls) -> date:
        settings = cls.settings()
        return cls.week_start_for(cls.today(), settings.week_starts_on)

    @classmethod
    def days_of(cls, plan: WeeklyPlan) -> list[date]:
        return [plan.starts_on + timedelta(days=i) for i in range(7)]

    @classmethod
    def find_covering_plan(cls, day: date) -> WeeklyPlan | None:
        candidates = WeeklyPlan.objects.filter(
            starts_on__lte=day,
            starts_on__gte=day - timedelta(days=6),
        )
        for plan in candidates:
            if plan.starts_on <= day <= plan.ends_on:
                return plan
        return None

    @classmethod
    @transaction.atomic
    def ensure_plan_for(cls, day: date) -> WeeklyPlan:
        existing = cls.find_covering_plan(day)
        if existing:
            return existing
        settings = cls.settings()
        starts_on = cls.week_start_for(day, settings.week_starts_on)
        overlap = WeeklyPlan.objects.filter(
            starts_on__lte=starts_on + timedelta(days=6),
            starts_on__gte=starts_on - timedelta(days=6),
        )
        for plan in overlap:
            if ranges_overlap(
                plan.starts_on,
                plan.ends_on,
                starts_on,
                starts_on + timedelta(days=6),
            ):
                raise ValueError(
                    "This date overlaps an existing week. Open that week instead of creating another."
                )
        plan, _ = WeeklyPlan.objects.get_or_create(
            starts_on=starts_on,
            defaults={"week_starts_on": settings.week_starts_on},
        )
        return plan

    @classmethod
    def local_now(cls) -> datetime:
        return timezone.now().astimezone(cls.current_timezone())


def ranges_overlap(a_start, a_end, b_start, b_end) -> bool:
    return a_start <= b_end and b_start <= a_end
