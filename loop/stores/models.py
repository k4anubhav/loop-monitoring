import zoneinfo
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, Q, When
from django.db.models.functions import ExtractIsoWeekDay, TruncTime

if TYPE_CHECKING:
    from stores.utils import StoreBusinessHourHelper


class Store(models.Model):
    store_id = models.BigAutoField(primary_key=True)
    timezone_str = models.CharField(max_length=50, default='America/Chicago')

    @property
    def timezone(self):
        return zoneinfo.ZoneInfo(self.timezone_str)

    def save(self, *args, **kwargs):
        # validate timezone
        try:
            zoneinfo.ZoneInfo(self.timezone_str)
        except zoneinfo.ZoneInfoNotFoundError:
            raise ValidationError(f'Invalid timezone: {self.timezone_str}')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'store: {self.store_id}'


class StoreBusinessHour(models.Model):
    class WeekDays(models.IntegerChoices):
        MONDAY = 0, 'Monday'
        TUESDAY = 1, 'Tuesday'
        WEDNESDAY = 2, 'Wednesday'
        THURSDAY = 3, 'Thursday'
        FRIDAY = 4, 'Friday'
        SATURDAY = 5, 'Saturday'
        SUNDAY = 6, 'Sunday'

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='business_hours')
    day = models.IntegerField(choices=WeekDays.choices, db_index=True)
    start_time_local = models.TimeField()
    end_time_local = models.TimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_time_local__lt=models.F('end_time_local')),
                name='start_time_lt_end_time'
            )
        ]

    def __str__(self):
        return f'{self.store_id} {self.get_day_display()} {self.start_time_local} - {self.end_time_local}'


class StoreStatusQuerySet(models.QuerySet):
    def filter_store_hours(self, helper: 'StoreBusinessHourHelper'):
        cases = []
        for weekday, hours in helper.business_hours_utc.items():
            conditions = None
            for b_hour in hours:
                condition = Q(
                    time__gte=b_hour.start_time,
                    time__lte=b_hour.end_time,
                )
                if conditions is None:
                    conditions = condition
                else:
                    conditions |= condition

            # if conditions is empty, then the store is closed on that day
            if conditions:
                cases.append(
                    When(Q(weekday=weekday) & conditions, then=True)
                )

        return self.annotate(
            time=TruncTime('timestamp_utc'),
            weekday=ExtractIsoWeekDay('timestamp_utc') - models.Value(1, output_field=models.IntegerField()),
            always_open=models.Value(helper.always_open, output_field=models.BooleanField()),
        ).annotate(
            is_store_open=Case(
                When(always_open=True, then=True),
                *cases,
                default=False,
            )
        ).filter(is_store_open=True)


class StoreStatus(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='status')
    timestamp_utc = models.DateTimeField(auto_now_add=True, db_index=True)

    # use boolean field rather than text choice
    is_active = models.BooleanField()

    objects = StoreStatusQuerySet.as_manager()

    def __str__(self):
        return f'{self.store_id} {self.timestamp_utc} {self.is_active}'
