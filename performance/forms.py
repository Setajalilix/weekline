from zoneinfo import available_timezones

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from performance.models import AppSettings, Category, Weekday, WeeklyGoal
from performance.services.calendar import minutes_of, time_from_minutes
from performance.services.weeks import WeekService

COLOR_SWATCHES = [
    "#B8A0FF",
    "#A9C9B2",
    "#E8C39E",
    "#F4A5AE",
    "#8EC8E8",
    "#F1E4C3",
    "#7A7D8A",
    "#C9A227",
    "#81A1C1",
    "#D08770",
    "#B48EAD",
    "#88C0D0",
    "#A3BE8C",
    "#BF616A",
    "#5E81AC",
    "#EBCB8B",
    "#FF8A65",
    "#6EC8A0",
    "#E6A8D7",
    "#7EB6FF",
]


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = f"{css} field-input field-select".strip()
            elif not isinstance(field.widget, (forms.CheckboxInput, forms.HiddenInput)):
                field.widget.attrs["class"] = f"{css} field-input".strip()
            if isinstance(field.widget, forms.NumberInput):
                field.widget.attrs["class"] += " field-number"
                field.widget.attrs.setdefault("inputmode", "numeric")


class LoginForm(StyledFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username"
        self.fields["password"].label = "Password"


class PasswordForm(StyledFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Current password"
        self.fields["new_password1"].label = "New password"
        self.fields["new_password2"].label = "Confirm new password"


class SettingsForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = AppSettings
        fields = ["week_starts_on", "timezone"]
        labels = {
            "week_starts_on": "Week starts on",
            "timezone": "Time zone",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        zones = sorted(available_timezones())
        self.fields["timezone"].widget = forms.Select(choices=[(z, z) for z in zones])
        self.fields["timezone"].widget.attrs["class"] = "field-input field-select"
        self.fields["week_starts_on"].choices = Weekday.choices


class GoalForm(StyledFormMixin, forms.Form):
    activity = forms.CharField(max_length=160, label="Goal name")
    target_hours = forms.IntegerField(min_value=0, initial=1, label="Hours")
    target_minutes = forms.IntegerField(min_value=0, max_value=59, initial=0, label="Minutes")
    description = forms.CharField(
        required=False,
        label="Notes",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Optional context for this week"}),
    )
    color = forms.CharField(initial="#B8A0FF", widget=forms.HiddenInput)
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label="Category",
        empty_label="No category",
    )

    def clean(self):
        cleaned = super().clean()
        total = cleaned.get("target_hours", 0) * 60 + cleaned.get("target_minutes", 0)
        if total < 1:
            raise forms.ValidationError("Set a target of at least 1 minute.")
        cleaned["target_total"] = total
        return cleaned


class SessionForm(StyledFormMixin, forms.Form):
    planned_date = forms.DateField(label="Day", widget=forms.DateInput(attrs={"type": "date"}))
    hours = forms.IntegerField(min_value=0, initial=1, label="Hours")
    minutes = forms.IntegerField(min_value=0, max_value=59, initial=0, label="Minutes")
    note = forms.CharField(required=False, max_length=240, label="Note")

    def clean(self):
        cleaned = super().clean()
        total = cleaned.get("hours", 0) * 60 + cleaned.get("minutes", 0)
        if total < 1:
            raise forms.ValidationError("Plan at least 1 minute.")
        cleaned["duration_minutes"] = total
        return cleaned


class ManualEntryForm(StyledFormMixin, forms.Form):
    activity = forms.CharField(max_length=160, label="Activity")
    weekly_goal = forms.ModelChoiceField(
        queryset=WeeklyGoal.objects.none(),
        required=False,
        label="Weekly goal",
        empty_label="No goal",
    )
    tracked_date = forms.DateField(label="Date", widget=forms.DateInput(attrs={"type": "date"}))
    hours = forms.IntegerField(min_value=0, initial=1, label="Hours")
    minutes = forms.IntegerField(min_value=0, max_value=59, initial=0, label="Minutes")
    starts_at = forms.TimeField(required=False, widget=forms.HiddenInput)
    note = forms.CharField(
        required=False,
        label="Note",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "What did you get done?"}),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label="Category",
        empty_label="No category",
    )

    def __init__(self, *args, plan=None, **kwargs):
        super().__init__(*args, **kwargs)
        if plan:
            self.fields["weekly_goal"].queryset = WeeklyGoal.objects.filter(plan=plan)
        else:
            self.fields["weekly_goal"].queryset = WeeklyGoal.objects.none()
        self.fields["weekly_goal"].label_from_instance = lambda obj: obj.title
        self.fields["activity"].widget.attrs["x-ref"] = "activity"
        if not self.is_bound:
            self.fields["tracked_date"].initial = WeekService.today()

    def clean(self):
        cleaned = super().clean()
        total = cleaned.get("hours", 0) * 60 + cleaned.get("minutes", 0)
        if total < 1:
            raise forms.ValidationError("Add at least 1 minute.")
        cleaned["duration_minutes"] = total
        starts_at = cleaned.get("starts_at")
        if starts_at:
            cleaned["ends_at"] = time_from_minutes(minutes_of(starts_at) + total)
        else:
            cleaned["ends_at"] = None
        return cleaned


class TimerStartForm(StyledFormMixin, forms.Form):
    activity = forms.CharField(max_length=160, label="What are you focusing on?")
    weekly_goal = forms.ModelChoiceField(
        queryset=WeeklyGoal.objects.none(),
        required=False,
        label="Weekly goal",
        empty_label="No goal",
    )

    def __init__(self, *args, plan=None, **kwargs):
        super().__init__(*args, **kwargs)
        if plan:
            self.fields["weekly_goal"].queryset = WeeklyGoal.objects.filter(plan=plan)
        self.fields["weekly_goal"].label_from_instance = lambda obj: obj.title


class TimerFinishForm(StyledFormMixin, forms.Form):
    hours = forms.IntegerField(min_value=0, label="Hours")
    minutes = forms.IntegerField(min_value=0, max_value=59, label="Minutes")
    starts_at = forms.TimeField(required=False, widget=forms.HiddenInput)
    tracked_date = forms.DateField(label="Date", widget=forms.DateInput(attrs={"type": "date"}))
    note = forms.CharField(
        required=False,
        label="Note",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Optional note"}),
    )

    def clean(self):
        cleaned = super().clean()
        total = cleaned.get("hours", 0) * 60 + cleaned.get("minutes", 0)
        if total < 5:
            raise forms.ValidationError("Save at least 5 minutes.")
        cleaned["duration_minutes"] = total
        starts_at = cleaned.get("starts_at")
        if starts_at:
            cleaned["ends_at"] = time_from_minutes(minutes_of(starts_at) + total)
        else:
            cleaned["ends_at"] = None
        return cleaned


class CategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "color"]
        labels = {"name": "Name", "color": "Color"}
        widgets = {"color": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get("color") and not self.data.get("color"):
            self.initial["color"] = COLOR_SWATCHES[0]


class MoveSessionForm(StyledFormMixin, forms.Form):
    planned_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
