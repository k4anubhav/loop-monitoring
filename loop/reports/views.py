from uuid import UUID

from celery.result import AsyncResult
from rest_framework import generics
from rest_framework.request import Request
from rest_framework.response import Response

from .models import StoreReport
from .serializers import ReportSerializer, ReportIdSerializer
from .tasks import generate_report


class ReportTriggerView(generics.GenericAPIView):
    serializer_class = ReportIdSerializer

    def post(self, request: Request, *args, **kwargs):
        result: AsyncResult = generate_report.delay()
        return Response(self.get_serializer({'report_id': result.id}).data)


class ReportView(generics.GenericAPIView):
    serializer_class = ReportSerializer

    def get(self, request: Request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        report_id: UUID = serializer.validated_data['report_id']
        # first check if the report present in the database (completed)
        try:
            report = StoreReport.objects.get(report_id=report_id)
            return Response(self.get_serializer({'status': 'completed', 'report': report.file}).data)
        except StoreReport.DoesNotExist:
            result: AsyncResult = AsyncResult(str(report_id))
            # `SUCCESS` means the task completed just after the database check
            if result.status in ['PENDING', 'STARTED', 'RETRY', 'SUCCESS']:
                return Response(self.get_serializer({'status': 'running'}).data)
            else:
                return Response(self.get_serializer({'status': 'failed'}).data)
