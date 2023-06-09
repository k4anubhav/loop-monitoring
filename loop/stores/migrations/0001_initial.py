# Generated by Django 4.1.7 on 2023-03-26 12:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Store",
            fields=[
                ("store_id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "timezone_str",
                    models.CharField(default="America/Chicago", max_length=50),
                ),
            ],
        ),
        migrations.CreateModel(
            name="StoreStatus",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "timestamp_utc",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                ("is_active", models.BooleanField()),
                (
                    "store",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status",
                        to="stores.store",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="StoreBusinessHour",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "day",
                    models.IntegerField(
                        choices=[
                            (0, "Monday"),
                            (1, "Tuesday"),
                            (2, "Wednesday"),
                            (3, "Thursday"),
                            (4, "Friday"),
                            (5, "Saturday"),
                            (6, "Sunday"),
                        ],
                        db_index=True,
                    ),
                ),
                ("start_time_local", models.TimeField()),
                ("end_time_local", models.TimeField()),
                (
                    "store",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="business_hours",
                        to="stores.store",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="storebusinesshour",
            constraint=models.CheckConstraint(
                check=models.Q(("start_time_local__lt", models.F("end_time_local"))),
                name="start_time_lt_end_time",
            ),
        ),
    ]
