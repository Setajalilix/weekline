from django.contrib import admin

from performance.models import (
    Activity,
    AppSettings,
    Category,
    PlannedSession,
    TimeEntry,
    TimerSession,
    WeeklyGoal,
    WeeklyPlan,
)


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ["week_starts_on", "timezone"]


admin.site.register(Category)
admin.site.register(Activity)
admin.site.register(WeeklyPlan)
admin.site.register(WeeklyGoal)
admin.site.register(PlannedSession)
admin.site.register(TimeEntry)
admin.site.register(TimerSession)
