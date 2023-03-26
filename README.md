# Uptime / Downtime Monitoring Django App

# Requirements

- Python 3.6+

## Install Requirements

```bash
pip install -r requirements.txt
```

## Run server

```bash
python manage.py runserver
```

## Run Celery worker

```bash
celery -A loop worker --loglevel=info

# For Windows
celery -A loop worker --loglevel=info -P solo
```

## Import data

```bash
python manage.py csv_import_store ../store-timezone.csv
python manage.py csv_import_business_hours ../store-hours.csv
python manage.py csv_import_store_status ../store-status.csv
```