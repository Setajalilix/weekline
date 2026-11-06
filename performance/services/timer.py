from datetime import time, timedelta

from django.db import transaction
from django.utils import timezone

from performance.models import (
    Activity,
    TimeEntry,
    TimeEntrySource,
    TimerSession,
    TimerStatus,
    WeeklyGoal,
)
from performance.services.weeks import WeekService


class TimerService:
    @classmethod
    def active(cls) -> TimerSession | None:
        return (
            TimerSession.objects.select_related("activity", "weekly_goal")
            .filter(status__in=[TimerStatus.RUNNING, TimerStatus.PAUSED])
            .first()
        )

    @classmethod
    def elapsed_seconds(cls, session: TimerSession, now=None) -> int:
        now = now or timezone.now()
        total = session.accumulated_seconds
        if session.status == TimerStatus.RUNNING and session.segment_started_at:
            total += max(0, int((now - session.segment_started_at).total_seconds()))
        return total

    @classmethod
    @transaction.atomic
    def start(cls, activity: Activity, weekly_goal: WeeklyGoal | None = None) -> TimerSession:
        existing = cls.active()
        if existing:
            raise ValueError("Finish or reset the current session before starting another.")
        now = timezone.now()
        plan = WeekService.ensure_plan_for(WeekService.today())
        if weekly_goal and weekly_goal.plan_id != plan.id:
            weekly_goal = None
        return TimerSession.objects.create(
            activity=activity,
            weekly_goal=weekly_goal,
            weekly_plan=plan,
            activity_title=activity.name,
            status=TimerStatus.RUNNING,
            started_at=now,
            segment_started_at=now,
            paused_at=None,
            accumulated_seconds=0,
        )

    @classmethod
    @transaction.atomic
    def pause(cls) -> TimerSession:
        session = cls._lock_active()
        if session.status != TimerStatus.RUNNING:
            raise ValueError("Only a running session can be paused.")
        now = timezone.now()
        session.accumulated_seconds = cls.elapsed_seconds(session, now)
        session.status = TimerStatus.PAUSED
        session.paused_at = now
        session.segment_started_at = None
        session.save()
        return session

    @classmethod
    @transaction.atomic
    def resume(cls) -> TimerSession:
        session = cls._lock_active()
        if session.status != TimerStatus.PAUSED:
            raise ValueError("Only a paused session can be resumed.")
        now = timezone.now()
        session.status = TimerStatus.RUNNING
        session.segment_started_at = now
        session.paused_at = None
        session.save()
        return session

    @classmethod
    @transaction.atomic
    def reset(cls) -> TimerSession:
        session = cls._lock_active()
        session.status = TimerStatus.DISCARDED
        session.finished_at = timezone.now()
        session.segment_started_at = None
        session.save()
        return session

    @classmethod
    def suggested_minutes(cls, session: TimerSession) -> int:
        seconds = cls.elapsed_seconds(session)
        minutes = max(1, round(seconds / 60)) if seconds > 0 else 1
        return minutes

    @classmethod
    @transaction.atomic
    def finish(cls, duration_minutes: int, note: str = "", tracked_date=None) -> TimeEntry:
        if duration_minutes < 1:
            raise ValueError("Duration must be at least 1 minute.")
        session = (
            TimerSession.objects.select_for_update(of=("self",))
            .select_related("activity", "weekly_goal")
            .filter(status__in=[TimerStatus.RUNNING, TimerStatus.PAUSED])
            .first()
        )
        if session is None:
            latest = (
                TimerSession.objects.select_for_update(of=("self",))
                .filter(status=TimerStatus.FINISHED)
                .order_by("-finished_at")
                .first()
            )
            existing = TimeEntry.objects.filter(timer_session=latest).first() if latest else None
            if existing:
                return existing
            raise ValueError("There is no session to finish.")
        existing = TimeEntry.objects.filter(timer_session=session).first()
        if existing:
            return existing

        now = timezone.now()
        if session.status == TimerStatus.RUNNING:
            session.accumulated_seconds = cls.elapsed_seconds(session, now)
            session.segment_started_at = None
        tracked_date = tracked_date or WeekService.today()
        plan = WeekService.ensure_plan_for(tracked_date)
        weekly_goal = session.weekly_goal
        if weekly_goal and weekly_goal.plan_id != plan.id:
            weekly_goal = None
        local_start = session.started_at.astimezone(WeekService.current_timezone())
        start_minutes = local_start.hour * 60 + local_start.minute
        end_minutes = start_minutes + duration_minutes
        starts_at = time(local_start.hour, local_start.minute)
        ends_at = time(min(23, end_minutes // 60), end_minutes % 60) if end_minutes < 24 * 60 else time(23, 59)
        entry = TimeEntry.objects.create(
            weekly_plan=plan,
            weekly_goal=weekly_goal,
            activity=session.activity,
            activity_title=session.activity_title,
            category=weekly_goal.category if weekly_goal else session.activity.category,
            tracked_date=tracked_date,
            starts_at=starts_at,
            ends_at=ends_at,
            duration_minutes=duration_minutes,
            source=TimeEntrySource.TIMER,
            note=note,
            timer_session=session,
        )
        session.status = TimerStatus.FINISHED
        session.finished_at = now
        session.paused_at = None
        session.save()
        return entry

    @classmethod
    def _lock_active(cls) -> TimerSession:
        session = (
            TimerSession.objects.select_for_update()
            .filter(status__in=[TimerStatus.RUNNING, TimerStatus.PAUSED])
            .first()
        )
        if session is None:
            raise ValueError("There is no active timer session.")
        return session

    @classmethod
    def client_state(cls, session: TimerSession | None) -> dict:
        if session is None:
            return {"status": "idle", "elapsed_seconds": 0}
        now = timezone.now()
        return {
            "status": session.status,
            "elapsed_seconds": cls.elapsed_seconds(session, now),
            "accumulated_seconds": session.accumulated_seconds,
            "segment_started_at": session.segment_started_at.isoformat() if session.segment_started_at else None,
            "server_now": now.isoformat(),
            "activity": session.activity_title,
        }
