from django.test import tag

from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APITestCase

from argus.incident.serializers import IncidentSerializer
from argus.notificationprofile.factories import (
    DestinationConfigFactory,
    FilterFactory,
    NotificationProfileFactory,
    TimeslotFactory,
)
from argus.notificationprofile.models import (
    Media,
    NotificationProfile,
    Filter,
    Timeslot,
)
from argus.util.testing import disconnect_signals, connect_signals

from .. import IncidentAPITestCaseHelper


@tag("API", "integration")
class ViewTests(APITestCase, IncidentAPITestCaseHelper):
    def setUp(self):
        disconnect_signals()
        super().init_test_objects()

        incident1_json = IncidentSerializer([self.incident1], many=True).data
        self.incident1_json = JSONRenderer().render(incident1_json)

        self.timeslot1 = TimeslotFactory(user=self.user1, name="Never")
        self.timeslot2 = TimeslotFactory(user=self.user1, name="Never 2: Ever-expanding Void")
        self.filter1 = FilterFactory(
            user=self.user1,
            name="Critical incidents",
            filter_string=f'{{"sourceSystemIds": [{self.source1.pk}]}}',
        )
        self.notification_profile1 = NotificationProfileFactory(user=self.user1, timeslot=self.timeslot1)
        self.notification_profile1.filters.add(self.filter1)
        self.filter2 = FilterFactory(
            user=self.user1,
            name="Unused filter",
            filter_string=f'{{"sourceSystemIds": [{self.source1.pk}]}}',
        )
        self.notification_profile1.destinations.set(self.user1.destinations.all())
        self.media = ["EM", "SM"]
        self.sms_destination = DestinationConfigFactory(
            user=self.user1,
            media=Media.objects.get(slug="sms"),
            settings={"phone_number": "+4747474700"},
        )

        self.notification_profile1.destinations.set(self.user1.destinations.all())
        self.media = ["EM", "SM"]

    def teardown(self):
        connect_signals()

    def test_incidents_filtered_by_notification_profile_view(self):
        response = self.user1_rest_client.get(
            f"/api/v1/notificationprofiles/{self.notification_profile1.pk}/incidents/"
        )
        self.assertEqual(response.content, self.incident1_json)

    def test_notification_profile_can_update_timeslot_without_changing_pk(self):
        profile1_pk = self.notification_profile1.pk
        profile1_path = f"/api/v1/notificationprofiles/{profile1_pk}/"

        response = self.user1_rest_client.put(
            profile1_path,
            {
                "timeslot": self.timeslot2.pk,
                "filters": [f.pk for f in self.notification_profile1.filters.all()],
                "media": self.media,
                "phone_number": self.sms_destination.pk,
                "active": self.notification_profile1.active,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pk"], profile1_pk)
        self.assertEqual(NotificationProfile.objects.get(pk=profile1_pk).timeslot.pk, self.timeslot2.pk)

    def test_get_notification_profile_by_pk(self):
        profile_pk = self.notification_profile1.pk
        response = self.user1_rest_client.get(f"/api/v1/notificationprofiles/{profile_pk}/")
        self.assertEqual(response.data["pk"], profile_pk)

    def test_get_all_notification_profiles(self):
        response = self.user1_rest_client.get("/api/v1/notificationprofiles/")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["pk"], self.notification_profile1.pk)

    def test_can_create_new_notification_profile_with_correct_values(self):
        response = self.user1_rest_client.post(
            "/api/v1/notificationprofiles/",
            {
                "timeslot": self.timeslot2.pk,
                "filters": [f.pk for f in self.notification_profile1.filters.all()],
                "media": self.media,
                "phone_number": self.sms_destination.pk,
                "active": self.notification_profile1.active,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(NotificationProfile.objects.filter(pk=response.data.get("pk")))

    def test_created_notificaton_profile_has_correct_media(self):
        response = self.user1_rest_client.post(
            "/api/v1/notificationprofiles/",
            {
                "timeslot": self.timeslot2.pk,
                "filters": [f.pk for f in self.notification_profile1.filters.all()],
                "media": self.media,
                "phone_number": self.sms_destination.pk,
                "active": self.notification_profile1.active,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["media"], self.media)

    def test_can_delete_notification_profile(self):
        profile_pk = self.notification_profile1.pk
        response = self.user1_rest_client.delete(f"/api/v1/notificationprofiles/{profile_pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(NotificationProfile.objects.filter(pk=profile_pk).exists())

    def test_get_all_timeslots(self):
        response = self.user1_rest_client.get("/api/v1/notificationprofiles/timeslots/")
        default_timeslot = self.user1.timeslots.get(name="All the time")
        timeslot_pks = set([default_timeslot.pk, self.timeslot1.pk, self.timeslot2.pk])
        response_pks = set([timeslot["pk"] for timeslot in response.data])
        self.assertEqual(response_pks, timeslot_pks)

    def test_can_create_new_timeslot_with_correct_values(self):
        response = self.user1_rest_client.post(
            "/api/v1/notificationprofiles/timeslots/",
            {
                "name": "test-timeslot",
                "time_recurrences": [{"days": [1, 2, 3], "start": "10:00:00", "end": "20:00:00"}],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Timeslot.objects.filter(user=self.user1, name="test-timeslot").exists())

    def test_can_not_create_new_timeslot_with_end_time_before_start_time(self):
        response = self.user1_rest_client.post(
            "/api/v1/notificationprofiles/timeslots/",
            {
                "name": "test-timeslot",
                "time_recurrences": [{"days": [1, 2, 3], "start": "20:00:00", "end": "10:00:00"}],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Timeslot.objects.filter(user=self.user1, name="test-timeslot").exists())

    def test_get_timeslot_by_pk(self):
        timeslot_pk = self.timeslot1.pk
        response = self.user1_rest_client.get(f"/api/v1/notificationprofiles/timeslots/{timeslot_pk}/")
        self.assertEqual(response.data["pk"], timeslot_pk)

    def test_can_update_timeslot_name(self):
        timeslot_pk = self.timeslot1.pk
        new_name = "new-test-name"
        response = self.user1_rest_client.put(
            f"/api/v1/notificationprofiles/timeslots/{timeslot_pk}/",
            {"name": new_name, "time_recurrences": [{"days": [1, 2, 3], "start": "10:00:00", "end": "20:00:00"}]},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Timeslot.objects.get(pk=timeslot_pk).name, new_name)

    def test_can_not_update_timeslot_end_time_to_before_start_time(self):
        timeslot_pk = self.timeslot1.pk
        response = self.user1_rest_client.put(
            f"/api/v1/notificationprofiles/timeslots/{timeslot_pk}/",
            {
                "name": self.timeslot1.name,
                "time_recurrences": [{"days": [1, 2, 3], "start": "20:00:00", "end": "10:00:00"}],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_delete_timeslot(self):
        timeslot_pk = self.timeslot1.pk
        response = self.user1_rest_client.delete(f"/api/v1/notificationprofiles/timeslots/{timeslot_pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Timeslot.objects.filter(pk=timeslot_pk).exists())

    def test_get_all_filters(self):
        response = self.user1_rest_client.get("/api/v1/notificationprofiles/filters/")
        self.assertTrue(len(response.data), 1)
        self.assertEqual(response.data[0]["pk"], self.filter1.pk)

    def test_can_create_new_filter_with_correct_values(self):
        response = self.user1_rest_client.post(
            "/api/v1/notificationprofiles/filters/",
            {
                "name": "test-filter",
                "filter_string": f'{{"sourceSystemIds": [{self.source1.pk}], "tags": ["key1=value"]}}',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Filter.objects.filter(user=self.user1, name="test-filter").exists())

    def test_get_filter_by_pk(self):
        filter_pk = self.filter1.pk
        response = self.user1_rest_client.get(f"/api/v1/notificationprofiles/filters/{filter_pk}/")
        self.assertEqual(response.data["pk"], filter_pk)

    def test_can_update_filter_name(self):
        filter_pk = self.filter1.pk
        new_name = "new-test-name"
        response = self.user1_rest_client.put(
            f"/api/v1/notificationprofiles/filters/{filter_pk}/",
            {
                "name": new_name,
                "filter_string": f'{{"sourceSystemIds": [{self.source1.pk}], "tags": ["key1=value"]}}',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Filter.objects.get(pk=filter_pk).name, new_name)

    def test_can_delete_unused_filter(self):
        filter_pk = self.filter2.pk
        response = self.user1_rest_client.delete(f"/api/v1/notificationprofiles/filters/{filter_pk}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Filter.objects.filter(pk=filter_pk).exists())

    def test_can_not_delete_used_filter(self):
        filter_pk = self.filter1.pk
        response = self.user1_rest_client.delete(f"/api/v1/notificationprofiles/filters/{filter_pk}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Filter.objects.filter(pk=filter_pk).exists())

    def test_filterpreview_returns_correct_incidents(self):
        response = self.user1_rest_client.post(
            "/api/v1/notificationprofiles/filterpreview/",
            {"sourceSystemIds": [self.source1.pk], "tags": [str(self.tag1)]},
        )
        self.assertTrue(len(response.data), 1)
        self.assertEqual(response.data[0]["pk"], self.incident1.pk)
