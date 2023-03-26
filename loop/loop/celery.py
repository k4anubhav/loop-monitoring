import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loop.settings')

app = Celery('loop')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
