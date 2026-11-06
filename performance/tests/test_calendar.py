from datetime import date, time

from django.test import TestCase

from performance.models import AppSettings, TimeEntry, WeeklyPlan
from performance.services.calendar import CalendarService
from performance.services.entries import TimeEntryService
from performance.services.planning import PlanningService


class CalendarLayoutTests(TestCase):
    def setUp(self):
        AppSettings.load()
        self.plan = WeeklyPlan.objects.create(starts_on=date(2026, 10, 31), week_starts_on=5)
        self.goal = PlanningService.add_goal(self.plan, activity_name="Workout", target_minutes=180, color="#A9C9B2")

    def test_timed_entry_keeps_start_and_finish(self):
        TimeEntryService.log_manual(
            activity_name="Workout",
            tracked_date=date(2026, 11, 2),
            duration_minutes=90,
            weekly_goal=self.goal,
            starts_at=time(6, 0),
            ends_at=time(7, 30),
        )
        view = CalendarService.week_view(self.plan)
        monday = next(day for day in view["days"] if day.date == date(2026, 11, 2))
        self.assertEqual(len(monday.events), 1)
        event = monday.events[0]
        self.assertEqual(event.start, 6 * 60)
        self.assertEqual(event.end, 7 * 60 + 30)
        self.assertEqual(event.title, "Workout")
        self.assertEqual(event.color, "#A9C9B2")

    def test_untimed_entries_stack_from_morning(self):
        TimeEntryService.log_manual(
            activity_name="Read",
            tracked_date=date(2026, 11, 3),
            duration_minutes=60,
        )
        TimeEntryService.log_manual(
            activity_name="Walk",
            tracked_date=date(2026, 11, 3),
            duration_minutes=30,
        )
        view = CalendarService.week_view(self.plan)
        tuesday = next(day for day in view["days"] if day.date == date(2026, 11, 3))
        self.assertEqual([event.start for event in tuesday.events], [8 * 60, 9 * 60])

    def test_overlapping_events_get_columns(self):
        TimeEntryService.log_manual(
            activity_name="School",
            tracked_date=date(2026, 11, 4),
            duration_minutes=180,
            starts_at=time(9, 0),
            ends_at=time(12, 0),
        )
        TimeEntryService.log_manual(
            activity_name="Calligraphy",
            tracked_date=date(2026, 11, 4),
            duration_minutes=60,
            starts_at=time(9, 30),
            ends_at=time(10, 30),
        )
        view = CalendarService.week_view(self.plan)
        wednesday = next(day for day in view["days"] if day.date == date(2026, 11, 4))
        cols = {event.title: (event.col, event.cols) for event in wednesday.events}
        self.assertEqual(cols["School"][1], 2)
        self.assertEqual(cols["Calligraphy"][1], 2)
        self.assertNotEqual(cols["School"][0], cols["Calligraphy"][0])

    def test_planned_sessions_appear_as_all_day(self):
        PlanningService.set_session(self.goal, date(2026, 11, 2), 60)
        view = CalendarService.week_view(self.plan)
        monday = next(day for day in view["days"] if day.date == date(2026, 11, 2))
        self.assertEqual(monday.all_day[0]["title"], "Workout")

    def test_day_runs_from_hour_1_to_24(self):
        view = CalendarService.week_view(self.plan)
        self.assertEqual(view["hours"][0], 1)
        self.assertEqual(view["hours"][-1], 24)
        self.assertEqual(len(view["hours"]), 24)

    def test_opening_a_week_without_a_plan_creates_it(self):
        from django.contrib.auth import get_user_model
        from django.test import Client

        from performance.models import WeeklyPlan

        user = get_user_model().objects.create_user("lilu", password="51525555")
        client = Client()
        client.force_login(user)
        self.assertFalse(WeeklyPlan.objects.filter(starts_on=date(2026, 11, 7)).exists())
        response = client.get("/calendar/?week=2026-11-07", HTTP_HOST="127.0.0.1")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(WeeklyPlan.objects.filter(starts_on=date(2026, 11, 7)).exists())
