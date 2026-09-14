from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("financials", "0003_analysisrun")]

    operations = [
        migrations.AlterField(
            model_name="analysisrun",
            name="status",
            field=models.CharField(
                choices=[
                    ("created", "Created"),
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("succeeded", "Succeeded"),
                    ("partially_evaluable", "Partially evaluable"),
                    ("failed", "Failed"),
                ],
                default="created",
                max_length=24,
            ),
        ),
    ]
