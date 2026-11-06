from datetime import date

from django.test import TestCase

from performance.models import AppSettings, TimeEntrySource, WeeklyPlan
from performance.services.entries import TimeEntryService
from performance.services.planning import PlanningService
from performance.services.reporting import ReportingService


class EntryAndReportTests(TestCase):
    def setUp(self):
        AppSettings.load()
        self.plan = WeeklyPlan.objects.create(starts_on=date(2026, 10, 31), week_starts_on=5)
        self.goal = PlanningService.add_goal(self.plan, activity_name="Python", target_minutes=120)

    def test_manual_entries_count_toward_achievement(self):
        TimeEntryService.log_manual(
            activity_name="Python",
            tracked_date=date(2026, 11, 2),
            duration_minutes=90,
            weekly_goal=self.goal,
        )
        report = ReportingService.week_report(self.plan)
        self.assertEqual(report["actual_minutes"], 90)
        self.assertEqual(report["achievement"], 75)

    def test_multiple_entries_same_day(self):
        TimeEntryService.log_manual(
            activity_name="Python",
            tracked_date=date(2026, 11, 2),
            duration_minutes=30,
            weekly_goal=self.goal,
        )
        TimeEntryService.log_manual(
            activity_name="Python",
            tracked_date=date(2026, 11, 2),
            duration_minutes=45,
            weekly_goal=self.goal,
        )
        report = ReportingService.week_report(self.plan)
        self.assertEqual(report["actual_minutes"], 75)

    def test_unplanned_activity_counts(self):
        TimeEntryService.log_manual(
            activity_name="Walk",
            tracked_date=date(2026, 11, 3),
            duration_minutes=40,
        )
        report = ReportingService.week_report(self.plan)
        self.assertEqual(report["actual_minutes"], 40)
        self.assertEqual(report["goals"][0]["actual_minutes"], 0)

    def test_achievement_not_capped(self):
        TimeEntryService.log_manual(
            activity_name="Python",
            tracked_date=date(2026, 11, 2),
            duration_minutes=180,
            weekly_goal=self.goal,
        )
        report = ReportingService.week_report(self.plan)
        self.assertEqual(report["achievement"], 150)
        self.assertEqual(report["goals"][0]["status"], "completed")

    def test_manual_and_timer_sources_are_both_included(self):
        from django.utils import timezone

        from performance.models import Activity, TimeEntry, TimerSession, TimerStatus

        TimeEntryService.log_manual(
            activity_name="Python",
            tracked_date=date(2026, 11, 2),
            duration_minutes=30,
            weekly_goal=self.goal,
        )
        activity = self.goal.activity
        session = TimerSession.objects.create(
            activity=activity,
            weekly_goal=self.goal,
            weekly_plan=self.plan,
            activity_title="Python",
            status=TimerStatus.FINISHED,
            started_at=timezone.now(),
            accumulated_seconds=3600,
            finished_at=timezone.now(),
        )
        TimeEntry.objects.create(
            weekly_plan=self.plan,
            weekly_goal=self.goal,
            activity=activity,
            activity_title="Python",
            tracked_date=date(2026, 11, 2),
            duration_minutes=60,
            source=TimeEntrySource.TIMER,
            timer_session=session,
        )
        report = ReportingService.week_report(self.plan)
        self.assertEqual(report["actual_minutes"], 90)
        self.assertEqual(report["manual_minutes"], 30)
        self.assertEqual(report["timer_minutes"], 60)


class LogEntryDayUrlTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        AppSettings.load()
        self.user = get_user_model().objects.create_user("lilu", password="51525555")
        self.client.force_login(self.user)

    def test_human_date_path_redirects_to_log_form(self):
        response = self.client.get("/entries/Nov. 8, 2026/", HTTP_HOST="127.0.0.1")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/entries/?date=2026-11-08")
