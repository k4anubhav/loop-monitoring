# Generated by Django 4.1.7 on 2023-03-26 12:36

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="StoreReport",
            fields=[
                (
                    "report_id",
                    models.UUIDField(editable=False, primary_key=True, serialize=False),
                ),
                ("file", models.FileField(upload_to="reports")),
            ],
        ),
    ]
