from collections import defaultdict
from datetime import date

from django.db.models import Prefetch, Sum

from performance.models import PlannedSession, TimeEntry, TimeEntrySource, WeeklyGoal, WeeklyPlan
from performance.services.weeks import WeekService


def format_minutes(minutes: int) -> str:
    hours, mins = divmod(max(0, minutes), 60)
    if hours and mins:
        return f"{hours}h {mins:02d}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


class ReportingService:
    @classmethod
    def week_report(cls, plan: WeeklyPlan) -> dict:
        goals = list(
            WeeklyGoal.objects.filter(plan=plan)
            .select_related("activity", "category")
            .prefetch_related("sessions")
        )
        entries = list(
            TimeEntry.objects.filter(weekly_plan=plan).select_related("activity", "weekly_goal", "category")
        )
        actual_by_goal = defaultdict(int)
        actual_by_day = defaultdict(int)
        source_totals = {TimeEntrySource.MANUAL: 0, TimeEntrySource.TIMER: 0}
        for entry in entries:
            actual_by_day[entry.tracked_date] += entry.duration_minutes
            source_totals[entry.source] += entry.duration_minutes
            if entry.weekly_goal_id:
                actual_by_goal[entry.weekly_goal_id] += entry.duration_minutes

        goal_rows = []
        completed = partial = none = 0
        target_total = 0
        for goal in goals:
            actual = actual_by_goal.get(goal.id, 0)
            target_total += goal.target_minutes
            pct = (actual / goal.target_minutes) * 100 if goal.target_minutes else 0
            if actual >= goal.target_minutes:
                status = "completed"
                completed += 1
            elif actual > 0:
                status = "partial"
                partial += 1
            else:
                status = "none"
                none += 1
            goal_rows.append(
                {
                    "goal": goal,
                    "actual_minutes": actual,
                    "target_minutes": goal.target_minutes,
                    "target_hours": goal.target_minutes // 60,
                    "target_mins": goal.target_minutes % 60,
                    "remaining_minutes": max(0, goal.target_minutes - actual),
                    "achievement": pct,
                    "status": status,
                    "allocated_minutes": sum(s.duration_minutes for s in goal.sessions.all()),
                }
            )

        actual_total = sum(source_totals.values())
        achievement = (actual_total / target_total) * 100 if target_total else 0
        days = WeekService.days_of(plan)
        daily = [
            {
                "date": day,
                "actual_minutes": actual_by_day.get(day, 0),
            }
            for day in days
        ]
        return {
            "plan": plan,
            "days": days,
            "goals": goal_rows,
            "entries": entries,
            "target_minutes": target_total,
            "actual_minutes": actual_total,
            "remaining_minutes": max(0, target_total - actual_total),
            "achievement": achievement,
            "completed_count": completed,
            "partial_count": partial,
            "none_count": none,
            "active_count": partial + none,
            "manual_minutes": source_totals[TimeEntrySource.MANUAL],
            "timer_minutes": source_totals[TimeEntrySource.TIMER],
            "daily": daily,
        }

    @classmethod
    def day_view(cls, day: date) -> dict:
        plan = WeekService.ensure_plan_for(day)
        sessions = list(
            PlannedSession.objects.filter(planned_date=day)
            .select_related("goal", "goal__activity")
            .order_by("goal__title")
        )
        entries = list(
            TimeEntry.objects.filter(tracked_date=day).select_related("activity", "weekly_goal")
        )
        return {
            "plan": plan,
            "date": day,
            "sessions": sessions,
            "entries": entries,
            "total_minutes": sum(e.duration_minutes for e in entries),
            "planned_minutes": sum(s.duration_minutes for s in sessions),
        }

    @staticmethod
    def history():
        return WeeklyPlan.objects.annotate(
            actual_minutes=Sum("time_entries__duration_minutes"),
            target_minutes=Sum("goals__target_minutes"),
        )
