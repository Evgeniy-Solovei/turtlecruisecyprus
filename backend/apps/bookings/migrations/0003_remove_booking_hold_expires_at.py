from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0002_booking_cancel_reason"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="booking",
            name="bookings_bo_hold_ex_ab9602_idx",
        ),
        migrations.RemoveField(
            model_name="booking",
            name="hold_expires_at",
        ),
    ]
