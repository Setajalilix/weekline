from datetime import date

from django.db import transaction
from django.db.models import Prefetch

from performance.models import Activity, PlannedSession, WeeklyGoal, WeeklyPlan
from performance.services.weeks import WeekService


class PlanningService:
    @staticmethod
    def get_or_create_activity(name: str, category=None) -> Activity:
        activity, _ = Activity.objects.get_or_create(
            name=name.strip(),
            defaults={"category": category},
        )
        return activity

    @classmethod
    @transaction.atomic
    def add_goal(
        cls,
        plan: WeeklyPlan,
        *,
        activity_name: str,
        target_minutes: int,
        description: str = "",
        category=None,
        color: str = "#B8A0FF",
    ) -> WeeklyGoal:
        if target_minutes < 1:
            raise ValueError("Weekly target must be at least 1 minute.")
        activity = cls.get_or_create_activity(activity_name, category)
        if WeeklyGoal.objects.filter(plan=plan, activity=activity).exists():
            raise ValueError("This activity is already a goal for the week.")
        return WeeklyGoal.objects.create(
            plan=plan,
            activity=activity,
            title=activity.name,
            description=description,
            category=category or activity.category,
            color=color,
            target_minutes=target_minutes,
        )

    @staticmethod
    def update_goal(goal: WeeklyGoal, *, target_minutes: int, description: str, color: str, category=None):
        if target_minutes < 1:
            raise ValueError("Weekly target must be at least 1 minute.")
        goal.target_minutes = target_minutes
        goal.description = description
        goal.color = color
        goal.category = category
        goal.save(update_fields=["target_minutes", "description", "color", "category", "updated_at"])
        return goal

    @classmethod
    @transaction.atomic
    def set_session(cls, goal: WeeklyGoal, planned_date: date, duration_minutes: int, note: str = ""):
        if duration_minutes < 1:
            raise ValueError("Planned time must be at least 1 minute.")
        cls._assert_date_in_plan(goal.plan, planned_date)
        session, created = PlannedSession.objects.get_or_create(
            goal=goal,
            planned_date=planned_date,
            defaults={"duration_minutes": duration_minutes, "note": note},
        )
        if not created:
            session.duration_minutes = duration_minutes
            session.note = note
            session.save(update_fields=["duration_minutes", "note", "updated_at"])
        return session

    @classmethod
    @transaction.atomic
    def move_session(cls, session: PlannedSession, new_date: date):
        cls._assert_date_in_plan(session.goal.plan, new_date)
        if PlannedSession.objects.filter(goal=session.goal, planned_date=new_date).exclude(pk=session.pk).exists():
            raise ValueError("That day already has a planned session for this goal. Edit it instead.")
        session.planned_date = new_date
        session.save(update_fields=["planned_date", "updated_at"])
        return session

    @staticmethod
    def delete_session(session: PlannedSession):
        session.delete()

    @classmethod
    @transaction.atomic
    def reuse_goal(cls, source_goal: WeeklyGoal, target_plan: WeeklyPlan) -> WeeklyGoal:
        return cls.add_goal(
            target_plan,
            activity_name=source_goal.activity.name,
            target_minutes=source_goal.target_minutes,
            description=source_goal.description,
            category=source_goal.category,
            color=source_goal.color,
        )

    @staticmethod
    def _assert_date_in_plan(plan: WeeklyPlan, planned_date: date):
        if not (plan.starts_on <= planned_date <= plan.ends_on):
            raise ValueError("Planned sessions must stay inside the week.")

    @staticmethod
    def plan_with_goals(plan: WeeklyPlan) -> WeeklyPlan:
        return WeeklyPlan.objects.prefetch_related(
            Prefetch(
                "goals",
                queryset=WeeklyGoal.objects.select_related("activity", "category").prefetch_related("sessions"),
            )
        ).get(pk=plan.pk)

    @classmethod
    def current_plan(cls) -> WeeklyPlan:
        return WeekService.ensure_plan_for(WeekService.today())
