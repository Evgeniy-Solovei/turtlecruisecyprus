from datetime import time

from django.test import TestCase

from apps.cruises.models import Cruise, CruiseSchedule
from apps.cruises.time_utils import default_times_for_cruise, format_time_range, times_for_cruise_date


class CruiseTimeUtilsTests(TestCase):
    def setUp(self):
        self.cruise = Cruise.objects.create(
            code="morning",
            name="Morning",
            default_adult_price=45,
            default_child_price=25,
            default_capacity=30,
            legacy_wp_service_id=99001,
        )
        for weekday in range(7):
            CruiseSchedule.objects.create(
                cruise=self.cruise,
                weekday=weekday,
                start_time=time(9, 30),
                end_time=time(14, 0),
            )

    def test_format_time_range_single_source(self):
        self.assertEqual(format_time_range(time(9, 30), time(14, 0)), "9:30 – 14:00")

    def test_times_for_cruise_date(self):
        from datetime import date, timedelta

        target = date.today() + timedelta(days=10)
        start, end, label = times_for_cruise_date(self.cruise, target)
        self.assertEqual(str(start), "09:30:00")
        self.assertEqual(str(end), "14:00:00")
        self.assertEqual(label, "9:30 – 14:00")

    def test_default_times_from_schedule_not_hardcoded(self):
        start, end, label = default_times_for_cruise(self.cruise)
        self.assertEqual(label, "9:30 – 14:00")
        CruiseSchedule.objects.filter(cruise=self.cruise).update(start_time=time(10, 0), end_time=time(15, 0))
        start, end, label = default_times_for_cruise(self.cruise)
        self.assertEqual(label, "10:00 – 15:00")
