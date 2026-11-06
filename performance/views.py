import json
from datetime import date, time, timedelta

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from performance.forms import (
    COLOR_SWATCHES,
    CategoryForm,
    GoalForm,
    LoginForm,
    ManualEntryForm,
    MoveSessionForm,
    PasswordForm,
    SessionForm,
    SettingsForm,
    TimerFinishForm,
    TimerStartForm,
)
from performance.models import Category, PlannedSession, TimeEntry, WeeklyGoal, WeeklyPlan
from performance.services.calendar import CalendarService
from performance.services.entries import TimeEntryService
from performance.services.planning import PlanningService
from performance.services.reporting import ReportingService, format_minutes
from performance.services.timer import TimerService
from performance.services.weeks import WeekService


class WeeklineLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class WeeklineLogoutView(LogoutView):
    next_page = "login"


def _plan_from_request(request) -> WeeklyPlan:
    starts = request.GET.get("week")
    if starts:
        try:
            day = date.fromisoformat(starts)
        except ValueError:
            day = WeekService.today()
        return WeekService.ensure_plan_for(day)
    return WeekService.ensure_plan_for(WeekService.today())


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def overview(request):
    plan = _plan_from_request(request)
    report = ReportingService.week_report(plan)
    today = WeekService.today()
    day = ReportingService.day_view(today)
    entry_form = ManualEntryForm(plan=plan)
    chart = {
        "labels": [d.strftime("%a") for d in report["days"]],
        "values": [row["actual_minutes"] / 60 for row in report["daily"]],
    }
    return render(
        request,
        "performance/overview.html",
        {
            "report": report,
            "plan": plan,
            "today": day,
            "entry_form": entry_form,
            "chart_json": json.dumps(chart),
            "format_minutes": format_minutes,
        },
    )


def _planner_redirect(plan: WeeklyPlan, *, edit=None):
    url = f"/planner/?week={plan.starts_on.isoformat()}"
    if edit:
        return redirect(f"{url}&edit={edit}")
    return redirect(url)


def planner(request):
    plan = _plan_from_request(request)
    report = ReportingService.week_report(plan)
    previous = WeeklyGoal.objects.select_related("activity", "plan").exclude(plan=plan).order_by("-plan__starts_on")[:20]
    edit_raw = request.GET.get("edit")
    edit_goal_id = int(edit_raw) if edit_raw and edit_raw.isdigit() else None
    return render(
        request,
        "performance/planner.html",
        {
            "plan": plan,
            "report": report,
            "goal_form": GoalForm(),
            "session_form": SessionForm(initial={"planned_date": WeekService.today()}),
            "previous_goals": previous,
            "days": WeekService.days_of(plan),
            "color_swatches": COLOR_SWATCHES,
            "edit_goal_id": edit_goal_id,
        },
    )


@require_POST
def create_goal(request):
    plan = _plan_from_request(request)
    form = GoalForm(request.POST)
    if form.is_valid():
        try:
            PlanningService.add_goal(
                plan,
                activity_name=form.cleaned_data["activity"],
                target_minutes=form.cleaned_data["target_total"],
                description=form.cleaned_data["description"],
                category=form.cleaned_data["category"],
                color=form.cleaned_data["color"],
            )
            messages.success(request, "Goal added.")
        except ValueError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "Add a name and a target of at least 1 minute.")
    return _planner_redirect(plan)


@require_POST
def update_goal(request, pk):
    goal = get_object_or_404(WeeklyGoal, pk=pk)
    form = GoalForm(request.POST)
    if form.is_valid():
        PlanningService.update_goal(
            goal,
            target_minutes=form.cleaned_data["target_total"],
            description=form.cleaned_data["description"],
            color=form.cleaned_data["color"],
            category=form.cleaned_data["category"],
        )
        messages.success(request, "Goal updated.")
    else:
        messages.error(request, "The target must be at least 1 minute.")
    return _planner_redirect(goal.plan, edit=goal.pk)


@require_POST
def delete_goal(request, pk):
    goal = get_object_or_404(WeeklyGoal, pk=pk)
    plan = goal.plan
    title = goal.title
    PlanningService.delete_goal(goal)
    messages.success(request, f"{title} removed from this week.")
    return _planner_redirect(plan)


@require_POST
def add_session(request, pk):
    goal = get_object_or_404(WeeklyGoal, pk=pk)
    form = SessionForm(request.POST)
    if form.is_valid():
        try:
            PlanningService.set_session(
                goal,
                form.cleaned_data["planned_date"],
                form.cleaned_data["duration_minutes"],
                form.cleaned_data["note"],
            )
            messages.success(request, "Day plan saved. Your weekly target did not change.")
        except ValueError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "Plan at least 1 minute on a day this week.")
    return _planner_redirect(goal.plan, edit=goal.pk)


