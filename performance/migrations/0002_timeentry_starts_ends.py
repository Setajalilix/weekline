from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("performance", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="timeentry",
            name="starts_at",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="timeentry",
            name="ends_at",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
