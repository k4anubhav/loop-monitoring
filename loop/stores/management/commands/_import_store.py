from stores.models import Store


def import_store(store_ids: 'list[int]'):
    Store.objects.bulk_create([
        Store(
            store_id=store_id,
            # ... other required fields
        )
        for store_id in store_ids
    ], ignore_conflicts=True)
