from datetime import date

from django.test import TestCase

from performance.models import AppSettings, PlannedSession, WeeklyGoal, WeeklyPlan
from performance.services.planning import PlanningService


class PlanningTests(TestCase):
    def setUp(self):
        AppSettings.load()
        self.plan = WeeklyPlan.objects.create(starts_on=date(2026, 10, 31), week_starts_on=5)
        self.goal = PlanningService.add_goal(self.plan, activity_name="Python", target_minutes=240)

    def test_allocating_sessions_does_not_change_target(self):
        PlanningService.set_session(self.goal, date(2026, 10, 31), 60)
        PlanningService.set_session(self.goal, date(2026, 11, 2), 90)
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.target_minutes, 240)
        self.assertEqual(PlannedSession.objects.filter(goal=self.goal).count(), 2)

    def test_moving_session_does_not_change_target(self):
        session = PlanningService.set_session(self.goal, date(2026, 10, 31), 60)
        PlanningService.move_session(session, date(2026, 11, 3))
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.target_minutes, 240)
        session.refresh_from_db()
        self.assertEqual(session.planned_date, date(2026, 11, 3))

    def test_cannot_move_onto_occupied_day(self):
        first = PlanningService.set_session(self.goal, date(2026, 10, 31), 60)
        PlanningService.set_session(self.goal, date(2026, 11, 2), 90)
        with self.assertRaises(ValueError):
            PlanningService.move_session(first, date(2026, 11, 2))

    def test_goal_without_planned_days(self):
        self.assertEqual(self.goal.sessions.count(), 0)

    def test_reuse_creates_new_goal_on_new_week(self):
        later = WeeklyPlan.objects.create(starts_on=date(2026, 11, 7), week_starts_on=5)
        reused = PlanningService.reuse_goal(self.goal, later)
        self.assertEqual(reused.activity_id, self.goal.activity_id)
        self.assertNotEqual(reused.id, self.goal.id)
        self.assertEqual(later.goals.count(), 1)
        self.assertEqual(self.plan.goals.count(), 1)

    def test_delete_goal_removes_sessions_keeps_plan(self):
        PlanningService.set_session(self.goal, date(2026, 10, 31), 60)
        PlanningService.delete_goal(self.goal)
        self.assertFalse(WeeklyGoal.objects.filter(pk=self.goal.pk).exists())
        self.assertEqual(PlannedSession.objects.count(), 0)
        self.assertTrue(WeeklyPlan.objects.filter(pk=self.plan.pk).exists())
