from django.db import models


class StoreReport(models.Model):
    report_id = models.UUIDField(primary_key=True, editable=False)

    file = models.FileField(upload_to='reports')
