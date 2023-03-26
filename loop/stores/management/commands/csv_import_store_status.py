import csv

from django.core.management.base import BaseCommand

from stores.models import StoreStatus
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
                    StoreStatus(
                        store_id=store_id,
                        timestamp_utc=row['timestamp_utc'],
                        is_active=row['status'] == 'active',
                    )
                )

        import_store(store_ids)
        StoreStatus.objects.bulk_create(models)
        self.stdout.write(self.style.SUCCESS(f'Successfully imported store status: {csv_file}'))
        self.stdout.write(self.style.SUCCESS(f'Total: {len(models)}'))