@require_POST
def move_session(request, pk):
    session = get_object_or_404(PlannedSession, pk=pk)
    form = MoveSessionForm(request.POST)
    if form.is_valid():
        try:
            PlanningService.move_session(session, form.cleaned_data["planned_date"])
            messages.success(request, "Session moved. Your weekly target did not change.")
        except ValueError as exc:
            messages.error(request, str(exc))
    return _planner_redirect(session.goal.plan, edit=session.goal_id)


@require_POST
def delete_session(request, pk):
    session = get_object_or_404(PlannedSession, pk=pk)
    week = session.goal.plan.starts_on
    PlanningService.delete_session(session)
    messages.success(request, "Day plan removed.")
    return redirect(f"/planner/?week={week.isoformat()}&edit={session.goal_id}")


@require_POST
def reuse_goal(request, pk):
    source = get_object_or_404(WeeklyGoal, pk=pk)
    plan = _plan_from_request(request)
    try:
        PlanningService.reuse_goal(source, plan)
        messages.success(request, f"{source.title} is on this week again.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect(f"/planner/?week={plan.starts_on.isoformat()}")


def calendar(request):
    plan = _plan_from_request(request)
    month_raw = request.GET.get("month")
    month = None
    if month_raw:
        try:
            year, month_n = month_raw.split("-")
            month = date(int(year), int(month_n), 1)
        except (TypeError, ValueError):
            month = None
    view = CalendarService.week_view(plan, month=month)
    return render(request, "performance/calendar.html", view)


def daily(request):
    from datetime import date as date_cls

    raw = request.GET.get("date")
    day = date_cls.fromisoformat(raw) if raw else WeekService.today()
    view = ReportingService.day_view(day)
    form = ManualEntryForm(plan=view["plan"], initial={"tracked_date": day})
    return render(
        request,
        "performance/daily.html",
        {
            "day": view,
            "entry_form": form,
            "prev": day - timedelta(days=1),
            "next": day + timedelta(days=1),
        },
    )


@require_http_methods(["GET", "POST"])
def log_entry(request):
    plan = _plan_from_request(request)
    if request.method == "GET":
        initial = {}
        raw_date = request.GET.get("date")
        raw_start = request.GET.get("start")
        if raw_date:
            try:
                initial["tracked_date"] = date.fromisoformat(raw_date)
            except ValueError:
                pass
        if raw_start:
            try:
                hour, minute = raw_start.split(":")
                initial["starts_at"] = time(int(hour), int(minute))
            except (ValueError, TypeError):
                pass
        form = ManualEntryForm(plan=plan, initial=initial)
        return render(request, "performance/log_time.html", {"entry_form": form, "plan": plan})
    form = ManualEntryForm(request.POST, plan=plan)
    if form.is_valid():
        try:
            TimeEntryService.log_manual(
                activity_name=form.cleaned_data["activity"],
                tracked_date=form.cleaned_data["tracked_date"],
                duration_minutes=form.cleaned_data["duration_minutes"],
                note=form.cleaned_data["note"],
                weekly_goal=form.cleaned_data["weekly_goal"],
                category=form.cleaned_data["category"],
                starts_at=form.cleaned_data.get("starts_at"),
                ends_at=form.cleaned_data.get("ends_at"),
            )
            messages.success(request, "Time saved.")
            next_url = request.POST.get("next") or "calendar"
            if next_url in {"/", "daily"}:
                return redirect("daily")
            if next_url == "calendar":
                return redirect("calendar")
            return redirect(next_url)
        except ValueError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "Add an activity and at least 1 minute.")
    return render(request, "performance/log_time.html", {"entry_form": form, "plan": plan})


@require_http_methods(["GET", "POST"])
def edit_entry(request, pk):
    entry = get_object_or_404(TimeEntry, pk=pk)
    hours, minutes = divmod(entry.duration_minutes, 60)
    if request.method == "POST":
        form = ManualEntryForm(request.POST, plan=entry.weekly_plan)
        if form.is_valid():
            TimeEntryService.update_entry(
                entry,
                duration_minutes=form.cleaned_data["duration_minutes"],
                note=form.cleaned_data["note"],
                tracked_date=form.cleaned_data["tracked_date"],
                weekly_goal=form.cleaned_data["weekly_goal"],
                starts_at=form.cleaned_data.get("starts_at"),
                ends_at=form.cleaned_data.get("ends_at"),
            )
            messages.success(request, "Entry updated.")
            return redirect(request.POST.get("next") or "/calendar/")
    else:
        form = ManualEntryForm(
            plan=entry.weekly_plan,
            initial={
                "activity": entry.activity_title,
                "weekly_goal": entry.weekly_goal_id,
                "tracked_date": entry.tracked_date,
                "hours": hours,
                "minutes": minutes,
                "starts_at": entry.starts_at,
                "note": entry.note,
                "category": entry.category_id,
            },
        )
        form.fields["activity"].widget.attrs["readonly"] = True
    return render(request, "performance/entry_edit.html", {"entry": entry, "entry_form": form})


