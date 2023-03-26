import csv
import io
import logging
from datetime import timedelta, datetime
from typing import TypedDict, Optional

from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone

from stores.models import Store, StoreStatus, StoreBusinessHour
from .models import StoreReport
from .utils import make_aware, StoreBusinessHourHelper, time_datetime_difference

logger = logging.getLogger(__name__)


class StoreReportDict(TypedDict):
    store_id: int
    uptime_last_hour: float
    downtime_last_hour: float
    uptime_last_day: float
    downtime_last_day: float
    uptime_last_week: float
    downtime_last_week: float


class StatusDict(TypedDict):
    is_active: bool
    timestamp_utc: datetime


class UptimeDowntimeCalculator:
    def __init__(self):
        self._uptime: 'Optional[timedelta]' = None
        self._downtime: 'Optional[timedelta]' = None

    @staticmethod
    def _handle_last_status(
            last_status: 'StatusDict',
            last_business_hour: 'StoreBusinessHourHelper.BusinessHour'
    ) -> 'tuple[timedelta, timedelta]':
        """
        Handle the last status of the last business hour
        """
        uptime = timedelta()
        downtime = timedelta()
        time_diff = time_datetime_difference(last_business_hour.end_time, last_status['timestamp_utc'])
        if last_status['is_active']:
            # last status is up, assume from last status to end of business hour is uptime
            uptime += time_diff
        else:
            # last status is down, assume from last status to end_time is downtime
            downtime += time_diff
        return uptime, downtime

    @staticmethod
    def _handle_first_status(
            crt_status: 'StatusDict',
            crt_business_hour: 'StoreBusinessHourHelper.BusinessHour'
    ) -> 'tuple[timedelta, timedelta]':
        """
        Handle the first status of the first business hour
        """
        uptime = timedelta()
        downtime = timedelta()
        time_diff = time_datetime_difference(crt_business_hour.start_time, crt_status['timestamp_utc'])
        if crt_status['is_active']:
            # first status is up, assume from start_time to first status is uptime
            uptime += time_diff
        else:
            # first status is down, assume from start_time to first status is downtime
            downtime += time_diff
        return uptime, downtime

    @classmethod
    def calculate_uptime_downtime(
            cls,
            start_datetime: 'datetime',
            end_datetime: 'datetime',
            helper: 'StoreBusinessHourHelper',
    ) -> 'tuple[timedelta, timedelta]':
        uptime = timedelta()
        downtime = timedelta()

        statuses = (
            StoreStatus.objects
            .filter(timestamp_utc__gte=start_datetime, timestamp_utc__lt=end_datetime, store_id=helper.store.store_id)
            .filter_store_hours(helper=helper)
            .order_by('timestamp_utc')
            .values('is_active', 'timestamp_utc')
        )

        last_status: 'Optional[StatusDict]' = None
        last_business_hour: 'Optional[StoreBusinessHourHelper.BusinessHour]' = None

        for status in statuses:
            status: 'StatusDict'
            status_time = make_aware(status['timestamp_utc'].time(), timezone.utc)
            last_status_time = make_aware(last_status['timestamp_utc'].time(), timezone.utc) if last_status else None

            business_hour = helper.get_business_hours(status['timestamp_utc'].weekday(), status_time)

            if not business_hour:
                logger.warning(
                    f'Should not happen, status {status} is not in any business hour, '
                    f'but it is in the store hours'
                )
                last_status = status
                last_business_hour = business_hour
                continue

            if last_business_hour and last_status and business_hour != last_business_hour:
                # handle the last status of the last business hour
                uptime_add, downtime_add = cls._handle_last_status(last_status, last_business_hour)
                uptime += uptime_add
                downtime += downtime_add

                last_status = None

            # handle the first status of the business hour
            if not last_status:
                uptime_add, downtime_add = cls._handle_first_status(status, business_hour)
                uptime += uptime_add
                downtime += downtime_add

                last_status = status
                last_business_hour = business_hour
                continue

            overlap_start = max(business_hour.start_time, last_status_time)
            overlap_end = min(business_hour.end_time, status_time)

            # both are in same timezone, no need to handle timezone
            overlap_duration = timedelta(
                hours=overlap_end.hour - overlap_start.hour,
                minutes=overlap_end.minute - overlap_start.minute,
                seconds=overlap_end.second - overlap_start.second,
                microseconds=overlap_end.microsecond - overlap_start.microsecond,
            )

            if last_status['is_active'] and status['is_active']:
                # last status is up and current status is up, assume from last status to current status is uptime
                uptime += overlap_duration
            elif not last_status['is_active'] and not status['is_active']:
                # last status is down and current status is down, assume from last status to current status is downtime
                downtime += overlap_duration
            elif last_status['is_active'] and not status['is_active']:
                # last status is up and current status is down, assume from last status to current status is downtime
                downtime += overlap_duration
            elif not last_status['is_active'] and status['is_active']:
                # last status is down and current status is up, assume from last status to current status is uptime
                uptime += overlap_duration

            last_status = status
            last_business_hour = business_hour

        # handle the last status of the business hour
        if last_status and last_business_hour:
            uptime_add, downtime_add = cls._handle_last_status(last_status, last_business_hour)
            uptime += uptime_add
            downtime += downtime_add
        else:
            # no status is found, assume from start_datetime to end_datetime is downtime
            downtime += end_datetime - start_datetime

        return uptime, downtime


