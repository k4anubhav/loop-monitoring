from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from stores.models import Store

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


def time_time_difference(time1: time, time2: time) -> timedelta:
    """
    Returns the difference between two times
    """
    today = datetime.today()
    diff = datetime.combine(today, time1) - datetime.combine(today, time2)
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

        @property
        def duration(self) -> timedelta:
            return time_time_difference(self.end_time, self.start_time)

        def is_time_within(self, time_: time) -> bool:
            return self.start_time <= time_ <= self.end_time

        def contains(self, datetime_: datetime) -> bool:
            return datetime_.weekday() == self.weekday and self.is_time_within(
                make_aware(datetime_.time(), timezone.utc))

        def __eq__(self, other):
            return (
                    self.start_time == other.start_time and
                    self.end_time == other.end_time and
                    self.weekday == other.weekday
            )

        def __lt__(self, other):
            return self.weekday < other.weekday or (
                    self.weekday == other.weekday and self.start_time < other.start_time)

        def __str__(self):
            return f"{self.start_time} - {self.end_time} on {self.weekday}"

        class StoreShift:
            def __init__(self, start_datetime: datetime, end_datetime: datetime):
                assert start_datetime < end_datetime
                assert start_datetime.weekday() == end_datetime.weekday()
                self.start_datetime = start_datetime
                self.end_datetime = end_datetime

    def __init__(self, store: 'Store'):
        self.store = store
        self.always_open = True

        # sorted business hours in UTC
        self.business_hours_utc: 'list[StoreBusinessHourHelper.BusinessHour]' = []

        temp_day = datetime.today()
        for business_hour in store.business_hours.order_by('day', 'start_time_local'):
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
                self.business_hours_utc.append(
                    StoreBusinessHourHelper.BusinessHour(start_time_utc, DAY_END, weekday))
                self.business_hours_utc.append(
                    StoreBusinessHourHelper.BusinessHour(DAY_START, end_time_utc, (weekday + 1) % 7))
            else:
                self.business_hours_utc.append(
                    StoreBusinessHourHelper.BusinessHour(start_time_utc, end_time_utc, weekday)
                )

        if self.always_open:
            for i in range(7):
                self.business_hours_utc.append(
                    StoreBusinessHourHelper.BusinessHour(DAY_START, DAY_END, i)
                )

    def get_business_hours(self, day: int, time_: 'datetime.time') -> 'Optional[StoreBusinessHourHelper.BusinessHour]':
        for business_hour in self.business_hours_utc:
            if business_hour.weekday == day and business_hour.is_time_within(time_):
                return business_hour
        return None

    def business_hour_generator(self, start_datetime: datetime, end_datetime: datetime):
        """
        Generate business hours from start_datetime to end_datetime
        """
        curr_datetime = start_datetime
        while curr_datetime <= end_datetime:
            curr_time = make_aware(curr_datetime.time(), timezone.utc)
            for business_hour in self.business_hours_utc:
                # if the business hour is on the same day
                if business_hour.weekday == curr_datetime.weekday():
                    # if the business hour is within the current day
                    if business_hour.contains(curr_datetime) or (curr_time < business_hour.start_time):
                        yield business_hour
                        curr_datetime = datetime.combine(curr_datetime.date(), business_hour.end_time)

            curr_datetime = datetime.combine(curr_datetime.date(), DAY_START) + timedelta(days=1)

    def __str__(self):
        return f"{self.store} - {self.business_hours_utc} - {self.always_open}"
