from django.test import tag

from rest_framework.test import APITestCase
from argus.auth.factories import PersonUserFactory
from argus.util.testing import disconnect_signals, connect_signals


@tag("integration")
class SignalTests(APITestCase):
    def setUp(self):
        disconnect_signals()

        self.user1 = PersonUserFactory()
        self.user2 = PersonUserFactory(email="")
        self.destination1 = self.user1.destination_configs.first()
        self.destination2 = self.user2.destination_configs.first()

    def teardown(self):
        connect_signals()

    def test_default_email_destinations(self):
        self.assertTrue(self.destination1)
        self.assertTrue(self.destination1.settings["synced"])

        self.assertFalse(self.destination2)

        self.user2.email = self.user2.username
        self.user2.save(update_fields=["email"])
        self.destination2 = self.user2.destination_configs.first()
        self.assertTrue(self.destination2)
        self.assertTrue(self.destination2.settings["synced"])

        self.user2.email = "new.email@example.com"
        self.user2.save(update_fields=["email"])
        self.destination2 = self.user2.destination_configs.filter(settings__synced=True).first()
        self.assertEqual(self.user2.email, self.destination2.settings["email_address"])

        self.user1.email = ""
        self.user1.save(update_fields=["email"])
        self.assertFalse(self.user1.destination_configs.filter(settings__synced=True))
