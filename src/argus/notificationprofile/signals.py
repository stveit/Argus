from argus.auth.models import User
from .models import DestinationConfig, Media, TimeRecurrence, Timeslot

__all__ = [
    "create_default_timeslot",
]


# Create default immediate Timeslot when a user is created
def create_default_timeslot(sender, instance: User, created, raw, *args, **kwargs):
    if raw or not created or instance.timeslots.exists():
        return

    TimeRecurrence.objects.create(
        timeslot=Timeslot.objects.create(user=instance, name="All the time"),
        days=[day for day in TimeRecurrence.Day.values],
        start=TimeRecurrence.DAY_START,
        end=TimeRecurrence.DAY_END,
    )


# Create default DestinationConfig when a user is created
def create_default_destination_config(sender, instance: User, created, raw, *args, **kwargs):
    if raw or not created or instance.destination_configs.exists():
        return

    DestinationConfig.objects.create(
        user=instance,
        media=Media.objects.get(slug="email"),
        settings={"email_address": instance.email},
    )


# Update the email address in the synced destination config when a user logs in
def update_email_address(sender, request, user: User, *args, **kwargs):
    email_destinations = user.destinations.filter(media__slug="email")

    for destination in email_destinations:
        if destination.settings["synced"] == True:
            if not user.phone_number:
                destination.delete()
                return
            if not destination.settings["phone_number"] == user.phone_number:
                destination.settings["phone_number"] = user.phone_number
                destination.save()
            return
