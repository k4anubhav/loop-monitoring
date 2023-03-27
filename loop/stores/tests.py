from datetime import time

from django.test import TestCase
from django.utils import timezone

from .models import Store, StoreBusinessHour
from .utils import StoreBusinessHourHelper, DAY_START, DAY_END


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

    def test_business_hours_utc(self):
        # leads to split in business hours
        self.assertEqual(len(self.store_split_helper.business_hours_utc), 4)
        hours = [
            StoreBusinessHourHelper.BusinessHour(
                start_time=time(18, 30, tzinfo=timezone.utc),
                end_time=DAY_END,
                weekday=0
            ),
            StoreBusinessHourHelper.BusinessHour(
                start_time=DAY_START,
                end_time=time(18, 29, 59, tzinfo=timezone.utc),
                weekday=1
            ),
            StoreBusinessHourHelper.BusinessHour(
                start_time=time(18, 30, tzinfo=timezone.utc),
                end_time=DAY_END,
                weekday=1
            ),
            StoreBusinessHourHelper.BusinessHour(
                start_time=DAY_START,
                end_time=time(18, 29, 59, tzinfo=timezone.utc),
                weekday=2
            ),
        ]
        self.assertEqual(self.store_split_helper.business_hours_utc, hours)

        # no business hours, means always open
        self.assertTrue(self.store_always_open_helper.always_open)
        always_open_hours = []
        for i in range(7):
            always_open_hours.append(StoreBusinessHourHelper.BusinessHour(
                DAY_START,
                DAY_END,
                i
            ))
        self.assertEqual(self.store_always_open_helper.business_hours_utc, always_open_hours)

        # check case when store is open one day of the week and closed the other
        self.assertFalse(self.store_one_day_helper.always_open)
        one_day_hours = [
            StoreBusinessHourHelper.BusinessHour(
                start_time=time(2, 30, tzinfo=timezone.utc),
                end_time=time(5, 29, 59, tzinfo=timezone.utc),
                weekday=0
            )
        ]
        self.assertEqual(self.store_one_day_helper.business_hours_utc, one_day_hours)

    def test_business_hour_generator(self):
        start_time = timezone.datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = timezone.datetime(2020, 1, 7, 23, 59, 59, tzinfo=timezone.utc)

        # leads to split in business hours
        hours = list(self.store_split_helper.business_hour_generator(start_time, end_time))
        self.assertEqual(len(hours), 4)

        # no business hours, means always open
        hours = list(self.store_always_open_helper.business_hour_generator(start_time, end_time))
        self.assertEqual(len(hours), 7)

        # check case when store is open one day of the week and closed the other
        hours = list(self.store_one_day_helper.business_hour_generator(start_time, end_time))
        self.assertEqual(len(hours), 1)
