from performance.models import TimerStatus
from performance.services.timer import TimerService


def ui(request):
    if not request.user.is_authenticated:
        return {}
    session = TimerService.active()
    return {
        "active_timer": session,
        "timer_running": bool(session and session.status == TimerStatus.RUNNING),
        "nav_items": [
            ("overview", "Overview", "/", "layout-dashboard"),
            ("calendar", "Calendar", "/calendar/", "calendar-range"),
            ("planner", "Weekly Planner", "/planner/", "calendar"),
            ("daily", "Daily Tracker", "/daily/", "calendar-days"),
            ("timer", "Focus Timer", "/timer/", "clock-3"),
            ("review", "Weekly Review", "/review/", "target"),
            ("history", "History", "/history/", "history"),
            ("settings", "Settings", "/settings/", "settings"),
        ],
    }
