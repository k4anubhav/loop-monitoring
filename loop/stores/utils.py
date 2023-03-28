from collections import defaultdict
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Iterator

from django.utils import timezone

if TYPE_CHECKING:
    from stores.models import Store

make_aware = timezone.make_aware

DAY_START = time(0, 0, tzinfo=timezone.utc)
DAY_END = time(23, 59, 59, 999999, tzinfo=timezone.utc)


class StoreBusinessHourHelper:
    """
    Helper class to handle the business hours of a store
    """

    class BusinessHour:
        def __init__(self, start_time: time, end_time: time, weekday: int):
            self.start_time = start_time
            self.end_time = end_time
            self.weekday = weekday

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

        def __repr__(self):
            return self.__str__()

    class StoreShift:
        def __init__(self, start_datetime: datetime, end_datetime: datetime):
            assert start_datetime < end_datetime
            assert start_datetime.weekday() == end_datetime.weekday()
            self.start_datetime = start_datetime
            self.end_datetime = end_datetime

    def __init__(self, store: 'Store'):
        self.store = store
        self.always_open = True
        self.business_hours: 'dict[int, list[StoreBusinessHourHelper.BusinessHour]]' = defaultdict(list)

        for b_hour in store.business_hours.order_by('day', 'start_time_local') \
                .values('day', 'start_time_local', 'end_time_local'):
            self.always_open = False
            self.business_hours[b_hour['day']].append(
                StoreBusinessHourHelper.BusinessHour(
                    b_hour['start_time_local'].replace(tzinfo=store.timezone),
                    b_hour['end_time_local'].replace(tzinfo=store.timezone),
                    b_hour['day']
                )
            )

        if self.always_open:
            for weekday in range(7):
                self.business_hours[weekday].append(
                    StoreBusinessHourHelper.BusinessHour(DAY_START, DAY_END, weekday)
                )

    def shifts_generator(
            self, start_datetime: datetime, end_datetime: datetime
    ) -> 'Iterator[StoreBusinessHourHelper.StoreShift]':
        """
        Generate all shifts between start_datetime and end_datetime
        """
        curr_datetime = start_datetime
        while curr_datetime <= end_datetime:
            for business_hour in self.business_hours[curr_datetime.weekday()]:
                shift_start_datetime = datetime.combine(curr_datetime.date(), business_hour.start_time)
                shift_end_datetime = datetime.combine(curr_datetime.date(), business_hour.end_time)
                if curr_datetime <= shift_end_datetime:
                    yield StoreBusinessHourHelper.StoreShift(shift_start_datetime, shift_end_datetime)
                    curr_datetime = shift_end_datetime

            curr_datetime = datetime.combine(curr_datetime.date(), DAY_START) + timedelta(days=1)

    def __str__(self):
        return f"{self.store} - {self.business_hours} - {self.always_open}"
