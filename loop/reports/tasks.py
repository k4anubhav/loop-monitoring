import csv
import io
import logging
from datetime import datetime, timedelta
from typing import TypedDict

from celery import shared_task
from django.core.files.base import ContentFile

from reports.models import StoreReport
from stores.models import Store, StoreStatus
from stores.utils import StoreBusinessHourHelper, time_datetime_difference

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


def calculate_uptime_downtime(
        start_datetime: datetime, end_datetime: datetime, helper: 'StoreBusinessHourHelper'
) -> (timedelta, timedelta):
    """
    Calculate uptime and downtime from start_datetime to end_datetime, if no status for business hours of that day, then
    consider it as downtime
    """
    status_list = list(
        StoreStatus.objects.filter(
            store=helper.store,
            timestamp_utc__gte=start_datetime,
            timestamp_utc__lte=end_datetime
        ).filter_store_hours(
            helper=helper
        ).order_by('timestamp_utc')
    )

    uptime = timedelta()
    downtime = timedelta()

    status_index = 0

    # iterate through all business hours in the given time range
    for business_hour in helper.business_hour_generator(start_datetime, end_datetime):
        # get all statuses of this business hour
        statuses_of_this_business_hour: 'list[StoreStatus]' = []
        while status_index < len(status_list):
            status = status_list[status_index]
            if business_hour.contains(status.timestamp_utc):
                statuses_of_this_business_hour.append(status)
                status_index += 1
            else:
                break

        if len(statuses_of_this_business_hour) == 0:
            # no status found for this business hour
            # consider it as downtime
            downtime += business_hour.duration
        else:
            # handle first status
            first_status = statuses_of_this_business_hour[0]
            time_diff = time_datetime_difference(business_hour.start_time, first_status.timestamp_utc)
            if first_status.is_active:
                # store is open, assume from business hour start time to first status is uptime
                uptime += time_diff
            else:
                # store is closed, assume from business hour start time to first status is downtime
                downtime += time_diff

            last_status = first_status
            # handle middle statuses
            for status in statuses_of_this_business_hour[1:]:
                time_diff = status.timestamp_utc - last_status.timestamp_utc
                if last_status.is_active and status.is_active:
                    # last status is up and current status is up, assume from last status to current status is uptime
                    uptime += time_diff
                elif not last_status.is_active and not status.is_active:
                    # last status is down and current status is down, assume from last status to current status is
                    # downtime
                    downtime += time_diff
                elif last_status.is_active and not status.is_active:
                    # last status is up and current status is down, assume from last status to current status is
                    # downtime
                    downtime += time_diff
                elif not last_status.is_active and status.is_active:
                    # last status is down and current status is up, assume from last status to current status is uptime
                    uptime += time_diff
                last_status = status

            # handle last status
            time_diff = time_datetime_difference(business_hour.end_time, last_status.timestamp_utc)
            if last_status.is_active:
                # store is open, assume from last status to end of business hour is uptime
                uptime += time_diff
            else:
                # store is closed, assume from last status to end of business hour is downtime
                downtime += time_diff

    return uptime, downtime


@shared_task(name='reports.tasks.generate_report')
def generate_report(from_datetime_str: str):
    """
    Generate report for each store, with uptime and downtime for last hour, last day, and last week
    """
    from_datetime: 'datetime' = datetime.fromisoformat(from_datetime_str)

    reports: 'list[StoreReportDict]' = []
    stores = Store.objects.all()

    total_stores = stores.count()
    completed_stores = 0

    for store in stores:
        if completed_stores % 100 == 0:
            logger.info(f'Completed {completed_stores} out of {total_stores} stores')

        business_hour_helper = StoreBusinessHourHelper(store=store)

        uptime_last_hour, downtime_last_hour = calculate_uptime_downtime(
            start_datetime=from_datetime - timedelta(hours=1),
            end_datetime=from_datetime,
            helper=business_hour_helper,
        )
        uptime_last_day, downtime_last_day = calculate_uptime_downtime(
            start_datetime=from_datetime - timedelta(days=1),
            end_datetime=from_datetime,
            helper=business_hour_helper,
        )
        uptime_last_week, downtime_last_week = calculate_uptime_downtime(
            start_datetime=from_datetime - timedelta(weeks=1),
            end_datetime=from_datetime,
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
