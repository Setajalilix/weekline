from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from performance.models import AppSettings, Category


class Command(BaseCommand):
    help = "Create the single Weekline user, settings, and starter categories."

    def handle(self, *args, **options):
        User = get_user_model()
        username = settings.WEEKLINE_USERNAME
        password = settings.WEEKLINE_PASSWORD
        user, created = User.objects.get_or_create(username=username, defaults={"is_staff": True})
        user.set_password(password)
        user.is_staff = True
        user.save()
        AppSettings.load()
        for name, color in [
            ("Deep work", "#B8A0FF"),
            ("Learning", "#A9C9B2"),
            ("Health", "#E8C39E"),
            ("Admin", "#A5A7B1"),
        ]:
            Category.objects.get_or_create(name=name, defaults={"color": color})
        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"User {username} {action}."))
