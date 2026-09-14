from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_peergroupproposal_peergroupmember"),
        ("financials", "0002_forecastmeasure_forecastperiod_companyforecast_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnalysisRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("created", "Created"), ("running", "Running"), ("succeeded", "Succeeded"), ("partially_evaluable", "Partially evaluable"), ("failed", "Failed")], default="created", max_length=24)),
                ("data_snapshot_ids", models.JSONField(default=dict)),
                ("assumptions", models.JSONField(default=dict)),
                ("score_configuration", models.JSONField(default=dict)),
                ("hard_rules", models.JSONField(default=list)),
                ("input_parameters", models.JSONField(default=dict)),
                ("output", models.JSONField(blank=True, null=True)),
                ("errors", models.JSONField(default=list)),
                ("confirmed_peers", models.ManyToManyField(blank=True, related_name="analysis_runs_as_peer", to="companies.company")),
                ("security", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="analysis_runs", to="companies.security")),
            ],
            options={"ordering": ["-requested_at", "-id"]},
        ),
    ]
