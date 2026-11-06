from django.shortcuts import redirect
from django.utils import timezone

from performance.models import AppSettings


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            settings = AppSettings.load()
            timezone.activate(settings.timezone)
        except Exception:
            timezone.deactivate()
        return self.get_response(request)


class SingleUserAuthMiddleware:
    OPEN_PREFIXES = ("/login", "/static", "/admin", "/favicon")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if any(path.startswith(prefix) for prefix in self.OPEN_PREFIXES):
            return self.get_response(request)
        if not request.user.is_authenticated:
            return redirect("login")
        return self.get_response(request)
