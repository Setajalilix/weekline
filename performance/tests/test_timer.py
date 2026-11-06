from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from performance.models import AppSettings, TimeEntry, TimerStatus
from performance.services.planning import PlanningService
from performance.services.timer import TimerService
from performance.services.weeks import WeekService


class TimerLifecycleTests(TestCase):
    def setUp(self):
        AppSettings.load()
        self.plan = WeekService.ensure_plan_for(WeekService.today())
        self.goal = PlanningService.add_goal(self.plan, activity_name="Deep work", target_minutes=120)
        self.activity = self.goal.activity

    def test_pause_excludes_paused_gap(self):
        t0 = timezone.now()
        with patch("performance.services.timer.timezone.now", return_value=t0):
            session = TimerService.start(self.activity, self.goal)
        t1 = t0 + timedelta(minutes=10)
        with patch("performance.services.timer.timezone.now", return_value=t1):
            session = TimerService.pause()
        self.assertEqual(session.status, TimerStatus.PAUSED)
        self.assertEqual(session.accumulated_seconds, 600)
        t2 = t1 + timedelta(hours=2)
        with patch("performance.services.timer.timezone.now", return_value=t2):
            elapsed = TimerService.elapsed_seconds(session, t2)
        self.assertEqual(elapsed, 600)
        with patch("performance.services.timer.timezone.now", return_value=t2):
            session = TimerService.resume()
        t3 = t2 + timedelta(minutes=5)
        with patch("performance.services.timer.timezone.now", return_value=t3):
            self.assertEqual(TimerService.elapsed_seconds(session, t3), 900)

    def test_finish_twice_creates_one_entry(self):
        t0 = timezone.now()
        with patch("performance.services.timer.timezone.now", return_value=t0):
            TimerService.start(self.activity, self.goal)
        t1 = t0 + timedelta(minutes=25)
        with patch("performance.services.timer.timezone.now", return_value=t1):
            first = TimerService.finish(25)
            second = TimerService.finish(40)
        self.assertEqual(first.id, second.id)
        self.assertEqual(TimeEntry.objects.count(), 1)
        self.assertEqual(first.duration_minutes, 25)
        self.assertEqual(first.source, "timer")
        self.assertIsNotNone(first.starts_at)
        self.assertIsNotNone(first.ends_at)

    def test_finish_rejects_under_five_minutes(self):
        TimerService.start(self.activity, self.goal)
        with self.assertRaises(ValueError):
            TimerService.finish(4)
        self.assertEqual(TimeEntry.objects.count(), 0)

    def test_discard_creates_no_entry(self):
        TimerService.start(self.activity, self.goal)
        TimerService.reset()
        self.assertEqual(TimeEntry.objects.count(), 0)
        self.assertIsNone(TimerService.active())

    def test_elapsed_uses_timestamps_not_a_counter(self):
        t0 = timezone.now()
        with patch("performance.services.timer.timezone.now", return_value=t0):
            session = TimerService.start(self.activity)
        later = t0 + timedelta(seconds=87)
        self.assertEqual(TimerService.elapsed_seconds(session, later), 87)
