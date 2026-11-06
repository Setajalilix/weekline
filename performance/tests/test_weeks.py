from datetime import date, timedelta

from django.test import TestCase

from performance.models import AppSettings, WeeklyPlan
from performance.services.weeks import WeekService


class WeekServiceTests(TestCase):
    def setUp(self):
        AppSettings.load()

    def test_saturday_week_start(self):
        # 2026-11-06 is a Friday.
        start = WeekService.week_start_for(date(2026, 11, 6), 5)
        self.assertEqual(start, date(2026, 10, 31))
        self.assertEqual(start.weekday(), 5)

    def test_monday_week_start(self):
        start = WeekService.week_start_for(date(2026, 11, 6), 0)
        self.assertEqual(start, date(2026, 11, 2))
        self.assertEqual(start.weekday(), 0)

    def test_existing_plan_keeps_stored_range(self):
        plan = WeeklyPlan.objects.create(starts_on=date(2026, 10, 31), week_starts_on=5)
        AppSettings.objects.filter(pk=1).update(week_starts_on=0)
        found = WeekService.ensure_plan_for(date(2026, 11, 4))
        self.assertEqual(found.id, plan.id)
        self.assertEqual(found.starts_on, date(2026, 10, 31))
        self.assertEqual(found.ends_on, date(2026, 11, 6))

    def test_new_week_does_not_copy_goals(self):
        from performance.services.planning import PlanningService

        old = WeeklyPlan.objects.create(starts_on=date(2026, 10, 24), week_starts_on=5)
        PlanningService.add_goal(old, activity_name="Python", target_minutes=240)
        new = WeekService.ensure_plan_for(date(2026, 11, 4))
        self.assertEqual(new.goals.count(), 0)
        self.assertEqual(old.goals.count(), 1)
