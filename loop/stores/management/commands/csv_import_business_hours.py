import csv

from django.core.management.base import BaseCommand

from stores.models import StoreBusinessHour
from ._import_store import import_store


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('file', type=str)

    def handle(self, *args, **options):
        csv_file = options['file']

        models = []
        store_ids = []
        with open(csv_file, 'r') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                store_id = int(row['store_id'])
                store_ids.append(store_id)
                models.append(
                    StoreBusinessHour(
                        store_id=store_id,
                        day=int(row['day']),
                        start_time_local=row['start_time_local'],
                        end_time_local=row['end_time_local'],
                    )
                )

        import_store(store_ids)
        StoreBusinessHour.objects.bulk_create(models)
        self.stdout.write(self.style.SUCCESS(f'Successfully imported business hours: {csv_file}'))
        self.stdout.write(self.style.SUCCESS(f'Total: {len(models)}'))
