from django.db import IntegrityError
from rest_framework import fields, serializers

from argus.incident.models import SourceSystem, Tag, Incident

from .primitive_serializers import FilterBlobSerializer, FilterPreviewSerializer
from .media import MEDIA_CLASSES_DICT
from .models import DestinationConfig, Filter, Media, NotificationProfile, TimeRecurrence, Timeslot
from .validators import validate_filter_string


class TimeRecurrenceSerializer(serializers.ModelSerializer):
    ALL_DAY_KEY = "all_day"

    days = fields.MultipleChoiceField(choices=TimeRecurrence.Day.choices)

    class Meta:
        model = TimeRecurrence
        fields = [
            "days",
            "start",
            "end",
        ]

    def validate(self, attrs: dict):
        if attrs["start"] >= attrs["end"]:
            raise serializers.ValidationError("'start' must be before 'end'.")
        return attrs

    def to_internal_value(self, data: dict):
        if data.get(self.ALL_DAY_KEY):
            data["start"] = TimeRecurrence.DAY_START
            data["end"] = TimeRecurrence.DAY_END

        return super().to_internal_value(data)

    def to_representation(self, instance: TimeRecurrence):
        instance_dict = super().to_representation(instance)
        # `days` is initially represented as a set; this converts it into a sorted list
        # (`days` is stored sorted in the DB - see `TimeRecurrence.save()`)
        instance_dict["days"] = sorted(instance_dict["days"])

        if instance_dict["start"] == str(TimeRecurrence.DAY_START) and instance_dict["end"] == str(
            TimeRecurrence.DAY_END
        ):
            instance_dict[self.ALL_DAY_KEY] = True

        return instance_dict


class TimeslotSerializer(serializers.ModelSerializer):
    time_recurrences = TimeRecurrenceSerializer(many=True)

    class Meta:
        model = Timeslot
        fields = [
            "pk",
            "name",
            "time_recurrences",
        ]
        # "user" isn't in the list of fields so we can't use a UniqueTogetherValidator

    def validate_name(self, name):
        owner = self.context["request"].user
        qs = Timeslot.objects.filter(user=owner, name=name)
        if not qs.exists():  # create
            return name
        instance = getattr(self, "instance", None)  # update
        if instance and qs.filter(pk=instance.pk).exists():
            return name
        raise serializers.ValidationError(
            f'The name "{name}" is already in use for a another timeslot owned by user {owner}.'
        )

    def create(self, validated_data: dict):
        time_recurrences_data = validated_data.pop("time_recurrences")
        timeslot = Timeslot.objects.create(**validated_data)

        for time_recurrence_data in time_recurrences_data:
            TimeRecurrence.objects.create(timeslot=timeslot, **time_recurrence_data)

        return timeslot

    def update(self, timeslot: Timeslot, validated_data: dict):
        time_recurrences_data = validated_data.pop("time_recurrences")
        name = validated_data["name"]
        timeslot.name = name
        timeslot.save()

        # Replace existing time recurrences with posted time recurrences
        timeslot.time_recurrences.all().delete()
        for time_recurrence_data in time_recurrences_data:
            TimeRecurrence.objects.create(timeslot=timeslot, **time_recurrence_data)

        return timeslot


class FilterSerializer(serializers.ModelSerializer):
    filter_string = serializers.CharField(
        validators=[validate_filter_string],
        help_text='Deprecated: Use "filter" instead',
    )
    filter = FilterBlobSerializer(required=False)

    class Meta:
        model = Filter
        fields = [
            "pk",
            "name",
            "filter_string",
            "filter",
        ]


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = [
            "slug",
            "name",
        ]


class ResponseDestinationConfigSerializer(serializers.ModelSerializer):
    media = MediaSerializer()

    class Meta:
        model = DestinationConfig
        fields = [
            "media",
            "settings",
        ]


class RequestDestinationConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DestinationConfig
        fields = [
            "media",
            "settings",
        ]

    def validate(self, attrs: dict):
        if self.instance and not attrs["media"].slug == self.instance.media.slug:
            raise serializers.ValidationError("Media cannot be updated, only settings.")

        attrs["settings"] = MEDIA_CLASSES_DICT[attrs["media"].slug].validate(self, attrs)

        return attrs


class ResponseNotificationProfileSerializer(serializers.ModelSerializer):
    timeslot = TimeslotSerializer()
    filters = FilterSerializer(many=True)
    destinations = ResponseDestinationConfigSerializer(many=True)

    class Meta:
        model = NotificationProfile
        fields = [
            "pk",
            "timeslot",
            "filters",
            "destinations",
            "active",
        ]
        # "pk" needs to be listed, as "timeslot" is the actual primary key
        read_only_fields = ["pk"]


class RequestNotificationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationProfile
        fields = [
            "pk",
            "timeslot",
            "filters",
            "destinations",
            "active",
        ]
        # "pk" needs to be listed, as "timeslot" is the actual primary key
        read_only_fields = ["pk"]

    def create(self, validated_data: dict):
        try:
            return super().create(validated_data)
        except IntegrityError as e:
            timeslot_pk = validated_data["timeslot"].pk
            if NotificationProfile.objects.filter(pk=timeslot_pk).exists():
                raise serializers.ValidationError(
                    f"NotificationProfile with Timeslot with pk={timeslot_pk} already exists."
                )
            else:
                raise e

    def update(self, instance: NotificationProfile, validated_data: dict):
        new_timeslot = validated_data.pop("timeslot")
        old_timeslot = instance.timeslot
        if new_timeslot != old_timeslot:
            # Save the notification profile with the new timeslot (will duplicate the object with a different PK)
            instance.timeslot = new_timeslot
            instance.save()
            # Delete the duplicate (old) object
            NotificationProfile.objects.get(timeslot=old_timeslot).delete()

        return super().update(instance, validated_data)

    def validate(self, attrs: dict):
        if attrs["timeslot"].user != self.context["request"].user:
            raise serializers.ValidationError("The user of 'timeslot' must be the same as the requesting user.")
        return attrs
