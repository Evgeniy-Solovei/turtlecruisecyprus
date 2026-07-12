from rest_framework import serializers

from .models import Cruise, CruiseSchedule


class CruiseScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CruiseSchedule
        fields = ["weekday", "start_time", "end_time", "timezone", "valid_from", "valid_to"]


class CruiseSerializer(serializers.ModelSerializer):
    schedules = CruiseScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = Cruise
        fields = [
            "code",
            "name",
            "description",
            "default_adult_price",
            "default_child_price",
            "child_allowed",
            "default_capacity",
            "default_duration_minutes",
            "schedules",
        ]
