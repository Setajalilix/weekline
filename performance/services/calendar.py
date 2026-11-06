from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, time, timedelta

from performance.models import Category, PlannedSession, TimeEntry, Weekday, WeeklyPlan
from performance.services.weeks import WeekService

HOUR_START = 1
HOUR_COUNT = 24
UNTIMED_START = 8 * 60
DAY_MINUTES = HOUR_COUNT * 60
ORIGIN_MINUTES = HOUR_START * 60


def minutes_of(value: time | None) -> int | None:
    if value is None:
        return None
    return value.hour * 60 + value.minute


def time_from_minutes(total: int) -> time:
    total = max(0, min(24 * 60, total))
    if total >= 24 * 60:
        return time(23, 59)
    return time(total // 60, total % 60)


def add_minutes(start: time, duration: int) -> time:
    return time_from_minutes(minutes_of(start) + duration)


@dataclass
class CalendarEvent:
    title: str
    color: str
    start: int
    end: int
    href: str
    kind: str
    time_label: str
    col: int = 0
    cols: int = 1

    @property
    def style(self) -> str:
        top = max(0, (self.start - ORIGIN_MINUTES) / DAY_MINUTES * 100)
        height = max(1.6, (self.end - self.start) / DAY_MINUTES * 100)
        width = 100 / self.cols
        left = self.col * width
        return (
            f"top:{top:.3f}%;height:{height:.3f}%;"
            f"left:calc({left:.2f}% + 2px);width:calc({width:.2f}% - 4px);"
            f"background:{self.color};"
        )


@dataclass
class CalendarDay:
    date: date
    is_today: bool
    events: list[CalendarEvent] = field(default_factory=list)
    all_day: list[dict] = field(default_factory=list)


class CalendarService:
    @classmethod
    def week_view(cls, plan: WeeklyPlan, *, month: date | None = None) -> dict:
        today = WeekService.today()
        days = WeekService.days_of(plan)
        entries = list(
            TimeEntry.objects.filter(
                weekly_plan=plan,
                tracked_date__range=(plan.starts_on, plan.ends_on),
            )
            .select_related("weekly_goal", "category")
            .order_by("tracked_date", "starts_at", "created_at")
        )
        sessions = list(
            PlannedSession.objects.filter(
                planned_date__range=(plan.starts_on, plan.ends_on)
            ).select_related("goal", "goal__category")
        )
        by_date: dict[date, list[TimeEntry]] = {day: [] for day in days}
        for entry in entries:
            by_date.setdefault(entry.tracked_date, []).append(entry)

        calendar_days: list[CalendarDay] = []
        hours = list(range(HOUR_START, HOUR_START + HOUR_COUNT))
        for day in days:
            placed = cls._place_entries(by_date.get(day, []))
            all_day = [
                {
                    "title": session.goal.title,
                    "color": session.goal.color,
                    "href": "/planner/",
                }
                for session in sessions
                if session.planned_date == day
            ]
            calendar_days.append(
                CalendarDay(date=day, is_today=day == today, events=placed, all_day=all_day)
            )

        for day in calendar_days:
            cls._pack(day.events)

        month = month or date(plan.starts_on.year, plan.starts_on.month, 1)
        tz = WeekService.current_timezone()
        offset = WeekService.local_now().utcoffset() or timedelta(0)
        offset_hours, offset_minutes = divmod(int(offset.total_seconds()) // 60, 60)
        sign = "+" if offset_hours >= 0 else "-"
        tz_label = f"GMT{sign}{abs(offset_hours)}:{abs(offset_minutes):02d}"

        now_top = None
        now = WeekService.local_now()
        if plan.starts_on <= today <= plan.ends_on:
            now_minutes = now.hour * 60 + now.minute
            now_top = max(0, min(100, (now_minutes - ORIGIN_MINUTES) / DAY_MINUTES * 100))

        return {
            "plan": plan,
            "days": calendar_days,
            "hours": hours,
            "today": today,
            "month": month,
            "month_weeks": cls._month_weeks(month, plan.week_starts_on),
            "weekday_labels": cls._weekday_labels(plan.week_starts_on),
            "categories": list(Category.objects.all()),
            "tz_label": tz_label,
            "tz_name": tz.key if hasattr(tz, "key") else str(tz),
            "now_top": now_top,
            "prev_week": plan.starts_on - timedelta(days=7),
            "next_week": plan.starts_on + timedelta(days=7),
            "prev_month": (month.replace(day=1) - timedelta(days=1)).replace(day=1),
            "next_month": (month.replace(day=28) + timedelta(days=8)).replace(day=1),
        }

    @classmethod
    def _place_entries(cls, entries: list[TimeEntry]) -> list[CalendarEvent]:
        timed = []
        untimed = []
        for entry in entries:
            start = minutes_of(entry.starts_at)
            end = minutes_of(entry.ends_at)
            if start is None:
                untimed.append(entry)
                continue
            if end is None or end <= start:
                end = min(24 * 60, start + entry.duration_minutes)
            timed.append(cls._event_from_entry(entry, start, end))

        cursor = UNTIMED_START
        occupied = sorted((event.start, event.end) for event in timed)
        for entry in untimed:
            start = cls._first_gap(cursor, entry.duration_minutes, occupied)
            end = min(24 * 60, start + entry.duration_minutes)
            timed.append(cls._event_from_entry(entry, start, end))
            occupied.append((start, end))
            occupied.sort()
            cursor = end
        return timed

    @staticmethod
    def _first_gap(start: int, duration: int, occupied: list[tuple[int, int]]) -> int:
        cursor = start
        for occ_start, occ_end in occupied:
            if cursor + duration <= occ_start:
                return cursor
            if cursor < occ_end:
                cursor = occ_end
        return cursor

    @staticmethod
    def _event_from_entry(entry: TimeEntry, start: int, end: int) -> CalendarEvent:
        start_label = time_from_minutes(start).strftime("%H:%M")
        end_label = time_from_minutes(end).strftime("%H:%M")
        return CalendarEvent(
            title=entry.activity_title,
            color=entry.calendar_color,
            start=start,
            end=end,
            href=f"/entries/{entry.pk}/",
            kind="tracked",
            time_label=f"{start_label} – {end_label}",
        )

    @staticmethod
    def _pack(events: list[CalendarEvent]) -> None:
        if not events:
            return
        ordered = sorted(events, key=lambda event: (event.start, -event.end, event.title))
        clusters: list[list[CalendarEvent]] = []
        current: list[CalendarEvent] = []
        current_end = -1
        for event in ordered:
            if current and event.start >= current_end:
                clusters.append(current)
                current = []
                current_end = -1
            current.append(event)
            current_end = max(current_end, event.end)
        if current:
            clusters.append(current)
        for cluster in clusters:
            col_ends: list[int] = []
            for event in cluster:
                placed = False
                for index, col_end in enumerate(col_ends):
                    if event.start >= col_end:
                        event.col = index
                        col_ends[index] = event.end
                        placed = True
                        break
                if not placed:
                    event.col = len(col_ends)
                    col_ends.append(event.end)
            columns = max(1, len(col_ends))
            for event in cluster:
                event.cols = columns

    @staticmethod
    def _weekday_labels(week_starts_on: int) -> list[str]:
        labels = []
        for offset in range(7):
            weekday = (week_starts_on + offset) % 7
            labels.append(Weekday(weekday).label[:3].upper())
        return labels

    @classmethod
    def _month_weeks(cls, month: date, week_starts_on: int) -> list[list[dict]]:
        first = date(month.year, month.month, 1)
        lead = (first.weekday() - week_starts_on) % 7
        days_in_month = monthrange(month.year, month.month)[1]
        cells: list[dict | None] = [None] * lead
        for day in range(1, days_in_month + 1):
            value = date(month.year, month.month, day)
            cells.append(
                {
                    "date": value,
                    "week_start": WeekService.week_start_for(value, week_starts_on),
                }
            )
        while len(cells) % 7:
            cells.append(None)
        return [cells[i : i + 7] for i in range(0, len(cells), 7)]