@require_POST
def delete_entry(request, pk):
    entry = get_object_or_404(TimeEntry, pk=pk)
    day = entry.tracked_date
    TimeEntryService.delete_entry(entry)
    messages.success(request, "Entry deleted.")
    return redirect(request.POST.get("next") or f"/daily/?date={day.isoformat()}")


def timer(request):
    plan = WeekService.ensure_plan_for(WeekService.today())
    session = TimerService.active()
    start_form = TimerStartForm(plan=plan)
    finish_form = None
    if session:
        suggested = TimerService.suggested_minutes(session)
        hours, minutes = divmod(suggested, 60)
        start_local = session.started_at.astimezone(WeekService.current_timezone())
        finish_form = TimerFinishForm(
            initial={
                "hours": hours,
                "minutes": minutes,
                "starts_at": start_local.time().replace(second=0, microsecond=0),
                "tracked_date": WeekService.today(),
            }
        )
    return render(
        request,
        "performance/timer.html",
        {
            "plan": plan,
            "session": session,
            "start_form": start_form,
            "finish_form": finish_form,
            "timer_state": json.dumps(TimerService.client_state(session)),
            "goals": plan.goals.select_related("activity"),
        },
    )


def timer_state(request):
    session = TimerService.active()
    return render(
        request,
        "performance/partials/timer_state.html",
        {
            "session": session,
            "timer_state": json.dumps(TimerService.client_state(session)),
        },
    )


@require_POST
def timer_start(request):
    plan = WeekService.ensure_plan_for(WeekService.today())
    form = TimerStartForm(request.POST, plan=plan)
    if not form.is_valid():
        messages.error(request, "Name what you're focusing on, then start.")
        return redirect("timer")
    try:
        activity = PlanningService.get_or_create_activity(form.cleaned_data["activity"])
        TimerService.start(activity, form.cleaned_data["weekly_goal"])
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("timer")


@require_POST
def timer_start_goal(request, pk):
    goal = get_object_or_404(WeeklyGoal, pk=pk)
    try:
        TimerService.start(goal.activity, goal)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect(request.POST.get("next") or "daily")
    return redirect("timer")


@require_POST
def timer_pause(request):
    try:
        TimerService.pause()
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("timer")


@require_POST
def timer_resume(request):
    try:
        TimerService.resume()
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("timer")


@require_POST
def timer_reset(request):
    try:
        TimerService.reset()
        messages.success(request, "Session cleared. Nothing was saved.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("timer")


@require_POST
def timer_finish(request):
    session = TimerService.active()
    if session is None:
        finished = TimeEntry.objects.filter(source="timer").select_related("timer_session").order_by("-created_at").first()
        if finished:
            messages.info(request, "This session is already saved.")
            return redirect("timer")
        messages.error(request, "There's no session to save.")
        return redirect("timer")
    form = TimerFinishForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Save at least 5 minutes.")
        return redirect("timer")
    try:
        TimerService.finish(
            form.cleaned_data["duration_minutes"],
            form.cleaned_data["note"],
            form.cleaned_data["tracked_date"],
        )
        messages.success(request, "Session saved.")
        return redirect("calendar")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("timer")


def review(request):
    plan = _plan_from_request(request)
    report = ReportingService.week_report(plan)
    chart = {
        "labels": [d.strftime("%a") for d in report["days"]],
        "values": [row["actual_minutes"] / 60 for row in report["daily"]],
        "manual": report["manual_minutes"] / 60,
        "timer": report["timer_minutes"] / 60,
    }
    return render(
        request,
        "performance/review.html",
        {"plan": plan, "report": report, "chart_json": json.dumps(chart)},
    )


def history(request):
    plans = list(ReportingService.history())
    return render(request, "performance/history.html", {"plans": plans})


def settings_view(request):
    app_settings = WeekService.settings()
    if request.method == "POST" and request.POST.get("form") == "settings":
        form = SettingsForm(request.POST, instance=app_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved. Past weeks keep their original dates.")
            return redirect("settings")
    else:
        form = SettingsForm(instance=app_settings)
    password_form = PasswordForm(request.user)
    if request.method == "POST" and request.POST.get("form") == "password":
        password_form = PasswordForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated.")
            return redirect("settings")
    category_form = CategoryForm()
    return render(
        request,
        "performance/settings.html",
        {
            "form": form,
            "password_form": password_form,
            "category_form": category_form,
            "categories": Category.objects.all(),
            "color_swatches": COLOR_SWATCHES,
        },
    )


@require_POST
def create_category(request):
    form = CategoryForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Category added.")
    else:
        messages.error(request, "Add a category name.")
    return redirect("settings")


@require_POST
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    name = category.name
    category.delete()
    messages.success(request, f"{name} removed.")
    return redirect("settings")
