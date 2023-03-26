import csv

from django.core.management.base import BaseCommand

from stores.models import Store


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('file', type=str)

    def handle(self, *args, **options):
        csv_file = options['file']

        models = []
        with open(csv_file, 'r') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                store_id = int(row['store_id'])
                models.append(
                    Store(
                        store_id=store_id,
                        timezone_str=row['timezone_str'],
                    )
                )
        Store.objects.bulk_create(models)
        self.stdout.write(self.style.SUCCESS(f'Successfully imported store status: {csv_file}'))
        self.stdout.write(self.style.SUCCESS(f'Total: {len(models)}'))
