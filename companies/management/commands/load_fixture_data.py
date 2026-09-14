from django.core.management.base import BaseCommand, CommandError

from analytics.fixture_provider import FixtureProvider
from companies.ingestion import import_fixture_data


class Command(BaseCommand):
    help = "Load the deterministic case-study companies and their normalized fixture data."

    def handle(self, *args, **options):
        report = import_fixture_data(FixtureProvider())
        if report.errors:
            raise CommandError("Fixture import failed: " + "; ".join(report.errors))
        self.stdout.write(self.style.SUCCESS(
            f"Imported {report.companies} companies, {report.securities} securities, "
            f"{report.statements} statements, {report.prices} prices, and "
            f"{report.corporate_actions} corporate actions."
        ))
