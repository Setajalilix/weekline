from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Weekday(models.IntegerChoices):
    MONDAY = 0, "Monday"
    TUESDAY = 1, "Tuesday"
    WEDNESDAY = 2, "Wednesday"
    THURSDAY = 3, "Thursday"
    FRIDAY = 4, "Friday"
    SATURDAY = 5, "Saturday"
    SUNDAY = 6, "Sunday"


class TimeEntrySource(models.TextChoices):
    MANUAL = "manual", "Manual"
    TIMER = "timer", "Timer"


class TimerStatus(models.TextChoices):
    RUNNING = "running", "Running"
    PAUSED = "paused", "Paused"
    FINISHED = "finished", "Finished"
    DISCARDED = "discarded", "Discarded"


class AppSettings(models.Model):
    week_starts_on = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
        default=Weekday.SATURDAY,
    )
    timezone = models.CharField(max_length=64, default="Asia/Tehran")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "settings"
        verbose_name_plural = "settings"

    def __str__(self):
        return "App settings"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    color = models.CharField(max_length=7, default="#B8A0FF")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Activity(models.Model):
    name = models.CharField(max_length=160, unique=True)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities",
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "activities"

    def __str__(self):
        return self.name


class WeeklyPlan(models.Model):
    starts_on = models.DateField(unique=True)
    week_starts_on = models.PositiveSmallIntegerField(choices=Weekday.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-starts_on"]
        indexes = [models.Index(fields=["starts_on"])]

    def __str__(self):
        return f"Week of {self.starts_on}"

    @property
    def ends_on(self):
        from datetime import timedelta

        return self.starts_on + timedelta(days=6)


class WeeklyGoal(models.Model):
    plan = models.ForeignKey(WeeklyPlan, on_delete=models.CASCADE, related_name="goals")
    activity = models.ForeignKey(
        Activity,
        on_delete=models.PROTECT,
        related_name="weekly_goals",
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="weekly_goals",
    )
    color = models.CharField(max_length=7, default="#B8A0FF")
    target_minutes = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(fields=["plan", "activity"], name="uniq_goal_activity_per_plan"),
        ]

    def __str__(self):
        return self.title


class PlannedSession(models.Model):
    goal = models.ForeignKey(
        WeeklyGoal,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    planned_date = models.DateField()
    duration_minutes = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    note = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["planned_date"]
        constraints = [
            models.UniqueConstraint(fields=["goal", "planned_date"], name="uniq_session_per_goal_day"),
        ]
        indexes = [models.Index(fields=["planned_date"])]

    def __str__(self):
        return f"{self.goal.title} on {self.planned_date}"


class TimerSession(models.Model):
    activity = models.ForeignKey(
        Activity,
        on_delete=models.PROTECT,
        related_name="timer_sessions",
    )
    weekly_goal = models.ForeignKey(
        WeeklyGoal,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="timer_sessions",
    )
    weekly_plan = models.ForeignKey(
        WeeklyPlan,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="timer_sessions",
    )
    activity_title = models.CharField(max_length=160)
    status = models.CharField(max_length=16, choices=TimerStatus.choices)
    started_at = models.DateTimeField()
    segment_started_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    accumulated_seconds = models.PositiveIntegerField(default=0)
    finished_at = models.DateTimeField(null=True, blank=True)
    active_guard = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["active_guard"],
                condition=Q(status__in=[TimerStatus.RUNNING, TimerStatus.PAUSED]),
                name="one_active_timer_session",
            ),
        ]

    def __str__(self):
        return f"{self.activity_title} ({self.status})"


class TimeEntry(models.Model):
    weekly_plan = models.ForeignKey(
        WeeklyPlan,
        on_delete=models.CASCADE,
        related_name="time_entries",
    )
    weekly_goal = models.ForeignKey(
        WeeklyGoal,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="time_entries",
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.PROTECT,
        related_name="time_entries",
    )
    activity_title = models.CharField(max_length=160)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="time_entries",
    )
    tracked_date = models.DateField()
    starts_at = models.TimeField(null=True, blank=True)
    ends_at = models.TimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    source = models.CharField(max_length=16, choices=TimeEntrySource.choices)
    note = models.TextField(blank=True)
    timer_session = models.OneToOneField(
        TimerSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="time_entry",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-tracked_date", "-created_at"]
        indexes = [
            models.Index(fields=["weekly_plan", "tracked_date"]),
            models.Index(fields=["tracked_date"]),
            models.Index(fields=["weekly_goal"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(source=TimeEntrySource.TIMER, timer_session__isnull=False)
                    | Q(source=TimeEntrySource.MANUAL, timer_session__isnull=True)
                ),
                name="time_entry_source_matches_timer",
            ),
        ]

    @property
    def calendar_color(self):
        if self.weekly_goal_id and self.weekly_goal.color:
            return self.weekly_goal.color
        if self.category_id:
            return self.category.color
        return "#B8A0FF"

    def __str__(self):
        return f"{self.activity_title} {self.duration_minutes}m"
