from collections import defaultdict
from datetime import datetime, time, timedelta
from functools import lru_cache
from typing import Optional, List, TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from stores.models import Store, StoreBusinessHour

make_aware = timezone.make_aware

DAY_START = time(0, 0, tzinfo=timezone.utc)
DAY_END = time(23, 59, 59, 999999, tzinfo=timezone.utc)


def time_datetime_difference(time_: time, datetime_: datetime) -> timedelta:
    """
    Returns the difference between time and datetime
    """
    diff = datetime.combine(datetime_.date(), time_) - datetime_
    if diff.total_seconds() < 0:
        return -diff
    return diff


class StoreBusinessHourHelper:
    """
    Helper class to handle the business hours of a store
    """

    class BusinessHour:
        def __init__(self, start_time: time, end_time: time, weekday: int):
            self.start_time = start_time
            self.end_time = end_time
            self.weekday = weekday

        def is_within(self, time_: time) -> bool:
            return self.start_time <= time_ <= self.end_time

        def __eq__(self, other):
            return (
                    self.start_time == other.start_time and
                    self.end_time == other.end_time and
                    self.weekday == other.weekday
            )

        def __str__(self):
            return f"{self.start_time} - {self.end_time}"

    def __init__(self, store: 'Store', business_hours: 'List[StoreBusinessHour]'):
        self.store = store
        self.always_open = True

        self._business_hours_utc: 'dict[int, list[StoreBusinessHourHelper.BusinessHour]]' = defaultdict(list)
        temp_day = datetime.today()
        for business_hour in business_hours:
            self.always_open = False
            # Make `start_time`, `end_time` correct timezone aware
            start_time_aware = business_hour.start_time_local.replace(tzinfo=self.store.timezone)
            end_time_aware = business_hour.end_time_local.replace(tzinfo=self.store.timezone)

            # Convert to UTC
            start_time_utc = make_aware(datetime.combine(temp_day, start_time_aware).astimezone(
                timezone.utc).time(), timezone.utc)
            end_time_utc = make_aware(datetime.combine(temp_day, end_time_aware).astimezone(
                timezone.utc).time(), timezone.utc)

            weekday = business_hour.day

            # handle the case when the timezone shifts cause the day change
            if start_time_utc > end_time_utc:
                self._business_hours_utc[weekday].append(
                    StoreBusinessHourHelper.BusinessHour(start_time_utc, DAY_END, weekday))
                self._business_hours_utc[(weekday + 1) % 7].append(
                    StoreBusinessHourHelper.BusinessHour(DAY_START, end_time_utc, (weekday + 1) % 7))
            else:
                self._business_hours_utc[weekday].append(
                    StoreBusinessHourHelper.BusinessHour(start_time_utc, end_time_utc, weekday)
                )

    @property
    def business_hours(self) -> 'dict[int, list[StoreBusinessHourHelper.BusinessHour]]':
        return self._business_hours_utc

    def get_business_hours_list(self, day: int) -> 'list[StoreBusinessHourHelper.BusinessHour]':
        return self.business_hours[day]

    @lru_cache
    def get_business_hours(self, day: int, time_: 'datetime.time') -> 'Optional[StoreBusinessHourHelper.BusinessHour]':
        if self.always_open:
            return StoreBusinessHourHelper.BusinessHour(DAY_START, DAY_END, day)
        for business_hour in self.business_hours[day]:
            if business_hour.is_within(time_):
                return business_hour
        return None

    def __str__(self):
        return f"{self.store} - {self.business_hours} - {self.always_open}"