@shared_task(name='reports.tasks.generate_report')
def generate_report():
    """
    Generate report for each store, with uptime and downtime for last hour, last day, and last week
    """

    reports: 'list[StoreReportDict]' = []
    stores = Store.objects.all()
    crt = timezone.now()

    total_stores = stores.count()
    completed_stores = 0

    for store in stores:
        if completed_stores % 100 == 0:
            logger.info(f'Completed {completed_stores} out of {total_stores} stores')
        business_hours = StoreBusinessHour.objects.filter(store=store)
        business_hour_helper = StoreBusinessHourHelper(store=store, business_hours=business_hours)

        uptime_last_hour, downtime_last_hour = UptimeDowntimeCalculator.calculate_uptime_downtime(
            start_datetime=crt - timedelta(hours=1),
            end_datetime=crt,
            helper=business_hour_helper,
        )
        uptime_last_day, downtime_last_day = UptimeDowntimeCalculator.calculate_uptime_downtime(
            start_datetime=crt - timedelta(days=1),
            end_datetime=crt,
            helper=business_hour_helper,
        )
        uptime_last_week, downtime_last_week = UptimeDowntimeCalculator.calculate_uptime_downtime(
            start_datetime=crt - timedelta(weeks=1),
            end_datetime=crt,
            helper=business_hour_helper,
        )

        reports.append({
            'store_id': store.store_id,
            'uptime_last_hour': uptime_last_hour.total_seconds() / 60,
            'downtime_last_hour': downtime_last_hour.total_seconds() / 60,
            'uptime_last_day': uptime_last_day.total_seconds() / 3600,
            'downtime_last_day': downtime_last_day.total_seconds() / 3600,
            'uptime_last_week': uptime_last_week.total_seconds() / 3600,
            'downtime_last_week': downtime_last_week.total_seconds() / 3600,
        })
        completed_stores += 1

    logger.info(f'Generated report for {len(reports)} stores')

    file_io = io.StringIO()
    writer = csv.DictWriter(file_io, fieldnames=reports[0].keys())
    writer.writeheader()
    # noinspection PyTypeChecker
    writer.writerows(reports)
    report_file = ContentFile(file_io.getvalue().encode(), name=f'{generate_report.request.id}.csv')
    StoreReport.objects.create(
        # task id of celery task
        report_id=generate_report.request.id,
        file=report_file,
    )

    return None
