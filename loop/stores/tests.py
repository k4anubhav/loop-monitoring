from django.test import TestCase
from django.utils import timezone

from .models import Store, StoreBusinessHour
from .utils import StoreBusinessHourHelper


class TestBusinessHourGenerator(TestCase):
    def setUp(self) -> None:
        # leads to split in business hours
        store_split = Store.objects.create(**{'store_id': 1, 'timezone_str': 'Asia/Kolkata'})
        StoreBusinessHour.objects.create(**{
            'store_id': 1,
            'day': 0,
            'start_time_local': '00:00:00',
            'end_time_local': '23:59:59',
        })
        StoreBusinessHour.objects.create(**{
            'store_id': 1,
            'day': 1,
            'start_time_local': '00:00:00',
            'end_time_local': '23:59:59',
        })
        self.store_split_helper = StoreBusinessHourHelper(store_split)

        # no business hours, means always open
        store_always_open = Store.objects.create(**{'store_id': 2, 'timezone_str': 'UTC'})
        self.store_always_open_helper = StoreBusinessHourHelper(store_always_open)

        # check case when store is open one day of the week and closed the other
        store_one_day = Store.objects.create(**{'store_id': 3, 'timezone_str': 'Asia/Kolkata'})
        StoreBusinessHour.objects.create(**{
            'store_id': 3,
            'day': 0,
            'start_time_local': '8:00:00',
            'end_time_local': '10:59:59',
        })
        self.store_one_day_helper = StoreBusinessHourHelper(store_one_day)

    def test_business_hour_generator(self):
        start_datetime = timezone.datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_datetime = timezone.datetime(2020, 1, 7, 23, 59, 59, tzinfo=timezone.utc)

        # leads to split in business hours
        hours = list(self.store_split_helper.shifts_generator(start_datetime, end_datetime))
        self.assertEqual(len(hours), 2)

        # no business hours, means always open
        hours = list(self.store_always_open_helper.shifts_generator(start_datetime, end_datetime))
        self.assertEqual(len(hours), 7)

        # check case when store is open one day of the week and closed the other
        hours = list(self.store_one_day_helper.shifts_generator(start_datetime, end_datetime))
        self.assertEqual(len(hours), 1)
