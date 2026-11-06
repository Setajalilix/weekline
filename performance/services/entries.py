from datetime import date, time

from django.db import transaction

from performance.models import Activity, TimeEntry, TimeEntrySource, WeeklyGoal
from performance.services.planning import PlanningService
from performance.services.weeks import WeekService


class TimeEntryService:
    @classmethod
    @transaction.atomic
    def log_manual(
        cls,
        *,
        activity_name: str,
        tracked_date: date,
        duration_minutes: int,
        note: str = "",
        weekly_goal: WeeklyGoal | None = None,
        category=None,
        starts_at: time | None = None,
        ends_at: time | None = None,
    ) -> TimeEntry:
        if duration_minutes < 1:
            raise ValueError("Duration must be at least 1 minute.")
        plan = WeekService.ensure_plan_for(tracked_date)
        if weekly_goal and weekly_goal.plan_id != plan.id:
            raise ValueError("That goal belongs to a different week.")
        activity = weekly_goal.activity if weekly_goal else PlanningService.get_or_create_activity(
            activity_name, category
        )
        return TimeEntry.objects.create(
            weekly_plan=plan,
            weekly_goal=weekly_goal,
            activity=activity,
            activity_title=activity.name,
            category=category or (weekly_goal.category if weekly_goal else activity.category),
            tracked_date=tracked_date,
            starts_at=starts_at,
            ends_at=ends_at,
            duration_minutes=duration_minutes,
            source=TimeEntrySource.MANUAL,
            note=note,
        )

    @staticmethod
    def update_entry(
        entry: TimeEntry,
        *,
        duration_minutes: int,
        note: str,
        tracked_date: date,
        weekly_goal=None,
        starts_at: time | None = None,
        ends_at: time | None = None,
    ):
        if duration_minutes < 1:
            raise ValueError("Duration must be at least 1 minute.")
        plan = WeekService.ensure_plan_for(tracked_date)
        if weekly_goal and weekly_goal.plan_id != plan.id:
            raise ValueError("That goal belongs to a different week.")
        entry.duration_minutes = duration_minutes
        entry.note = note
        entry.tracked_date = tracked_date
        entry.weekly_plan = plan
        entry.weekly_goal = weekly_goal
        entry.starts_at = starts_at
        entry.ends_at = ends_at
        entry.save()
        return entry

    @staticmethod
    def delete_entry(entry: TimeEntry):
        entry.delete()
